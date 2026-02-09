"""LangGraph Librarian Agent for knowledge distillation."""

import logging
from typing import TypedDict, Annotated, List, Dict, Any
from datetime import datetime

from langgraph.graph import StateGraph, END
from langchain_core.messages import HumanMessage
from langchain_openai import ChatOpenAI

from src.settings import Settings
from src.memory_gateway.gateway import MemoryGateway
from src.memory_gateway.models import MemoryRequest, MemoryType, MemoryOperation
from .distiller import KnowledgeDistiller

logger = logging.getLogger(__name__)


class LibrarianState(TypedDict):
    """State for Librarian agent."""

    messages: Annotated[List[Any], "Messages"]
    raw_documents: List[Dict[str, Any]]
    extracted_entities: List[Dict[str, Any]]
    current_batch: int
    total_processed: int
    errors: List[str]


class LibrarianAgent:
    """
    LangGraph-based Librarian agent.
    
    This agent monitors the MongoDB "Capture" bucket and periodically:
    1. Fetches new unprocessed documents
    2. Analyzes them for architectural knowledge
    3. Extracts structured entities (Decisions, Requirements, etc.)
    4. Creates Neo4j nodes and relationships
    5. Marks documents as processed
    
    Implements Tiago Forte's "Distill" principle - condensing raw notes
    into high-level, actionable knowledge.
    """

    def __init__(self, settings: Settings, memory_gateway: MemoryGateway):
        """
        Initialize Librarian agent.
        
        Args:
            settings: Application settings
            memory_gateway: Memory gateway instance
        """
        self.settings = settings
        self.gateway = memory_gateway
        self.distiller = KnowledgeDistiller(settings, memory_gateway)
        
        # Initialize LLM for extraction (provider decides temperature)
        from mdrag.llm.completion_client import get_llm_init_kwargs
        self.llm = ChatOpenAI(
            model=settings.llm_model,
            api_key=settings.llm_api_key,
            base_url=settings.llm_base_url,
            **get_llm_init_kwargs(settings),
        )
        
        # Build the graph
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """
        Build LangGraph workflow.
        
        Returns:
            StateGraph instance
        """
        workflow = StateGraph(LibrarianState)
        
        # Add nodes
        workflow.add_node("fetch_documents", self._fetch_documents)
        workflow.add_node("analyze_documents", self._analyze_documents)
        workflow.add_node("extract_entities", self._extract_entities)
        workflow.add_node("create_graph_nodes", self._create_graph_nodes)
        workflow.add_node("mark_processed", self._mark_processed)
        
        # Define edges
        workflow.set_entry_point("fetch_documents")
        workflow.add_edge("fetch_documents", "analyze_documents")
        workflow.add_edge("analyze_documents", "extract_entities")
        workflow.add_edge("extract_entities", "create_graph_nodes")
        workflow.add_edge("create_graph_nodes", "mark_processed")
        workflow.add_edge("mark_processed", END)
        
        return workflow.compile()

    async def _fetch_documents(self, state: LibrarianState) -> LibrarianState:
        """
        Fetch unprocessed documents from MongoDB.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with raw documents
        """
        logger.info("librarian_fetching_documents")
        
        try:
            # Query MongoDB for unprocessed episodic memories
            request = MemoryRequest(
                operation=MemoryOperation.QUERY,
                memory_type=MemoryType.EPISODIC,
                entity_type="episodic_memories",
                filters={"metadata.processed": {"$ne": True}},
                limit=50,  # Process in batches
            )
            
            response = await self.gateway.execute(request)
            
            if response.success:
                state["raw_documents"] = response.data or []
                logger.info(
                    "librarian_documents_fetched",
                    extra={"count": len(state["raw_documents"])},
                )
            else:
                logger.error(
                    "librarian_fetch_failed",
                    extra={"error": response.error},
                )
                state["errors"].append(f"Fetch failed: {response.error}")
            
        except Exception as e:
            logger.exception("librarian_fetch_exception", extra={"error": str(e)})
            state["errors"].append(str(e))
        
        return state

    async def _analyze_documents(self, state: LibrarianState) -> LibrarianState:
        """
        Analyze documents for architectural knowledge.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with analysis
        """
        logger.info("librarian_analyzing_documents")
        
        if not state["raw_documents"]:
            return state
        
        # Add analysis message
        analysis_prompt = f"""
Analyze the following conversation/note excerpts for architectural knowledge:

Number of documents: {len(state["raw_documents"])}

Your task:
1. Identify architectural decisions
2. Identify requirements (functional/non-functional)
3. Identify code entities discussed
4. Identify external resources mentioned (videos, articles, etc.)

For each item, extract:
- Name/title
- Description/rationale
- Context
- Relationships to other entities

Focus on actionable, structured information that belongs in a knowledge graph.
"""
        
        state["messages"].append(HumanMessage(content=analysis_prompt))
        
        return state

    async def _extract_entities(self, state: LibrarianState) -> LibrarianState:
        """
        Extract structured entities from documents.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state with extracted entities
        """
        logger.info("librarian_extracting_entities")
        
        extracted = []
        
        for doc in state["raw_documents"]:
            try:
                # Use distiller to extract entities
                entities = await self.distiller.extract_entities_from_text(
                    doc.get("content", "")
                )
                
                for entity in entities:
                    entity["source_doc_id"] = str(doc.get("_id", ""))
                    extracted.append(entity)
                
            except Exception as e:
                logger.exception(
                    "librarian_extraction_failed",
                    extra={"doc_id": str(doc.get("_id", "")), "error": str(e)},
                )
                state["errors"].append(f"Extraction failed for {doc.get('_id')}: {e}")
        
        state["extracted_entities"] = extracted
        logger.info(
            "librarian_entities_extracted",
            extra={"count": len(extracted)},
        )
        
        return state

    async def _create_graph_nodes(self, state: LibrarianState) -> LibrarianState:
        """
        Create Neo4j nodes from extracted entities.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state
        """
        logger.info("librarian_creating_graph_nodes")
        
        created_count = 0
        
        for entity in state["extracted_entities"]:
            try:
                # Create node based on entity type
                await self.distiller.create_graph_node(entity)
                created_count += 1
                
            except Exception as e:
                logger.exception(
                    "librarian_node_creation_failed",
                    extra={"entity": entity, "error": str(e)},
                )
                state["errors"].append(f"Node creation failed: {e}")
        
        state["total_processed"] += created_count
        logger.info(
            "librarian_nodes_created",
            extra={"count": created_count},
        )
        
        return state

    async def _mark_processed(self, state: LibrarianState) -> LibrarianState:
        """
        Mark documents as processed in MongoDB.
        
        Args:
            state: Current agent state
            
        Returns:
            Updated state
        """
        logger.info("librarian_marking_processed")
        
        for doc in state["raw_documents"]:
            try:
                doc_id = doc.get("_id")
                if doc_id:
                    request = MemoryRequest(
                        operation=MemoryOperation.UPDATE,
                        memory_type=MemoryType.EPISODIC,
                        entity_type="episodic_memories",
                        entity_id=str(doc_id),
                        data={
                            "metadata.processed": True,
                            "metadata.processed_at": datetime.utcnow().isoformat(),
                        },
                    )
                    
                    await self.gateway.execute(request)
                
            except Exception as e:
                logger.exception(
                    "librarian_mark_failed",
                    extra={"doc_id": str(doc.get("_id", "")), "error": str(e)},
                )
        
        logger.info("librarian_processing_complete")
        
        return state

    async def run_distillation(self) -> Dict[str, Any]:
        """
        Run a single distillation cycle.
        
        Returns:
            Summary of processing
        """
        logger.info("librarian_cycle_started")
        
        initial_state = LibrarianState(
            messages=[],
            raw_documents=[],
            extracted_entities=[],
            current_batch=0,
            total_processed=0,
            errors=[],
        )
        
        try:
            final_state = await self.graph.ainvoke(initial_state)
            
            summary = {
                "documents_processed": len(final_state["raw_documents"]),
                "entities_extracted": len(final_state["extracted_entities"]),
                "total_processed": final_state["total_processed"],
                "errors": final_state["errors"],
                "timestamp": datetime.utcnow().isoformat(),
            }
            
            logger.info("librarian_cycle_complete", extra=summary)
            return summary
            
        except Exception as e:
            logger.exception("librarian_cycle_failed", extra={"error": str(e)})
            return {
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat(),
            }

    async def run_continuous(
        self, interval_minutes: int = 30, max_cycles: int = -1
    ) -> None:
        """
        Run continuous distillation loop.
        
        Args:
            interval_minutes: Minutes between cycles
            max_cycles: Maximum cycles to run (-1 for infinite)
        """
        logger.info(
            "librarian_continuous_started",
            extra={"interval_minutes": interval_minutes},
        )
        
        cycle = 0
        
        while max_cycles < 0 or cycle < max_cycles:
            try:
                summary = await self.run_distillation()
                
                logger.info(
                    "librarian_cycle_summary",
                    extra={"cycle": cycle, **summary},
                )
                
                # Sleep until next cycle
                import asyncio
                await asyncio.sleep(interval_minutes * 60)
                
                cycle += 1
                
            except Exception as e:
                logger.exception("librarian_continuous_error", extra={"error": str(e)})
                # Sleep and retry
                import asyncio
                await asyncio.sleep(60)

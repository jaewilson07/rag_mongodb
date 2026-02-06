"""
Librarian Agent: Distills raw chat logs into structured knowledge graph nodes.

Implements Tiago Forte's distillation approach:
1. Capture: Raw chat logs in MongoDB
2. Organize: Categorize and tag conversations
3. Distill: Extract key decisions, insights, and relationships
4. Express: Create Neo4j nodes with proper relationships
"""

import asyncio
import logging
from typing import Any, Optional

from langgraph.graph import StateGraph, END
from pydantic import BaseModel, Field

from neuralcursor.brain.neo4j.client import Neo4jClient
from neuralcursor.brain.neo4j.models import (
    ConversationNode,
    DecisionNode,
    Relationship,
    RelationType,
)
from neuralcursor.brain.mongodb.client import MongoDBClient, ConversationSession
from neuralcursor.llm.orchestrator import get_orchestrator, LLMRequest

logger = logging.getLogger(__name__)


class DistillationState(BaseModel):
    """State for the distillation workflow."""

    session: ConversationSession
    summary: Optional[str] = None
    key_points: list[str] = Field(default_factory=list)
    decisions: list[dict[str, Any]] = Field(default_factory=list)
    conversation_node_uid: Optional[str] = None
    error: Optional[str] = None


class LibrarianAgent:
    """
    Librarian agent that distills conversations into knowledge.
    
    Runs periodically in the background to process MongoDB chat logs
    and create structured Neo4j nodes.
    """

    def __init__(
        self,
        neo4j_client: Neo4jClient,
        mongodb_client: MongoDBClient,
    ):
        """
        Initialize Librarian agent.
        
        Args:
            neo4j_client: Neo4j client
            mongodb_client: MongoDB client
        """
        self.neo4j = neo4j_client
        self.mongodb = mongodb_client
        self.orchestrator = get_orchestrator()

        # Build the distillation workflow
        self.workflow = self._build_workflow()

    def _build_workflow(self) -> StateGraph:
        """
        Build LangGraph workflow for distillation.
        
        Returns:
            Compiled StateGraph
        """
        workflow = StateGraph(DistillationState)

        # Add nodes
        workflow.add_node("summarize", self._summarize_conversation)
        workflow.add_node("extract_decisions", self._extract_decisions)
        workflow.add_node("create_graph_nodes", self._create_graph_nodes)
        workflow.add_node("mark_complete", self._mark_complete)

        # Define edges
        workflow.set_entry_point("summarize")
        workflow.add_edge("summarize", "extract_decisions")
        workflow.add_edge("extract_decisions", "create_graph_nodes")
        workflow.add_edge("create_graph_nodes", "mark_complete")
        workflow.add_edge("mark_complete", END)

        return workflow.compile()

    async def _summarize_conversation(self, state: DistillationState) -> DistillationState:
        """
        Step 1: Summarize the conversation using reasoning LLM.
        
        Args:
            state: Current distillation state
            
        Returns:
            Updated state with summary
        """
        try:
            # Format conversation messages
            messages_text = "\n\n".join(
                [
                    f"[{msg.role}] {msg.content}"
                    for msg in state.session.messages
                ]
            )

            prompt = f"""Analyze the following conversation and provide:
1. A concise summary (2-3 sentences)
2. Key points discussed (bullet list)

Conversation:
{messages_text}

Provide your response in the following format:
SUMMARY:
[your summary here]

KEY POINTS:
- [point 1]
- [point 2]
- [point 3]
"""

            request = LLMRequest(
                prompt=prompt,
                max_tokens=1000,
                temperature=0.3,
            )

            response = await self.orchestrator.generate_reasoning(request)

            # Parse response
            response_text = response.text
            summary_section = response_text.split("KEY POINTS:")[0].replace("SUMMARY:", "").strip()
            key_points_section = response_text.split("KEY POINTS:")[1] if "KEY POINTS:" in response_text else ""

            key_points = [
                line.strip().lstrip("- ").lstrip("* ")
                for line in key_points_section.split("\n")
                if line.strip() and line.strip().startswith(("-", "*"))
            ]

            state.summary = summary_section
            state.key_points = key_points

            logger.info(
                "librarian_summarized",
                extra={
                    "session_id": state.session.session_id,
                    "key_points_count": len(key_points),
                },
            )

        except Exception as e:
            logger.exception("librarian_summarize_failed", extra={"error": str(e)})
            state.error = str(e)

        return state

    async def _extract_decisions(self, state: DistillationState) -> DistillationState:
        """
        Step 2: Extract architectural decisions from the conversation.
        
        Args:
            state: Current distillation state
            
        Returns:
            Updated state with decisions
        """
        if state.error:
            return state

        try:
            messages_text = "\n\n".join(
                [
                    f"[{msg.role}] {msg.content}"
                    for msg in state.session.messages
                ]
            )

            prompt = f"""Analyze this conversation and extract any significant architectural or design decisions.

For each decision, provide:
1. The decision made
2. The context that led to it
3. Why it was chosen (rationale)

Conversation:
{messages_text}

Format each decision as:
DECISION:
Context: [context]
Decision: [the decision]
Rationale: [why]
---
"""

            request = LLMRequest(
                prompt=prompt,
                max_tokens=1500,
                temperature=0.3,
            )

            response = await self.orchestrator.generate_reasoning(request)

            # Parse decisions
            decisions_text = response.text
            decision_blocks = [
                block.strip()
                for block in decisions_text.split("---")
                if "Decision:" in block
            ]

            decisions = []
            for block in decision_blocks:
                lines = block.split("\n")
                decision_dict = {}

                for line in lines:
                    if line.startswith("Context:"):
                        decision_dict["context"] = line.replace("Context:", "").strip()
                    elif line.startswith("Decision:"):
                        decision_dict["decision"] = line.replace("Decision:", "").strip()
                    elif line.startswith("Rationale:"):
                        decision_dict["rationale"] = line.replace("Rationale:", "").strip()

                if decision_dict.get("decision"):
                    decisions.append(decision_dict)

            state.decisions = decisions

            logger.info(
                "librarian_extracted_decisions",
                extra={
                    "session_id": state.session.session_id,
                    "decisions_count": len(decisions),
                },
            )

        except Exception as e:
            logger.exception("librarian_extract_failed", extra={"error": str(e)})
            state.error = str(e)

        return state

    async def _create_graph_nodes(self, state: DistillationState) -> DistillationState:
        """
        Step 3: Create nodes in Neo4j graph.
        
        Args:
            state: Current distillation state
            
        Returns:
            Updated state with node UIDs
        """
        if state.error:
            return state

        try:
            # Create ConversationNode
            conversation_node = ConversationNode(
                name=f"Conversation: {state.session.session_id[:12]}",
                description=state.summary,
                summary=state.summary or "",
                key_points=state.key_points,
                participants=["user", "assistant"],
                mongo_conversation_ids=[state.session.session_id],
            )

            conv_uid = await self.neo4j.create_node(conversation_node)
            state.conversation_node_uid = conv_uid

            logger.info(
                "librarian_created_conversation_node",
                extra={"session_id": state.session.session_id, "uid": conv_uid},
            )

            # Create DecisionNodes for each extracted decision
            for decision_data in state.decisions:
                decision_node = DecisionNode(
                    name=decision_data["decision"][:100],  # Truncate if too long
                    description=decision_data.get("rationale"),
                    context=decision_data["context"],
                    decision=decision_data["decision"],
                    rationale=decision_data.get("rationale"),
                    consequences=[],
                    alternatives=[],
                )

                decision_uid = await self.neo4j.create_node(decision_node)

                # Create relationship: ConversationNode -> DecisionNode
                relationship = Relationship(
                    from_uid=conv_uid,
                    to_uid=decision_uid,
                    relation_type=RelationType.CONTAINS,
                )

                await self.neo4j.create_relationship(relationship)

                logger.info(
                    "librarian_created_decision_node",
                    extra={"decision_uid": decision_uid, "conversation_uid": conv_uid},
                )

        except Exception as e:
            logger.exception("librarian_create_nodes_failed", extra={"error": str(e)})
            state.error = str(e)

        return state

    async def _mark_complete(self, state: DistillationState) -> DistillationState:
        """
        Step 4: Mark the session as distilled in MongoDB.
        
        Args:
            state: Current distillation state
            
        Returns:
            Updated state
        """
        if state.error or not state.conversation_node_uid:
            return state

        try:
            await self.mongodb.mark_session_distilled(
                state.session.session_id,
                state.conversation_node_uid,
            )

            logger.info(
                "librarian_marked_complete",
                extra={"session_id": state.session.session_id},
            )

        except Exception as e:
            logger.exception("librarian_mark_complete_failed", extra={"error": str(e)})
            state.error = str(e)

        return state

    async def distill_session(self, session: ConversationSession) -> Optional[str]:
        """
        Distill a single conversation session.
        
        Args:
            session: Conversation session to distill
            
        Returns:
            UID of created ConversationNode, or None if failed
        """
        initial_state = DistillationState(session=session)

        try:
            final_state = await self.workflow.ainvoke(initial_state)

            if final_state.get("error"):
                logger.error(
                    "librarian_distillation_failed",
                    extra={
                        "session_id": session.session_id,
                        "error": final_state["error"],
                    },
                )
                return None

            return final_state.get("conversation_node_uid")

        except Exception as e:
            logger.exception(
                "librarian_workflow_failed",
                extra={"session_id": session.session_id, "error": str(e)},
            )
            return None

    async def run_distillation_loop(
        self, interval_seconds: int = 300, batch_size: int = 5
    ) -> None:
        """
        Run continuous distillation loop in background.
        
        Args:
            interval_seconds: How often to check for new sessions
            batch_size: Max sessions to process per iteration
        """
        logger.info(
            "librarian_loop_started",
            extra={"interval_seconds": interval_seconds, "batch_size": batch_size},
        )

        while True:
            try:
                # Get sessions ready for distillation
                sessions = await self.mongodb.get_sessions_for_distillation(
                    min_messages=5
                )

                if sessions:
                    logger.info(
                        "librarian_processing_batch",
                        extra={"sessions_count": len(sessions)},
                    )

                    # Process sessions concurrently
                    tasks = [
                        self.distill_session(session)
                        for session in sessions[:batch_size]
                    ]

                    results = await asyncio.gather(*tasks, return_exceptions=True)

                    success_count = sum(1 for r in results if r and not isinstance(r, Exception))

                    logger.info(
                        "librarian_batch_complete",
                        extra={
                            "total": len(tasks),
                            "success": success_count,
                            "failed": len(tasks) - success_count,
                        },
                    )

                await asyncio.sleep(interval_seconds)

            except Exception as e:
                logger.exception("librarian_loop_error", extra={"error": str(e)})
                await asyncio.sleep(interval_seconds)

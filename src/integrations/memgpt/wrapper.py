"""MemGPT wrapper for NeuralCursor Second Brain."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

try:
    from letta import LettaClient, create_client

    LETTA_AVAILABLE = True
except ImportError:
    LETTA_AVAILABLE = False

from mdrag.capabilities.memory.gateway import MemoryGateway
from mdrag.settings import Settings

from .context_manager import ContextManager
from .tools import MemoryTools

logger = logging.getLogger(__name__)


class MemGPTWrapper:
    """
    MemGPT wrapper for stateful context management.

    This wrapper:
    - Manages MemGPT agent lifecycle
    - Registers Second Brain tools
    - Handles context paging between working memory and long-term storage
    - Maintains conversation state across sessions
    """

    def __init__(self, settings: Settings, memory_gateway: MemoryGateway):
        """
        Initialize MemGPT wrapper.

        Args:
            settings: Application settings
            memory_gateway: Memory gateway instance
        """
        if not LETTA_AVAILABLE:
            raise RuntimeError(
                "Letta (MemGPT) not installed. Install with: pip install letta"
            )

        self.settings = settings
        self.gateway = memory_gateway
        self.memory_tools = MemoryTools(memory_gateway)
        self.context_manager = ContextManager(memory_gateway)

        self.client: Optional[LettaClient] = None
        self.agent_id: Optional[str] = None
        self._initialized = False

    async def initialize(self, agent_name: str = "neuralcursor") -> None:
        """
        Initialize MemGPT client and agent.

        Args:
            agent_name: Name for the MemGPT agent
        """
        try:
            # Create Letta client
            self.client = create_client()
            logger.info("memgpt_client_created")

            # Try to get existing agent
            agents = self.client.list_agents()
            existing_agent = next((a for a in agents if a.name == agent_name), None)

            if existing_agent:
                self.agent_id = existing_agent.id
                logger.info("memgpt_agent_loaded", extra={"agent_id": self.agent_id})
            else:
                # Create new agent with custom tools
                agent = self.client.create_agent(
                    name=agent_name,
                    tools=[
                        "save_decision",
                        "save_requirement",
                        "save_code_entity",
                        "save_resource",
                        "query_why_code_exists",
                        "get_active_projects",
                        "save_episodic_memory",
                    ],
                    system=self._get_system_prompt(),
                )
                self.agent_id = agent.id
                logger.info("memgpt_agent_created", extra={"agent_id": self.agent_id})

            self._initialized = True

        except Exception as e:
            logger.exception("memgpt_initialization_failed", extra={"error": str(e)})
            raise

    def _get_system_prompt(self) -> str:
        """
        Get system prompt for MemGPT agent.

        Returns:
            System prompt
        """
        return """You are NeuralCursor, an intelligent Second Brain for software development.

Your purpose is to maintain a knowledge graph of architectural decisions, requirements, 
code entities, and their relationships. You have access to two memory systems:

1. **Structural Memory (Neo4j)**: For architectural knowledge
   - Projects, Areas, Decisions, Requirements, CodeEntity, Resources
   - Relationships like DEPENDS_ON, IMPLEMENTS, SUPERSEDES, INSPIRED_BY

2. **Episodic Memory (MongoDB)**: For conversation history and raw notes

## Your Responsibilities:

1. **Capture Context Automatically**: When developers discuss decisions, requirements, 
   or implementations, save them to the knowledge graph without being asked.

2. **Answer "Why" Questions**: When asked about code, trace back through the graph 
   to explain the original requirement, the decision made, and any resources that 
   inspired it.

3. **Maintain Relationships**: Always link new entities to their context:
   - Requirements → Decisions → CodeEntities
   - Resources → Decisions (via INSPIRED_BY)
   - Projects → Requirements, Decisions, CodeEntities

4. **Context Paging**: When your working memory fills up, proactively save important 
   context to long-term storage (Neo4j) while keeping the most relevant entities 
   in "Core Memory."

5. **Be Proactive**: Look for opportunities to structure unstructured information 
   into the knowledge graph.

## Example Interaction:

User: "I think we should use Redis for caching because the database queries are slow."

You should:
1. Save a Decision: "Use Redis for caching"
   - Rationale: "Database queries are slow, need performance improvement"
2. Save a Requirement: "Improve query performance"
   - Priority: high
3. Link them: Requirement → Decision

Then respond: "I've captured that architectural decision. I've linked it to the 
performance requirement. Would you like me to find similar patterns in other projects?"

Remember: The goal is "Architectural Intuition" - always know WHY code exists.
"""

    async def send_message(
        self, message: str, context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Send a message to MemGPT agent and get response.

        Args:
            message: User message
            context: Optional context dictionary

        Returns:
            Agent response
        """
        if not self._initialized:
            raise RuntimeError("MemGPT not initialized. Call initialize() first.")

        try:
            # Check if context paging is needed
            await self.context_manager.check_and_page_context(self.agent_id)

            # Send message
            response = self.client.send_message(
                agent_id=self.agent_id,
                message=message,
                role="user",
            )

            # Extract response text
            if isinstance(response, list):
                # Get the last assistant message
                assistant_messages = [
                    msg
                    for msg in response
                    if hasattr(msg, "role") and msg.role == "assistant"
                ]
                if assistant_messages:
                    response_text = assistant_messages[-1].text
                else:
                    response_text = str(response[-1]) if response else "No response"
            else:
                response_text = str(response)

            logger.info(
                "memgpt_message_sent",
                extra={
                    "message_length": len(message),
                    "response_length": len(response_text),
                },
            )

            return response_text

        except Exception as e:
            logger.exception("memgpt_message_failed", extra={"error": str(e)})
            raise

    async def get_conversation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get conversation history for current agent.

        Args:
            limit: Maximum messages to retrieve

        Returns:
            List of messages
        """
        if not self._initialized:
            raise RuntimeError("MemGPT not initialized. Call initialize() first.")

        try:
            messages = self.client.get_messages(
                agent_id=self.agent_id,
                limit=limit,
            )

            return [
                {
                    "role": msg.role if hasattr(msg, "role") else "unknown",
                    "content": msg.text if hasattr(msg, "text") else str(msg),
                    "timestamp": msg.created_at if hasattr(msg, "created_at") else None,
                }
                for msg in messages
            ]

        except Exception as e:
            logger.exception("memgpt_history_failed", extra={"error": str(e)})
            return []

    async def save_conversation_checkpoint(self) -> str:
        """
        Save current conversation state as a checkpoint.

        Returns:
            Checkpoint ID
        """
        if not self._initialized:
            raise RuntimeError("MemGPT not initialized. Call initialize() first.")

        try:
            # Get current state
            agent_state = self.client.get_agent(self.agent_id)

            # Save to MongoDB as episodic memory
            checkpoint_data = {
                "agent_id": self.agent_id,
                "agent_name": agent_state.name
                if hasattr(agent_state, "name")
                else "unknown",
                "timestamp": datetime.utcnow().isoformat(),
                "state": "checkpoint",
            }

            checkpoint_id = await self.memory_tools.save_episodic_memory(
                content=f"Conversation checkpoint for agent {self.agent_id}",
                metadata=checkpoint_data,
            )

            logger.info(
                "memgpt_checkpoint_saved", extra={"checkpoint_id": checkpoint_id}
            )
            return checkpoint_id

        except Exception as e:
            logger.exception("memgpt_checkpoint_failed", extra={"error": str(e)})
            raise

    async def restore_from_checkpoint(self, checkpoint_id: str) -> None:
        """
        Restore conversation state from a checkpoint.

        Args:
            checkpoint_id: Checkpoint ID to restore
        """
        if not self._initialized:
            raise RuntimeError("MemGPT not initialized. Call initialize() first.")

        logger.info("memgpt_checkpoint_restore", extra={"checkpoint_id": checkpoint_id})
        # Implementation would restore agent state from checkpoint
        # This is a placeholder for the actual restoration logic

    async def close(self) -> None:
        """Close MemGPT client and save final state."""
        if self._initialized:
            await self.save_conversation_checkpoint()
            logger.info("memgpt_wrapper_closed")

"""Context manager for autonomous context paging."""

import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from mdrag.capabilities.memory.gateway import MemoryGateway
from mdrag.capabilities.memory.models import WorkingSet

logger = logging.getLogger(__name__)


class ContextManager:
    """
    Manages context paging between working memory and long-term storage.
    
    This implements the "Working Set" logic where:
    - Recently accessed entities stay in "Core Memory" (hot)
    - Inactive entities are paged to "Cold Storage" but remain searchable
    - Context window management prevents overflow
    """

    def __init__(
        self,
        memory_gateway: MemoryGateway,
        core_memory_limit: int = 20,
        context_window_tokens: int = 8192,
    ):
        """
        Initialize context manager.
        
        Args:
            memory_gateway: Memory gateway instance
            core_memory_limit: Maximum entities in core memory
            context_window_tokens: Estimated context window size
        """
        self.gateway = memory_gateway
        self.core_memory_limit = core_memory_limit
        self.context_window_tokens = context_window_tokens
        self.working_set: Optional[WorkingSet] = None
        self._last_update = datetime.utcnow()

    async def check_and_page_context(self, agent_id: str) -> None:
        """
        Check if context paging is needed and perform it.
        
        Args:
            agent_id: MemGPT agent ID
        """
        # Update working set if stale (> 5 minutes)
        if (
            not self.working_set
            or (datetime.utcnow() - self._last_update) > timedelta(minutes=5)
        ):
            await self.refresh_working_set()
        
        # Check if core memory needs paging
        if len(self.working_set.core_memory) > self.core_memory_limit:
            await self.page_context()

    async def refresh_working_set(self) -> None:
        """Refresh working set from memory gateway."""
        self.working_set = await self.gateway.get_working_set()
        self._last_update = datetime.utcnow()
        
        logger.info(
            "context_working_set_refreshed",
            extra={
                "active_projects": len(self.working_set.active_projects),
                "active_files": len(self.working_set.active_files),
                "core_memory_size": len(self.working_set.core_memory),
            },
        )

    async def page_context(self) -> None:
        """
        Page context from core memory to cold storage.
        
        Move least recently used entities from core memory to cold storage.
        """
        if not self.working_set:
            await self.refresh_working_set()
        
        # Sort core memory by last access time
        sorted_memory = sorted(
            self.working_set.core_memory,
            key=lambda x: x.get("last_accessed", datetime.min.isoformat()),
        )
        
        # Calculate how many to page out
        overflow = len(sorted_memory) - self.core_memory_limit
        
        if overflow > 0:
            # Page out oldest entities
            to_page = sorted_memory[:overflow]
            
            for entity in to_page:
                entity_uuid = entity.get("uuid")
                if entity_uuid:
                    self.working_set.cold_storage.append(entity_uuid)
                    self.working_set.core_memory.remove(entity)
            
            logger.info(
                "context_paged",
                extra={
                    "paged_count": len(to_page),
                    "remaining_core": len(self.working_set.core_memory),
                },
            )

    async def promote_to_core(self, entity_uuid: str, entity_data: Dict[str, Any]) -> None:
        """
        Promote an entity from cold storage to core memory.
        
        Args:
            entity_uuid: Entity UUID
            entity_data: Entity data
        """
        if not self.working_set:
            await self.refresh_working_set()
        
        # Remove from cold storage if present
        if entity_uuid in self.working_set.cold_storage:
            self.working_set.cold_storage.remove(entity_uuid)
        
        # Add to core memory with access timestamp
        entity_data["last_accessed"] = datetime.utcnow().isoformat()
        self.working_set.core_memory.append(entity_data)
        
        # Check if paging is needed
        if len(self.working_set.core_memory) > self.core_memory_limit:
            await self.page_context()
        
        logger.info(
            "context_promoted_to_core",
            extra={"entity_uuid": entity_uuid},
        )

    async def get_context_summary(self) -> str:
        """
        Get human-readable summary of current context.
        
        Returns:
            Context summary
        """
        if not self.working_set:
            await self.refresh_working_set()
        
        summary = [
            "# Current Context Summary",
            f"\n## Active Projects: {len(self.working_set.active_projects)}",
        ]
        
        for project_uuid in self.working_set.active_projects[:5]:
            node = await self.gateway.neo4j_client.get_node(project_uuid)
            if node:
                summary.append(f"- {node.get('name', 'Unknown')}")
        
        summary.extend([
            f"\n## Recently Active Files: {len(self.working_set.active_files)}",
        ])
        
        for file_path in self.working_set.active_files[:10]:
            summary.append(f"- {file_path}")
        
        summary.extend([
            f"\n## Core Memory: {len(self.working_set.core_memory)} entities",
            f"## Cold Storage: {len(self.working_set.cold_storage)} entities",
            f"\nLast Updated: {self.working_set.last_updated}",
        ])
        
        return "\n".join(summary)

    async def archive_project_context(self, project_uuid: str) -> None:
        """
        Archive all context for a completed project.
        
        Args:
            project_uuid: Project UUID to archive
        """
        from mdrag.integrations.neo4j.queries import SecondBrainQueries
        
        # Archive project and related entities
        query, params = SecondBrainQueries.archive_completed_project(project_uuid)
        await self.gateway.neo4j_client.execute_cypher(query, params)
        
        # Remove from working set
        if self.working_set and project_uuid in self.working_set.active_projects:
            self.working_set.active_projects.remove(project_uuid)
        
        logger.info(
            "context_project_archived",
            extra={"project_uuid": project_uuid},
        )

    async def estimate_context_size(self) -> int:
        """
        Estimate current context size in tokens.
        
        Returns:
            Estimated token count
        """
        if not self.working_set:
            await self.refresh_working_set()
        
        # Rough estimate: 4 characters per token
        total_chars = 0
        
        for entity in self.working_set.core_memory:
            # Estimate entity size
            entity_str = str(entity)
            total_chars += len(entity_str)
        
        estimated_tokens = total_chars // 4
        
        return estimated_tokens

"""Graph pruning and optimization routines."""

import logging
from typing import List, Dict, Any
from datetime import datetime

from mdrag.capabilities.memory.gateway import MemoryGateway
from mdrag.integrations.neo4j.queries import SecondBrainQueries

logger = logging.getLogger(__name__)


class GraphOptimizer:
    """
    Maintains knowledge graph health through:
    - Deduplication of duplicate nodes
    - Pruning of stale/obsolete entities
    - Relationship cleanup
    - Archive old projects
    """

    def __init__(self, memory_gateway: MemoryGateway):
        """
        Initialize graph optimizer.
        
        Args:
            memory_gateway: Memory gateway instance
        """
        self.gateway = memory_gateway

    async def run_brain_care_cycle(self) -> Dict[str, Any]:
        """
        Run a complete "Brain Care" cycle.
        
        Returns:
            Summary of operations performed
        """
        logger.info("graph_optimizer_cycle_started")
        
        summary = {
            "timestamp": datetime.utcnow().isoformat(),
            "duplicates_merged": 0,
            "stale_decisions_found": 0,
            "broken_links_fixed": 0,
            "projects_archived": 0,
            "orphaned_nodes_removed": 0,
        }
        
        try:
            # 1. Find and merge duplicates
            summary["duplicates_merged"] = await self.merge_duplicate_nodes()
            
            # 2. Find stale decisions
            summary["stale_decisions_found"] = await self.find_stale_decisions()
            
            # 3. Fix broken relationships
            summary["broken_links_fixed"] = await self.fix_broken_relationships()
            
            # 4. Archive completed projects
            summary["projects_archived"] = await self.archive_completed_projects()
            
            # 5. Remove orphaned nodes
            summary["orphaned_nodes_removed"] = await self.remove_orphaned_nodes()
            
            logger.info("graph_optimizer_cycle_complete", extra=summary)
            return summary
            
        except Exception as e:
            logger.exception("graph_optimizer_cycle_failed", extra={"error": str(e)})
            summary["error"] = str(e)
            return summary

    async def merge_duplicate_nodes(self) -> int:
        """
        Find and merge duplicate nodes based on name similarity.
        
        Returns:
            Number of duplicates merged
        """
        logger.info("graph_optimizer_finding_duplicates")
        
        # Find nodes with same name and type
        query = """
        MATCH (n1), (n2)
        WHERE n1.name = n2.name
          AND labels(n1) = labels(n2)
          AND n1.uuid < n2.uuid
        RETURN n1.uuid as uuid1, n2.uuid as uuid2, n1.name as name, labels(n1)[0] as type
        LIMIT 100
        """
        
        duplicates = await self.gateway.neo4j_client.execute_cypher(query)
        
        merged_count = 0
        
        for dup in duplicates:
            try:
                # Merge relationships from n2 to n1
                await self._merge_node_relationships(dup["uuid2"], dup["uuid1"])
                
                # Delete n2
                await self.gateway.neo4j_client.delete_node(dup["uuid2"])
                
                merged_count += 1
                logger.info(
                    "graph_optimizer_nodes_merged",
                    extra={
                        "name": dup["name"],
                        "type": dup["type"],
                        "kept": dup["uuid1"],
                        "removed": dup["uuid2"],
                    },
                )
                
            except Exception as e:
                logger.exception(
                    "graph_optimizer_merge_failed",
                    extra={"duplicate": dup, "error": str(e)},
                )
        
        logger.info(
            "graph_optimizer_duplicates_merged",
            extra={"count": merged_count},
        )
        return merged_count

    async def _merge_node_relationships(self, source_uuid: str, target_uuid: str) -> None:
        """
        Merge all relationships from source node to target node.
        
        Args:
            source_uuid: Source node UUID (will be deleted)
            target_uuid: Target node UUID (will be kept)
        """
        # Get all outgoing relationships from source
        query_out = """
        MATCH (source {uuid: $source_uuid})-[r]->(dest)
        RETURN type(r) as rel_type, dest.uuid as dest_uuid, properties(r) as props
        """
        
        out_rels = await self.gateway.neo4j_client.execute_cypher(
            query_out, {"source_uuid": source_uuid}
        )
        
        # Recreate relationships from target
        for rel in out_rels:
            merge_query = f"""
            MATCH (target {{uuid: $target_uuid}})
            MATCH (dest {{uuid: $dest_uuid}})
            MERGE (target)-[r:{rel['rel_type']}]->(dest)
            SET r = $props
            """
            await self.gateway.neo4j_client.execute_cypher(
                merge_query,
                {
                    "target_uuid": target_uuid,
                    "dest_uuid": rel["dest_uuid"],
                    "props": rel["props"],
                },
            )
        
        # Get all incoming relationships to source
        query_in = """
        MATCH (origin)-[r]->(source {uuid: $source_uuid})
        RETURN type(r) as rel_type, origin.uuid as origin_uuid, properties(r) as props
        """
        
        in_rels = await self.gateway.neo4j_client.execute_cypher(
            query_in, {"source_uuid": source_uuid}
        )
        
        # Recreate relationships to target
        for rel in in_rels:
            merge_query = f"""
            MATCH (origin {{uuid: $origin_uuid}})
            MATCH (target {{uuid: $target_uuid}})
            MERGE (origin)-[r:{rel['rel_type']}]->(target)
            SET r = $props
            """
            await self.gateway.neo4j_client.execute_cypher(
                merge_query,
                {
                    "origin_uuid": rel["origin_uuid"],
                    "target_uuid": target_uuid,
                    "props": rel["props"],
                },
            )

    async def find_stale_decisions(self, days_threshold: int = 90) -> int:
        """
        Find decisions that haven't been updated in a long time.
        
        Args:
            days_threshold: Number of days to consider stale
            
        Returns:
            Number of stale decisions found
        """
        logger.info("graph_optimizer_finding_stale_decisions")
        
        query, params = SecondBrainQueries.find_stale_decisions(days_threshold)
        stale = await self.gateway.neo4j_client.execute_cypher(query, params)
        
        if stale:
            logger.warning(
                "graph_optimizer_stale_decisions_found",
                extra={"count": len(stale), "threshold_days": days_threshold},
            )
            
            # Log each stale decision
            for dec in stale[:10]:  # Log first 10
                logger.info(
                    "graph_optimizer_stale_decision",
                    extra={
                        "name": dec.get("name"),
                        "last_updated": dec.get("last_updated"),
                        "affected_code_count": dec.get("affected_code_count", 0),
                    },
                )
        
        return len(stale)

    async def fix_broken_relationships(self) -> int:
        """
        Find and fix broken relationships (pointing to non-existent nodes).
        
        Returns:
            Number of broken relationships fixed
        """
        logger.info("graph_optimizer_fixing_broken_links")
        
        # Find relationships pointing to non-existent nodes
        query = """
        MATCH (n)-[r]->()
        WHERE NOT EXISTS {
            MATCH (target {uuid: endNode(r).uuid})
        }
        RETURN id(r) as rel_id, type(r) as rel_type, n.uuid as source_uuid
        LIMIT 100
        """
        
        broken = await self.gateway.neo4j_client.execute_cypher(query)
        
        # Delete broken relationships
        for rel in broken:
            delete_query = """
            MATCH ()-[r]->()
            WHERE id(r) = $rel_id
            DELETE r
            """
            await self.gateway.neo4j_client.execute_cypher(
                delete_query, {"rel_id": rel["rel_id"]}
            )
        
        if broken:
            logger.warning(
                "graph_optimizer_broken_links_fixed",
                extra={"count": len(broken)},
            )
        
        return len(broken)

    async def archive_completed_projects(self) -> int:
        """
        Archive projects marked as completed.
        
        Returns:
            Number of projects archived
        """
        logger.info("graph_optimizer_archiving_projects")
        
        # Find completed projects not yet archived
        query = """
        MATCH (p:Project {status: 'completed'})
        WHERE NOT p:Archive
        RETURN p.uuid as uuid, p.name as name
        """
        
        completed = await self.gateway.neo4j_client.execute_cypher(query)
        
        archived_count = 0
        
        for project in completed:
            try:
                archive_query, params = SecondBrainQueries.archive_completed_project(
                    project["uuid"]
                )
                await self.gateway.neo4j_client.execute_cypher(archive_query, params)
                
                archived_count += 1
                logger.info(
                    "graph_optimizer_project_archived",
                    extra={"name": project["name"], "uuid": project["uuid"]},
                )
                
            except Exception as e:
                logger.exception(
                    "graph_optimizer_archive_failed",
                    extra={"project": project, "error": str(e)},
                )
        
        return archived_count

    async def remove_orphaned_nodes(self) -> int:
        """
        Remove nodes with no relationships (orphaned).
        
        Returns:
            Number of orphaned nodes removed
        """
        logger.info("graph_optimizer_removing_orphans")
        
        # Find nodes with no relationships
        query = """
        MATCH (n)
        WHERE NOT (n)-[]-() AND NOT n:Project AND NOT n:Area
        RETURN n.uuid as uuid, labels(n)[0] as type, n.name as name
        LIMIT 100
        """
        
        orphans = await self.gateway.neo4j_client.execute_cypher(query)
        
        removed_count = 0
        
        for orphan in orphans:
            try:
                await self.gateway.neo4j_client.delete_node(orphan["uuid"])
                removed_count += 1
                
                logger.info(
                    "graph_optimizer_orphan_removed",
                    extra={"name": orphan["name"], "type": orphan["type"]},
                )
                
            except Exception as e:
                logger.exception(
                    "graph_optimizer_orphan_removal_failed",
                    extra={"orphan": orphan, "error": str(e)},
                )
        
        if removed_count > 0:
            logger.info(
                "graph_optimizer_orphans_removed",
                extra={"count": removed_count},
            )
        
        return removed_count

    async def get_optimization_recommendations(self) -> List[str]:
        """
        Analyze graph and provide optimization recommendations.
        
        Returns:
            List of recommendation strings
        """
        recommendations = []
        
        # Get graph stats
        stats = await self.gateway.get_graph_stats()
        
        # Check for imbalances
        if stats.node_counts.get("Decision", 0) < stats.node_counts.get("CodeEntity", 0) * 0.1:
            recommendations.append(
                "Low Decision-to-Code ratio. Consider documenting more architectural decisions."
            )
        
        if stats.node_counts.get("Requirement", 0) < stats.node_counts.get("Decision", 0) * 0.5:
            recommendations.append(
                "Low Requirement-to-Decision ratio. Consider linking decisions to requirements."
            )
        
        if stats.active_projects > 10:
            recommendations.append(
                f"{stats.active_projects} active projects. Consider archiving completed ones."
            )
        
        # Check for stale decisions
        stale_count = await self.find_stale_decisions(days_threshold=90)
        if stale_count > 5:
            recommendations.append(
                f"{stale_count} decisions haven't been updated in 90+ days. Review for relevance."
            )
        
        return recommendations

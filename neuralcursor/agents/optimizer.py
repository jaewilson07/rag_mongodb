"""
Graph Optimizer: Weekly "Brain Care" routines.

Performs:
1. Duplicate node detection and merging
2. Broken relationship cleanup
3. Archive management (move completed projects)
4. Graph statistics and health metrics
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any

from neuralcursor.brain.neo4j.client import Neo4jClient

logger = logging.getLogger(__name__)


class GraphOptimizer:
    """
    Maintains graph health through periodic optimization.
    
    Runs weekly "Brain Care" routines to keep the knowledge graph clean,
    fast, and accurate.
    """

    def __init__(self, neo4j_client: Neo4jClient):
        """
        Initialize optimizer.
        
        Args:
            neo4j_client: Neo4j client
        """
        self.neo4j = neo4j_client

    async def find_duplicate_nodes(self) -> list[dict[str, Any]]:
        """
        Find potential duplicate nodes based on name similarity.
        
        Returns:
            List of duplicate candidate pairs
        """
        cypher = """
        MATCH (n1), (n2)
        WHERE id(n1) < id(n2)
          AND labels(n1) = labels(n2)
          AND n1.name = n2.name
          AND NOT n1.archived = true
          AND NOT n2.archived = true
        RETURN 
            n1.uid as uid1,
            n2.uid as uid2,
            n1.name as name,
            labels(n1) as type
        LIMIT 50
        """

        results = await self.neo4j.query(cypher)

        logger.info(
            "optimizer_found_duplicates",
            extra={"duplicates_count": len(results)},
        )

        return results

    async def merge_duplicate_nodes(
        self, uid1: str, uid2: str, keep_uid: str
    ) -> bool:
        """
        Merge two duplicate nodes, keeping one and archiving the other.
        
        Args:
            uid1: First node UID
            uid2: Second node UID
            keep_uid: UID of node to keep
            
        Returns:
            True if merge succeeded
        """
        try:
            archive_uid = uid2 if keep_uid == uid1 else uid1

            # Transfer relationships from archived node to kept node
            cypher = """
            MATCH (archived {uid: $archive_uid})-[r]->(other)
            MATCH (keep {uid: $keep_uid})
            WHERE NOT (keep)-[:${type(r)}]->(other)
            CREATE (keep)-[new:${type(r)}]->(other)
            SET new = properties(r)
            
            WITH archived, keep
            MATCH (other)-[r]->(archived)
            WHERE NOT (other)-[:${type(r)}]->(keep)
            CREATE (other)-[new:${type(r)}]->(keep)
            SET new = properties(r)
            
            WITH archived
            SET archived.archived = true,
                archived.archived_at = datetime(),
                archived.merge_reason = 'duplicate'
            """

            await self.neo4j.query(
                cypher,
                {"archive_uid": archive_uid, "keep_uid": keep_uid},
            )

            logger.info(
                "optimizer_merged_duplicates",
                extra={"kept": keep_uid, "archived": archive_uid},
            )

            return True

        except Exception as e:
            logger.exception("optimizer_merge_failed", extra={"error": str(e)})
            return False

    async def cleanup_broken_relationships(self) -> int:
        """
        Remove relationships that point to non-existent nodes.
        
        Returns:
            Number of broken relationships removed
        """
        # Neo4j typically handles this automatically, but we can check
        cypher = """
        MATCH ()-[r]->()
        WHERE NOT exists((startNode(r))) OR NOT exists((endNode(r)))
        DELETE r
        RETURN count(r) as deleted
        """

        results = await self.neo4j.query(cypher)
        deleted = results[0]["deleted"] if results else 0

        if deleted > 0:
            logger.info(
                "optimizer_cleaned_broken_relationships",
                extra={"deleted_count": deleted},
            )

        return deleted

    async def archive_completed_projects(self, days_inactive: int = 90) -> int:
        """
        Move completed projects to Archive that haven't been touched in X days.
        
        Args:
            days_inactive: Days of inactivity threshold
            
        Returns:
            Number of projects archived
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days_inactive)

        cypher = """
        MATCH (p:Project)
        WHERE p.status = 'completed'
          AND p.updated_at < datetime($cutoff_date)
          AND NOT p.archived = true
        SET p.archived = true,
            p.archived_at = datetime(),
            p.archive_reason = 'completed_and_inactive'
        RETURN count(p) as archived
        """

        results = await self.neo4j.query(
            cypher, {"cutoff_date": cutoff_date.isoformat()}
        )
        archived = results[0]["archived"] if results else 0

        if archived > 0:
            logger.info(
                "optimizer_archived_projects",
                extra={"archived_count": archived, "days_inactive": days_inactive},
            )

        return archived

    async def compute_graph_stats(self) -> dict[str, Any]:
        """
        Compute comprehensive graph statistics.
        
        Returns:
            Dictionary with graph health metrics
        """
        stats = {}

        # Node counts by type
        node_count_cypher = """
        MATCH (n)
        RETURN labels(n)[0] as type, count(n) as count
        ORDER BY count DESC
        """
        node_results = await self.neo4j.query(node_count_cypher)
        stats["nodes_by_type"] = {
            record["type"]: record["count"] for record in node_results
        }
        stats["total_nodes"] = sum(stats["nodes_by_type"].values())

        # Relationship counts by type
        rel_count_cypher = """
        MATCH ()-[r]->()
        RETURN type(r) as type, count(r) as count
        ORDER BY count DESC
        """
        rel_results = await self.neo4j.query(rel_count_cypher)
        stats["relationships_by_type"] = {
            record["type"]: record["count"] for record in rel_results
        }
        stats["total_relationships"] = sum(stats["relationships_by_type"].values())

        # Archived vs active
        archived_cypher = """
        MATCH (n)
        RETURN 
            sum(CASE WHEN n.archived = true THEN 1 ELSE 0 END) as archived,
            sum(CASE WHEN n.archived <> true THEN 1 ELSE 0 END) as active
        """
        archived_results = await self.neo4j.query(archived_cypher)
        if archived_results:
            stats["archived_nodes"] = archived_results[0]["archived"]
            stats["active_nodes"] = archived_results[0]["active"]

        # Orphaned nodes (no relationships)
        orphan_cypher = """
        MATCH (n)
        WHERE NOT (n)--()
          AND NOT n.archived = true
        RETURN count(n) as orphans
        """
        orphan_results = await self.neo4j.query(orphan_cypher)
        stats["orphaned_nodes"] = orphan_results[0]["orphans"] if orphan_results else 0

        # Most connected nodes
        connected_cypher = """
        MATCH (n)-[r]-()
        WHERE NOT n.archived = true
        RETURN n.uid as uid, n.name as name, labels(n)[0] as type, count(r) as connections
        ORDER BY connections DESC
        LIMIT 10
        """
        connected_results = await self.neo4j.query(connected_cypher)
        stats["most_connected"] = connected_results

        return stats

    async def run_optimization_cycle(self) -> dict[str, Any]:
        """
        Run a complete optimization cycle.
        
        Returns:
            Summary of optimization actions
        """
        logger.info("optimizer_cycle_started")

        summary = {
            "started_at": datetime.utcnow().isoformat(),
            "actions": {},
        }

        try:
            # 1. Find and report duplicates (don't auto-merge, require manual review)
            duplicates = await self.find_duplicate_nodes()
            summary["actions"]["duplicates_found"] = len(duplicates)

            # 2. Cleanup broken relationships
            broken_cleaned = await self.cleanup_broken_relationships()
            summary["actions"]["broken_relationships_cleaned"] = broken_cleaned

            # 3. Archive old completed projects
            projects_archived = await self.archive_completed_projects()
            summary["actions"]["projects_archived"] = projects_archived

            # 4. Compute stats
            stats = await self.compute_graph_stats()
            summary["graph_stats"] = stats

            # Health score (simple heuristic)
            health_score = 100
            if stats["orphaned_nodes"] > 10:
                health_score -= 10
            if len(duplicates) > 5:
                health_score -= 10
            if stats.get("total_nodes", 0) > 10000:
                health_score -= 5  # Performance warning

            summary["health_score"] = max(0, health_score)
            summary["completed_at"] = datetime.utcnow().isoformat()

            logger.info(
                "optimizer_cycle_completed",
                extra={"health_score": summary["health_score"]},
            )

        except Exception as e:
            logger.exception("optimizer_cycle_failed", extra={"error": str(e)})
            summary["error"] = str(e)

        return summary

    async def run_weekly_cycle(self, interval_days: int = 7) -> None:
        """
        Run optimization cycle on a weekly schedule.
        
        Args:
            interval_days: Days between optimization cycles
        """
        logger.info(
            "optimizer_weekly_cycle_started",
            extra={"interval_days": interval_days},
        )

        while True:
            try:
                summary = await self.run_optimization_cycle()

                # Log summary
                logger.info(
                    "optimizer_weekly_summary",
                    extra={
                        "health_score": summary.get("health_score"),
                        "actions": summary.get("actions"),
                    },
                )

            except Exception as e:
                logger.exception("optimizer_weekly_cycle_error", extra={"error": str(e)})

            # Wait for next cycle
            await asyncio.sleep(interval_days * 24 * 3600)

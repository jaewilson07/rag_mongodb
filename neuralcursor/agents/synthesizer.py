"""
Cross-Project Synthesizer: Discovers patterns across different projects.

Finds:
1. Reusable utility functions
2. Common design patterns
3. Shared architectural decisions
4. Knowledge transfer opportunities
"""

import logging
from typing import Any

from neuralcursor.brain.neo4j.client import Neo4jClient
from neuralcursor.llm.orchestrator import get_orchestrator, LLMRequest

logger = logging.getLogger(__name__)


class CrossProjectSynthesizer:
    """
    Discovers patterns and reusable components across projects.
    
    Example: Finding a utility function in "Van Conversion" project
    that could be useful in "NerdBbB" project.
    """

    def __init__(self, neo4j_client: Neo4jClient):
        """
        Initialize synthesizer.
        
        Args:
            neo4j_client: Neo4j client
        """
        self.neo4j = neo4j_client
        self.orchestrator = get_orchestrator()

    async def find_similar_patterns(
        self, project_uid: str
    ) -> list[dict[str, Any]]:
        """
        Find similar patterns across different projects.
        
        Args:
            project_uid: Source project UID
            
        Returns:
            List of similar patterns found in other projects
        """
        # Get source project details
        project = await self.neo4j.get_node(project_uid)
        if not project:
            return []

        project_name = project.get("name", "")

        # Find code entities in this project
        cypher = """
        MATCH (p:Project {uid: $uid})-[:CONTAINS]->(code:CodeEntity)
        WHERE NOT code.archived = true
        RETURN code.uid as uid, code.name as name, code.entity_type as type
        LIMIT 50
        """

        entities = await self.neo4j.query(cypher, {"uid": project_uid})

        similar_patterns = []

        for entity in entities[:10]:  # Analyze top 10 entities
            entity_name = entity.get("name", "")

            # Find similarly named entities in other projects
            similar_cypher = """
            MATCH (code1:CodeEntity {uid: $uid})
            MATCH (code2:CodeEntity)
            WHERE code2.uid <> $uid
              AND NOT code2.archived = true
              AND (
                code1.name = code2.name
                OR code1.entity_type = code2.entity_type
              )
            MATCH (code2)<-[:CONTAINS]-(other_project:Project)
            WHERE other_project.uid <> $project_uid
            RETURN 
                code2.uid as similar_uid,
                code2.name as similar_name,
                other_project.uid as other_project_uid,
                other_project.name as other_project_name
            LIMIT 5
            """

            similar = await self.neo4j.query(
                similar_cypher,
                {"uid": entity["uid"], "project_uid": project_uid},
            )

            for match in similar:
                similar_patterns.append(
                    {
                        "source_entity": entity_name,
                        "source_project": project_name,
                        "similar_entity": match["similar_name"],
                        "target_project": match["other_project_name"],
                        "similarity_type": "name_match",
                    }
                )

        logger.info(
            "synthesizer_found_patterns",
            extra={
                "project": project_name,
                "patterns_count": len(similar_patterns),
            },
        )

        return similar_patterns

    async def discover_reusable_utilities(self) -> list[dict[str, Any]]:
        """
        Discover utility functions that appear useful across projects.
        
        Returns:
            List of potentially reusable utilities
        """
        # Find functions that are used multiple times within a project
        # (high internal connectivity suggests utility value)
        cypher = """
        MATCH (code:CodeEntity {entity_type: 'function'})
        WHERE NOT code.archived = true
        MATCH (code)<-[:DEPENDS_ON]-(dependent)
        WITH code, count(dependent) as usage_count
        WHERE usage_count >= 3
        MATCH (code)<-[:CONTAINS]-(project:Project)
        RETURN 
            code.uid as uid,
            code.name as name,
            code.file_path as file_path,
            project.name as project,
            usage_count
        ORDER BY usage_count DESC
        LIMIT 20
        """

        results = await self.neo4j.query(cypher)

        utilities = []

        for record in results:
            utilities.append(
                {
                    "uid": record["uid"],
                    "name": record["name"],
                    "file_path": record["file_path"],
                    "project": record["project"],
                    "usage_count": record["usage_count"],
                    "suggestion": f"Consider extracting '{record['name']}' to a shared utility library",
                }
            )

        logger.info(
            "synthesizer_found_utilities",
            extra={"utilities_count": len(utilities)},
        )

        return utilities

    async def find_common_decisions(self) -> list[dict[str, Any]]:
        """
        Find architectural decisions that appear across multiple projects.
        
        Returns:
            List of common decision patterns
        """
        # Find decisions with similar context/keywords
        cypher = """
        MATCH (d1:Decision)-[:BELONGS_TO]->(p1:Project)
        MATCH (d2:Decision)-[:BELONGS_TO]->(p2:Project)
        WHERE p1.uid <> p2.uid
          AND NOT d1.archived = true
          AND NOT d2.archived = true
          AND (
            d1.context CONTAINS d2.context
            OR d2.context CONTAINS d1.context
          )
        RETURN 
            d1.uid as decision1_uid,
            d1.decision as decision1,
            p1.name as project1,
            d2.uid as decision2_uid,
            d2.decision as decision2,
            p2.name as project2
        LIMIT 20
        """

        results = await self.neo4j.query(cypher)

        common_decisions = []

        for record in results:
            # Use LLM to verify they're actually similar
            similarity = await self._check_decision_similarity(
                record["decision1"], record["decision2"]
            )

            if similarity:
                common_decisions.append(
                    {
                        "decision1_uid": record["decision1_uid"],
                        "decision1": record["decision1"],
                        "project1": record["project1"],
                        "decision2_uid": record["decision2_uid"],
                        "decision2": record["decision2"],
                        "project2": record["project2"],
                        "similarity_score": similarity.get("score", 0),
                        "pattern": similarity.get("pattern"),
                    }
                )

        logger.info(
            "synthesizer_found_common_decisions",
            extra={"common_decisions_count": len(common_decisions)},
        )

        return common_decisions

    async def _check_decision_similarity(
        self, decision1: str, decision2: str
    ) -> dict[str, Any] | None:
        """
        Use LLM to check if two decisions are similar.
        
        Args:
            decision1: First decision text
            decision2: Second decision text
            
        Returns:
            Similarity details if similar, None otherwise
        """
        try:
            prompt = f"""Compare these two architectural decisions:

Decision 1:
{decision1}

Decision 2:
{decision2}

Are these decisions similar or following the same pattern?

Respond in this format:
SIMILAR: [YES or NO]
SCORE: [0-100]
PATTERN: [common pattern they share, if any]
"""

            request = LLMRequest(
                prompt=prompt,
                max_tokens=300,
                temperature=0.2,
            )

            response = await self.orchestrator.generate_reasoning(request)

            response_text = response.text.lower()

            if "similar: yes" in response_text:
                # Extract score and pattern
                lines = response.text.split("\n")
                score = 50  # default
                pattern = ""

                for line in lines:
                    if line.startswith("SCORE:"):
                        try:
                            score = int(line.replace("SCORE:", "").strip())
                        except ValueError:
                            pass
                    elif line.startswith("PATTERN:"):
                        pattern = line.replace("PATTERN:", "").strip()

                return {"score": score, "pattern": pattern}

            return None

        except Exception as e:
            logger.exception("similarity_check_failed", extra={"error": str(e)})
            return None

    async def run_synthesis_cycle(self) -> dict[str, Any]:
        """
        Run a complete cross-project synthesis cycle.
        
        Returns:
            Summary of discoveries
        """
        logger.info("synthesizer_cycle_started")

        summary = {
            "discoveries": {
                "reusable_utilities": [],
                "common_decisions": [],
                "similar_patterns": [],
            }
        }

        try:
            # Find reusable utilities
            utilities = await self.discover_reusable_utilities()
            summary["discoveries"]["reusable_utilities"] = utilities

            # Find common decisions
            decisions = await self.find_common_decisions()
            summary["discoveries"]["common_decisions"] = decisions

            # Get all active projects
            projects_cypher = """
            MATCH (p:Project)
            WHERE p.status = 'active' AND NOT p.archived = true
            RETURN p.uid as uid
            LIMIT 5
            """

            projects = await self.neo4j.query(projects_cypher)

            # Find similar patterns for each project
            for project in projects:
                patterns = await self.find_similar_patterns(project["uid"])
                summary["discoveries"]["similar_patterns"].extend(patterns)

            summary["total_discoveries"] = (
                len(utilities)
                + len(decisions)
                + len(summary["discoveries"]["similar_patterns"])
            )

            logger.info(
                "synthesizer_cycle_completed",
                extra={"total_discoveries": summary["total_discoveries"]},
            )

        except Exception as e:
            logger.exception("synthesizer_cycle_failed", extra={"error": str(e)})
            summary["error"] = str(e)

        return summary

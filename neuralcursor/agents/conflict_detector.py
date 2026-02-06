"""
Conflict Detector: Identifies architectural drifts and contradictions.

Flags when:
1. New code contradicts existing Requirements
2. Decisions conflict with each other
3. Implementation deviates from documented design
"""

import logging
from typing import Any, Optional

from neuralcursor.brain.neo4j.client import Neo4jClient
from neuralcursor.llm.orchestrator import get_orchestrator, LLMRequest

logger = logging.getLogger(__name__)


class ConflictDetector:
    """
    Detects contextual drifts and architectural conflicts.
    
    Proactively alerts when code or decisions contradict
    established patterns or requirements.
    """

    def __init__(self, neo4j_client: Neo4jClient):
        """
        Initialize conflict detector.
        
        Args:
            neo4j_client: Neo4j client
        """
        self.neo4j = neo4j_client
        self.orchestrator = get_orchestrator()

    async def check_requirement_conflicts(
        self, requirement_uid: str
    ) -> list[dict[str, Any]]:
        """
        Check if a requirement conflicts with existing decisions or code.
        
        Args:
            requirement_uid: UID of requirement to check
            
        Returns:
            List of potential conflicts
        """
        # Get the requirement
        requirement = await self.neo4j.get_node(requirement_uid)
        if not requirement:
            return []

        # Find related decisions and code entities
        cypher = """
        MATCH (req:Requirement {uid: $uid})
        OPTIONAL MATCH (req)<-[:IMPLEMENTS]-(decision:Decision)
        OPTIONAL MATCH (req)<-[:IMPLEMENTS]-(code:CodeEntity)
        RETURN 
            req,
            collect(DISTINCT decision) as decisions,
            collect(DISTINCT code) as code_entities
        """

        results = await self.neo4j.query(cypher, {"uid": requirement_uid})

        if not results:
            return []

        conflicts = []

        # Use LLM to detect semantic conflicts
        req_text = requirement.get("description", "")
        decisions = results[0].get("decisions", [])

        for decision in decisions:
            if decision:
                decision_text = decision.get("decision", "")

                # Check for conflicts using reasoning LLM
                conflict = await self._detect_semantic_conflict(
                    req_text, decision_text, "requirement", "decision"
                )

                if conflict:
                    conflicts.append(
                        {
                            "type": "requirement_decision_conflict",
                            "requirement_uid": requirement_uid,
                            "decision_uid": decision.get("uid"),
                            "severity": conflict.get("severity", "medium"),
                            "explanation": conflict.get("explanation"),
                        }
                    )

        return conflicts

    async def check_decision_conflicts(
        self, new_decision_uid: str
    ) -> list[dict[str, Any]]:
        """
        Check if a new decision conflicts with previous decisions.
        
        Args:
            new_decision_uid: UID of new decision
            
        Returns:
            List of conflicts with existing decisions
        """
        # Get the new decision
        new_decision = await self.neo4j.get_node(new_decision_uid)
        if not new_decision:
            return []

        # Find related decisions
        cypher = """
        MATCH (new:Decision {uid: $uid})
        MATCH (existing:Decision)
        WHERE existing.uid <> $uid
          AND NOT existing.archived = true
          AND (
            existing.context CONTAINS new.context 
            OR new.context CONTAINS existing.context
          )
        RETURN existing
        LIMIT 20
        """

        results = await self.neo4j.query(cypher, {"uid": new_decision_uid})

        conflicts = []
        new_decision_text = new_decision.get("decision", "")

        for record in results:
            existing = record.get("existing")
            if existing:
                existing_text = existing.get("decision", "")

                # Check for conflicts
                conflict = await self._detect_semantic_conflict(
                    new_decision_text,
                    existing_text,
                    "new_decision",
                    "existing_decision",
                )

                if conflict:
                    conflicts.append(
                        {
                            "type": "decision_decision_conflict",
                            "new_decision_uid": new_decision_uid,
                            "existing_decision_uid": existing.get("uid"),
                            "severity": conflict.get("severity", "high"),
                            "explanation": conflict.get("explanation"),
                            "recommendation": conflict.get("recommendation"),
                        }
                    )

        return conflicts

    async def _detect_semantic_conflict(
        self,
        text1: str,
        text2: str,
        label1: str,
        label2: str,
    ) -> Optional[dict[str, Any]]:
        """
        Use LLM to detect semantic conflicts between two texts.
        
        Args:
            text1: First text
            text2: Second text
            label1: Label for first text
            label2: Label for second text
            
        Returns:
            Conflict details if detected, None otherwise
        """
        try:
            prompt = f"""Analyze these two statements for conflicts or contradictions:

{label1}:
{text1}

{label2}:
{text2}

Do these statements conflict or contradict each other?

Respond in this format:
CONFLICT: [YES or NO]
SEVERITY: [low, medium, high]
EXPLANATION: [brief explanation]
RECOMMENDATION: [what to do about it]
"""

            request = LLMRequest(
                prompt=prompt,
                max_tokens=500,
                temperature=0.2,  # Lower temp for more consistent analysis
            )

            response = await self.orchestrator.generate_reasoning(request)

            # Parse response
            response_text = response.text.lower()

            if "conflict: yes" in response_text:
                # Extract severity
                severity = "medium"
                if "severity: high" in response_text:
                    severity = "high"
                elif "severity: low" in response_text:
                    severity = "low"

                # Extract explanation and recommendation
                lines = response.text.split("\n")
                explanation = ""
                recommendation = ""

                for line in lines:
                    if line.startswith("EXPLANATION:"):
                        explanation = line.replace("EXPLANATION:", "").strip()
                    elif line.startswith("RECOMMENDATION:"):
                        recommendation = line.replace("RECOMMENDATION:", "").strip()

                return {
                    "severity": severity,
                    "explanation": explanation,
                    "recommendation": recommendation,
                }

            return None

        except Exception as e:
            logger.exception("conflict_detection_failed", extra={"error": str(e)})
            return None

    async def scan_for_conflicts(self) -> dict[str, Any]:
        """
        Scan entire graph for conflicts.
        
        Returns:
            Summary of all detected conflicts
        """
        logger.info("conflict_scan_started")

        conflicts = {
            "requirement_conflicts": [],
            "decision_conflicts": [],
            "total_conflicts": 0,
        }

        try:
            # Get all active requirements
            req_cypher = """
            MATCH (req:Requirement)
            WHERE NOT req.archived = true
            RETURN req.uid as uid
            """

            req_results = await self.neo4j.query(req_cypher)

            for record in req_results[:10]:  # Limit to 10 for performance
                req_uid = record["uid"]
                req_conflicts = await self.check_requirement_conflicts(req_uid)
                conflicts["requirement_conflicts"].extend(req_conflicts)

            # Get recent decisions (last 30 days)
            decision_cypher = """
            MATCH (d:Decision)
            WHERE NOT d.archived = true
              AND d.created_at > datetime() - duration({days: 30})
            RETURN d.uid as uid
            ORDER BY d.created_at DESC
            LIMIT 20
            """

            decision_results = await self.neo4j.query(decision_cypher)

            for record in decision_results:
                decision_uid = record["uid"]
                decision_conflicts = await self.check_decision_conflicts(decision_uid)
                conflicts["decision_conflicts"].extend(decision_conflicts)

            conflicts["total_conflicts"] = (
                len(conflicts["requirement_conflicts"])
                + len(conflicts["decision_conflicts"])
            )

            logger.info(
                "conflict_scan_completed",
                extra={"total_conflicts": conflicts["total_conflicts"]},
            )

        except Exception as e:
            logger.exception("conflict_scan_failed", extra={"error": str(e)})
            conflicts["error"] = str(e)

        return conflicts

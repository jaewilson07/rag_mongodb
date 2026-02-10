"""Conflict detection engine for contextual drift alerts."""

import logging
from typing import List, Dict, Any
from datetime import datetime

from mdrag.capabilities.memory.gateway import MemoryGateway

logger = logging.getLogger(__name__)


class ConflictType:
    """Types of conflicts that can be detected."""

    REQUIREMENT_CODE_MISMATCH = "requirement_code_mismatch"
    DECISION_SUPERSEDED = "decision_superseded"
    CONTRADICTORY_DECISIONS = "contradictory_decisions"
    ORPHANED_CODE = "orphaned_code"
    IMPLEMENTATION_GAP = "implementation_gap"


class Conflict:
    """Represents a detected conflict."""

    def __init__(
        self,
        conflict_type: str,
        severity: str,
        description: str,
        entities: List[Dict[str, Any]],
        suggested_action: str,
    ):
        """
        Initialize conflict.
        
        Args:
            conflict_type: Type of conflict
            severity: low, medium, high, critical
            description: Human-readable description
            entities: List of involved entities
            suggested_action: Recommended action to resolve
        """
        self.conflict_type = conflict_type
        self.severity = severity
        self.description = description
        self.entities = entities
        self.suggested_action = suggested_action
        self.detected_at = datetime.utcnow()

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "conflict_type": self.conflict_type,
            "severity": self.severity,
            "description": self.description,
            "entities": self.entities,
            "suggested_action": self.suggested_action,
            "detected_at": self.detected_at.isoformat(),
        }


class ConflictDetector:
    """
    Detects contextual drift and architectural conflicts.
    
    Monitors for:
    - Code that contradicts documented requirements
    - Decisions that have been superseded but code not updated
    - Contradictory decisions within same project
    - Orphaned code with no architectural context
    - Requirements with no implementation
    """

    def __init__(self, memory_gateway: MemoryGateway):
        """
        Initialize conflict detector.
        
        Args:
            memory_gateway: Memory gateway instance
        """
        self.gateway = memory_gateway

    async def detect_all_conflicts(self) -> List[Conflict]:
        """
        Run all conflict detection checks.
        
        Returns:
            List of detected conflicts
        """
        logger.info("conflict_detector_scanning")
        
        conflicts = []
        
        try:
            # 1. Check for requirement-code mismatches
            conflicts.extend(await self.detect_requirement_mismatches())
            
            # 2. Check for superseded decisions with active code
            conflicts.extend(await self.detect_superseded_decision_conflicts())
            
            # 3. Check for contradictory decisions
            conflicts.extend(await self.detect_contradictory_decisions())
            
            # 4. Check for orphaned code
            conflicts.extend(await self.detect_orphaned_code())
            
            # 5. Check for implementation gaps
            conflicts.extend(await self.detect_implementation_gaps())
            
            logger.info(
                "conflict_detector_scan_complete",
                extra={"total_conflicts": len(conflicts)},
            )
            
            # Log high-severity conflicts
            high_severity = [c for c in conflicts if c.severity in ["high", "critical"]]
            for conflict in high_severity:
                logger.warning("conflict_detected_high_severity", extra=conflict.to_dict())
            
            return conflicts
            
        except Exception as e:
            logger.exception("conflict_detector_scan_failed", extra={"error": str(e)})
            return conflicts

    async def detect_requirement_mismatches(self) -> List[Conflict]:
        """
        Detect code that may violate stated requirements.
        
        Returns:
            List of conflicts
        """
        logger.info("conflict_detector_checking_requirements")
        
        conflicts = []
        
        # Find code entities with requirements but possibly conflicting implementation
        query = """
        MATCH (req:Requirement)-[:IMPLEMENTS]->(dec:Decision)-[:IMPLEMENTS]->(code:CodeEntity)
        WHERE req.status IN ['accepted', 'implemented']
        RETURN req, dec, code
        LIMIT 50
        """
        
        results = await self.gateway.neo4j_client.execute_cypher(query)
        
        # This is a placeholder - in reality, would need LLM to analyze code
        # against acceptance criteria
        for result in results:
            req = result.get("req", {})
            code = result.get("code", {})
            
            # Check if requirement has acceptance criteria
            if not req.get("acceptance_criteria"):
                conflicts.append(
                    Conflict(
                        conflict_type=ConflictType.REQUIREMENT_CODE_MISMATCH,
                        severity="medium",
                        description=f"Requirement '{req.get('name')}' has no acceptance criteria for code '{code.get('name')}'",
                        entities=[{"requirement": req, "code": code}],
                        suggested_action="Add acceptance criteria to requirement or verify implementation",
                    )
                )
        
        return conflicts

    async def detect_superseded_decision_conflicts(self) -> List[Conflict]:
        """
        Detect code implementing superseded decisions.
        
        Returns:
            List of conflicts
        """
        logger.info("conflict_detector_checking_superseded_decisions")
        
        conflicts = []
        
        # Find code implementing superseded decisions
        query = """
        MATCH (old_dec:Decision)-[:SUPERSEDES]->(new_dec:Decision)
        MATCH (old_dec)-[:IMPLEMENTS]->(code:CodeEntity)
        RETURN old_dec, new_dec, code
        """
        
        results = await self.gateway.neo4j_client.execute_cypher(query)
        
        for result in results:
            old_dec = result.get("old_dec", {})
            new_dec = result.get("new_dec", {})
            code = result.get("code", {})
            
            conflicts.append(
                Conflict(
                    conflict_type=ConflictType.DECISION_SUPERSEDED,
                    severity="high",
                    description=(
                        f"Code '{code.get('name')}' implements superseded decision '{old_dec.get('name')}'. "
                        f"New decision: '{new_dec.get('name')}'"
                    ),
                    entities=[
                        {"old_decision": old_dec, "new_decision": new_dec, "code": code}
                    ],
                    suggested_action=(
                        f"Update code to implement '{new_dec.get('name')}' or mark decision as still relevant"
                    ),
                )
            )
        
        return conflicts

    async def detect_contradictory_decisions(self) -> List[Conflict]:
        """
        Detect contradictory decisions within same project.
        
        Returns:
            List of conflicts
        """
        logger.info("conflict_detector_checking_contradictory_decisions")
        
        conflicts = []
        
        # Find decisions in same project with similar names (potential conflicts)
        query = """
        MATCH (p:Project)-[:HAS_DECISION]->(d1:Decision)
        MATCH (p)-[:HAS_DECISION]->(d2:Decision)
        WHERE d1.uuid < d2.uuid
          AND d1.name CONTAINS d2.name OR d2.name CONTAINS d1.name
          AND NOT (d1)-[:SUPERSEDES]->(d2)
          AND NOT (d2)-[:SUPERSEDES]->(d1)
        RETURN p, d1, d2
        LIMIT 20
        """
        
        results = await self.gateway.neo4j_client.execute_cypher(query)
        
        for result in results:
            project = result.get("p", {})
            d1 = result.get("d1", {})
            d2 = result.get("d2", {})
            
            conflicts.append(
                Conflict(
                    conflict_type=ConflictType.CONTRADICTORY_DECISIONS,
                    severity="medium",
                    description=(
                        f"Project '{project.get('name')}' has similar decisions: "
                        f"'{d1.get('name')}' and '{d2.get('name')}'"
                    ),
                    entities=[{"project": project, "decision1": d1, "decision2": d2}],
                    suggested_action="Review decisions for potential conflict or redundancy",
                )
            )
        
        return conflicts

    async def detect_orphaned_code(self) -> List[Conflict]:
        """
        Detect code entities with no architectural context.
        
        Returns:
            List of conflicts
        """
        logger.info("conflict_detector_checking_orphaned_code")
        
        conflicts = []
        
        # Find code entities with no incoming relationships
        query = """
        MATCH (code:CodeEntity)
        WHERE NOT (code)<-[:IMPLEMENTS]-()
          AND NOT code.file_path CONTAINS 'test'
          AND NOT code.file_path CONTAINS '__init__'
        RETURN code
        LIMIT 50
        """
        
        results = await self.gateway.neo4j_client.execute_cypher(query)
        
        for result in results:
            code = result.get("code", {})
            
            conflicts.append(
                Conflict(
                    conflict_type=ConflictType.ORPHANED_CODE,
                    severity="low",
                    description=f"Code entity '{code.get('name')}' has no architectural context",
                    entities=[{"code": code}],
                    suggested_action="Link to a decision or requirement, or document its purpose",
                )
            )
        
        return conflicts

    async def detect_implementation_gaps(self) -> List[Conflict]:
        """
        Detect requirements with no implementation.
        
        Returns:
            List of conflicts
        """
        logger.info("conflict_detector_checking_implementation_gaps")
        
        conflicts = []
        
        # Find high-priority requirements with no code
        query = """
        MATCH (req:Requirement {status: 'accepted'})
        WHERE req.priority IN ['high', 'critical']
          AND NOT (req)-[:IMPLEMENTS]->()-[:IMPLEMENTS]->(:CodeEntity)
        RETURN req
        """
        
        results = await self.gateway.neo4j_client.execute_cypher(query)
        
        for result in results:
            req = result.get("req", {})
            
            conflicts.append(
                Conflict(
                    conflict_type=ConflictType.IMPLEMENTATION_GAP,
                    severity="high" if req.get("priority") == "critical" else "medium",
                    description=f"High-priority requirement '{req.get('name')}' has no implementation",
                    entities=[{"requirement": req}],
                    suggested_action="Implement requirement or update status",
                )
            )
        
        return conflicts

    async def get_conflict_report(self) -> str:
        """
        Generate human-readable conflict report.
        
        Returns:
            Markdown formatted report
        """
        conflicts = await self.detect_all_conflicts()
        
        if not conflicts:
            return "# Conflict Report\n\n✅ No conflicts detected. System is healthy."
        
        # Group by severity
        critical = [c for c in conflicts if c.severity == "critical"]
        high = [c for c in conflicts if c.severity == "high"]
        medium = [c for c in conflicts if c.severity == "medium"]
        low = [c for c in conflicts if c.severity == "low"]
        
        report = [
            "# Conflict Detection Report",
            f"\n**Scan Date**: {datetime.utcnow().isoformat()}",
            f"\n**Total Conflicts**: {len(conflicts)}",
            "",
        ]
        
        if critical:
            report.append(f"\n## 🚨 Critical ({len(critical)})")
            for c in critical:
                report.append(f"\n### {c.description}")
                report.append(f"**Action**: {c.suggested_action}")
        
        if high:
            report.append(f"\n## ⚠️ High ({len(high)})")
            for c in high[:5]:  # Show first 5
                report.append(f"\n### {c.description}")
                report.append(f"**Action**: {c.suggested_action}")
        
        if medium:
            report.append(f"\n## ⚡ Medium ({len(medium)})")
            report.append(f"\n{len(medium)} medium-severity conflicts detected.")
        
        if low:
            report.append(f"\n## ℹ️ Low ({len(low)})")
            report.append(f"\n{len(low)} low-severity conflicts detected.")
        
        return "\n".join(report)

"""Discovery agent for cross-project pattern recognition."""

import logging
from typing import List, Dict, Any
from collections import defaultdict

from src.memory_gateway.gateway import MemoryGateway
from src.integrations.neo4j.queries import SecondBrainQueries

logger = logging.getLogger(__name__)


class Pattern:
    """Represents a discovered pattern."""

    def __init__(
        self,
        pattern_type: str,
        name: str,
        description: str,
        occurrences: int,
        projects: List[str],
        entities: List[Dict[str, Any]],
        suggestion: str,
    ):
        """
        Initialize pattern.
        
        Args:
            pattern_type: Type of pattern (utility, architecture, etc.)
            name: Pattern name
            description: Pattern description
            occurrences: Number of occurrences
            projects: List of project names
            entities: Related entities
            suggestion: Suggested action
        """
        self.pattern_type = pattern_type
        self.name = name
        self.description = description
        self.occurrences = occurrences
        self.projects = projects
        self.entities = entities
        self.suggestion = suggestion

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "pattern_type": self.pattern_type,
            "name": self.name,
            "description": self.description,
            "occurrences": self.occurrences,
            "projects": self.projects,
            "entities": self.entities,
            "suggestion": self.suggestion,
        }


class DiscoveryAgent:
    """
    Discovers patterns and insights across projects.
    
    Identifies:
    - Reusable utility functions across projects
    - Common architectural patterns
    - Frequently referenced resources
    - Similar requirements across projects
    - Code duplication opportunities
    """

    def __init__(self, memory_gateway: MemoryGateway):
        """
        Initialize discovery agent.
        
        Args:
            memory_gateway: Memory gateway instance
        """
        self.gateway = memory_gateway

    async def discover_all_patterns(self) -> List[Pattern]:
        """
        Run all pattern discovery checks.
        
        Returns:
            List of discovered patterns
        """
        logger.info("discovery_agent_scanning")
        
        patterns = []
        
        try:
            # 1. Find reusable utilities
            patterns.extend(await self.find_reusable_utilities())
            
            # 2. Find common architectural patterns
            patterns.extend(await self.find_architectural_patterns())
            
            # 3. Find frequently referenced resources
            patterns.extend(await self.find_popular_resources())
            
            # 4. Find similar requirements
            patterns.extend(await self.find_similar_requirements())
            
            logger.info(
                "discovery_agent_scan_complete",
                extra={"total_patterns": len(patterns)},
            )
            
            return patterns
            
        except Exception as e:
            logger.exception("discovery_agent_scan_failed", extra={"error": str(e)})
            return patterns

    async def find_reusable_utilities(self, min_projects: int = 2) -> List[Pattern]:
        """
        Find utility functions used across multiple projects.
        
        Args:
            min_projects: Minimum number of projects for consideration
            
        Returns:
            List of patterns
        """
        logger.info("discovery_agent_finding_utilities")
        
        patterns = []
        
        # Query for cross-project functions
        query, params = SecondBrainQueries.find_cross_project_patterns(
            entity_type="function", min_usage=min_projects
        )
        
        results = await self.gateway.neo4j_client.execute_cypher(query, params)
        
        for result in results:
            entity_name = result.get("entity_name", "Unknown")
            file_path = result.get("file_path", "Unknown")
            usage_count = result.get("usage_count", 0)
            projects = result.get("projects", [])
            
            project_names = [p.get("name", "Unknown") for p in projects]
            
            patterns.append(
                Pattern(
                    pattern_type="utility",
                    name=entity_name,
                    description=f"Utility function found in {usage_count} projects",
                    occurrences=usage_count,
                    projects=project_names,
                    entities=[{"file_path": file_path, "name": entity_name}],
                    suggestion=f"Consider extracting '{entity_name}' into a shared utility library",
                )
            )
        
        logger.info(
            "discovery_agent_utilities_found",
            extra={"count": len(patterns)},
        )
        
        return patterns

    async def find_architectural_patterns(self) -> List[Pattern]:
        """
        Find common architectural patterns across projects.
        
        Returns:
            List of patterns
        """
        logger.info("discovery_agent_finding_architectural_patterns")
        
        patterns = []
        
        # Find common decision themes
        query = """
        MATCH (d:Decision)
        WITH d.name as decision_name, collect(d) as decisions
        WHERE size(decisions) >= 2
        RETURN decision_name, size(decisions) as count, decisions
        LIMIT 20
        """
        
        results = await self.gateway.neo4j_client.execute_cypher(query)
        
        for result in results:
            decision_name = result.get("decision_name", "Unknown")
            count = result.get("count", 0)
            decisions = result.get("decisions", [])
            
            patterns.append(
                Pattern(
                    pattern_type="architecture",
                    name=decision_name,
                    description=f"Architectural decision repeated {count} times",
                    occurrences=count,
                    projects=[],  # Would need to query project relationships
                    entities=decisions,
                    suggestion=f"Consider creating a standard pattern or template for '{decision_name}'",
                )
            )
        
        return patterns

    async def find_popular_resources(self, min_references: int = 3) -> List[Pattern]:
        """
        Find resources frequently referenced across decisions.
        
        Args:
            min_references: Minimum number of references
            
        Returns:
            List of patterns
        """
        logger.info("discovery_agent_finding_popular_resources")
        
        patterns = []
        
        # Find resources with multiple decision links
        query = """
        MATCH (res:Resource)-[:INSPIRED_BY]->(dec:Decision)
        WITH res, collect(dec) as decisions
        WHERE size(decisions) >= $min_references
        RETURN res, size(decisions) as reference_count, decisions
        ORDER BY reference_count DESC
        LIMIT 10
        """
        
        results = await self.gateway.neo4j_client.execute_cypher(
            query, {"min_references": min_references}
        )
        
        for result in results:
            resource = result.get("res", {})
            reference_count = result.get("reference_count", 0)
            decisions = result.get("decisions", [])
            
            decision_names = [d.get("name", "Unknown") for d in decisions]
            
            patterns.append(
                Pattern(
                    pattern_type="resource",
                    name=resource.get("name", "Unknown"),
                    description=f"Resource inspired {reference_count} decisions",
                    occurrences=reference_count,
                    projects=[],
                    entities=[{"resource": resource, "decisions": decision_names}],
                    suggestion="This resource is highly influential. Consider adding to recommended reading.",
                )
            )
        
        return patterns

    async def find_similar_requirements(self) -> List[Pattern]:
        """
        Find similar requirements across projects.
        
        Returns:
            List of patterns
        """
        logger.info("discovery_agent_finding_similar_requirements")
        
        patterns = []
        
        # Group requirements by similar names
        query = """
        MATCH (req:Requirement)
        WITH split(req.name, ' ')[0] as theme, collect(req) as requirements
        WHERE size(requirements) >= 2
        RETURN theme, size(requirements) as count, requirements
        ORDER BY count DESC
        LIMIT 20
        """
        
        results = await self.gateway.neo4j_client.execute_cypher(query)
        
        for result in results:
            theme = result.get("theme", "Unknown")
            count = result.get("count", 0)
            requirements = result.get("requirements", [])
            
            req_names = [r.get("name", "Unknown") for r in requirements]
            
            patterns.append(
                Pattern(
                    pattern_type="requirement",
                    name=f"{theme} Requirements",
                    description=f"{count} requirements related to {theme}",
                    occurrences=count,
                    projects=[],
                    entities=[{"theme": theme, "requirements": req_names}],
                    suggestion=f"Consider creating a standard requirement template for {theme}-related features",
                )
            )
        
        return patterns

    async def find_code_duplication_candidates(self) -> List[Pattern]:
        """
        Find potential code duplication across projects.
        
        Returns:
            List of patterns
        """
        logger.info("discovery_agent_finding_duplication_candidates")
        
        patterns = []
        
        # Find code entities with identical names in different projects
        query = """
        MATCH (p1:Project)-[:CONTAINS]->(c1:CodeEntity)
        MATCH (p2:Project)-[:CONTAINS]->(c2:CodeEntity)
        WHERE p1.uuid < p2.uuid
          AND c1.name = c2.name
          AND c1.entity_type = c2.entity_type
        RETURN c1.name as name, c1.entity_type as type, 
               collect(DISTINCT p1.name) + collect(DISTINCT p2.name) as projects,
               count(*) as occurrences
        ORDER BY occurrences DESC
        LIMIT 20
        """
        
        results = await self.gateway.neo4j_client.execute_cypher(query)
        
        for result in results:
            name = result.get("name", "Unknown")
            entity_type = result.get("type", "unknown")
            projects = result.get("projects", [])
            occurrences = result.get("occurrences", 0)
            
            patterns.append(
                Pattern(
                    pattern_type="duplication",
                    name=name,
                    description=f"{entity_type} '{name}' appears in {len(projects)} projects",
                    occurrences=occurrences,
                    projects=projects,
                    entities=[{"name": name, "type": entity_type}],
                    suggestion=f"Review '{name}' for potential consolidation or shared library extraction",
                )
            )
        
        return patterns

    async def get_discovery_report(self) -> str:
        """
        Generate human-readable discovery report.
        
        Returns:
            Markdown formatted report
        """
        patterns = await self.discover_all_patterns()
        
        if not patterns:
            return "# Discovery Report\n\nNo significant patterns found."
        
        # Group by pattern type
        by_type = defaultdict(list)
        for pattern in patterns:
            by_type[pattern.pattern_type].append(pattern)
        
        report = [
            "# Cross-Project Pattern Discovery Report",
            f"\n**Total Patterns Found**: {len(patterns)}",
            "",
        ]
        
        # Utilities
        if "utility" in by_type:
            report.append(f"\n## 🔧 Reusable Utilities ({len(by_type['utility'])})")
            for pattern in by_type["utility"][:5]:
                report.append(f"\n### {pattern.name}")
                report.append(f"**Occurrences**: {pattern.occurrences}")
                report.append(f"**Projects**: {', '.join(pattern.projects)}")
                report.append(f"**Suggestion**: {pattern.suggestion}")
        
        # Architecture
        if "architecture" in by_type:
            report.append(f"\n## 🏗️ Architectural Patterns ({len(by_type['architecture'])})")
            for pattern in by_type["architecture"][:5]:
                report.append(f"\n### {pattern.name}")
                report.append(f"**Occurrences**: {pattern.occurrences}")
                report.append(f"**Suggestion**: {pattern.suggestion}")
        
        # Resources
        if "resource" in by_type:
            report.append(f"\n## 📚 Influential Resources ({len(by_type['resource'])})")
            for pattern in by_type["resource"][:5]:
                report.append(f"\n### {pattern.name}")
                report.append(f"**Inspired {pattern.occurrences} decisions**")
                report.append(f"**Suggestion**: {pattern.suggestion}")
        
        # Requirements
        if "requirement" in by_type:
            report.append(f"\n## 📋 Requirement Themes ({len(by_type['requirement'])})")
            for pattern in by_type["requirement"][:5]:
                report.append(f"\n### {pattern.name}")
                report.append(f"**Occurrences**: {pattern.occurrences}")
        
        return "\n".join(report)

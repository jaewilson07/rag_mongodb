"""Pydantic models for Neo4j graph nodes following PARA methodology."""

from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class NodeType(str, Enum):
    """Graph node types following PARA methodology."""

    PROJECT = "Project"
    AREA = "Area"
    DECISION = "Decision"
    REQUIREMENT = "Requirement"
    CODE_ENTITY = "CodeEntity"
    RESOURCE = "Resource"
    ARCHIVE = "Archive"


class RelationType(str, Enum):
    """Graph relationship types."""

    DEPENDS_ON = "DEPENDS_ON"
    IMPLEMENTS = "IMPLEMENTS"
    SUPERSEDES = "SUPERSEDES"
    BELONGS_TO = "BELONGS_TO"
    INSPIRED_BY = "INSPIRED_BY"
    REFERENCES = "REFERENCES"
    RELATED_TO = "RELATED_TO"
    HAS_DECISION = "HAS_DECISION"
    HAS_REQUIREMENT = "HAS_REQUIREMENT"
    CONTAINS = "CONTAINS"


class GraphNode(BaseModel):
    """Base class for all graph nodes."""

    uuid: Optional[str] = Field(None, description="Unique identifier")
    name: str = Field(..., description="Node name")
    description: Optional[str] = Field(None, description="Node description")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    tags: List[str] = Field(default_factory=list)


class Project(GraphNode):
    """Project node - goal-oriented work with deadline."""

    node_type: str = NodeType.PROJECT
    status: str = Field(default="active", description="active, completed, archived")
    deadline: Optional[datetime] = Field(None, description="Project deadline")
    context: Optional[str] = Field(None, description="Why this project exists")
    goals: List[str] = Field(default_factory=list)


class Area(GraphNode):
    """Area of Responsibility - ongoing standard to maintain."""

    node_type: str = NodeType.AREA
    responsibility: str = Field(..., description="What standard to maintain")
    active: bool = Field(default=True)


class Decision(GraphNode):
    """Architectural or design decision."""

    node_type: str = NodeType.DECISION
    rationale: str = Field(..., description="Why this decision was made")
    alternatives_considered: List[str] = Field(default_factory=list)
    consequences: List[str] = Field(default_factory=list)
    decided_at: datetime = Field(default_factory=datetime.utcnow)
    decided_by: Optional[str] = Field(None, description="Who made the decision")


class Requirement(GraphNode):
    """Functional or non-functional requirement."""

    node_type: str = NodeType.REQUIREMENT
    requirement_type: str = Field(
        default="functional", description="functional, non-functional, constraint"
    )
    priority: str = Field(default="medium", description="low, medium, high, critical")
    status: str = Field(
        default="proposed", description="proposed, accepted, implemented, rejected"
    )
    acceptance_criteria: List[str] = Field(default_factory=list)
    source: Optional[str] = Field(None, description="Where requirement came from")


class CodeEntity(GraphNode):
    """Code-level entity (function, class, module, file)."""

    node_type: str = NodeType.CODE_ENTITY
    entity_type: str = Field(
        ..., description="function, class, module, file, package"
    )
    file_path: str = Field(..., description="Absolute or relative file path")
    line_number: Optional[int] = Field(None, description="Starting line number")
    code_snippet: Optional[str] = Field(None, description="Actual code")
    ast_info: Dict[str, Any] = Field(
        default_factory=dict, description="AST metadata"
    )
    dependencies: List[str] = Field(default_factory=list)


class Resource(GraphNode):
    """External resource (URL, document, video, reference)."""

    node_type: str = NodeType.RESOURCE
    resource_type: str = Field(
        ..., description="url, document, video, paper, book, tutorial"
    )
    url: Optional[str] = Field(None, description="Resource URL")
    content_hash: Optional[str] = Field(None, description="Content hash for caching")
    mongodb_ref: Optional[str] = Field(
        None, description="Reference to MongoDB document_id"
    )
    key_points: List[str] = Field(default_factory=list)


class Relationship(BaseModel):
    """Graph relationship between nodes."""

    source_uuid: str = Field(..., description="Source node UUID")
    target_uuid: str = Field(..., description="Target node UUID")
    relation_type: RelationType = Field(..., description="Relationship type")
    properties: Dict[str, Any] = Field(
        default_factory=dict, description="Relationship properties"
    )
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GraphQuery(BaseModel):
    """Query parameters for graph traversal."""

    node_type: Optional[NodeType] = None
    filters: Dict[str, Any] = Field(default_factory=dict)
    max_depth: int = Field(default=3, description="Maximum traversal depth")
    limit: int = Field(default=50, description="Maximum results")
    include_relationships: bool = Field(default=True)


class GraphQueryResult(BaseModel):
    """Result from graph query."""

    nodes: List[Dict[str, Any]] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

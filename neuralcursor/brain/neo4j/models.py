"""
Pydantic models for Neo4j graph nodes and relationships.

Implements PARA methodology: Projects, Areas, Resources, Archives.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator


class NodeType(str, Enum):
    """Types of nodes in the knowledge graph."""

    PROJECT = "Project"
    AREA = "Area"
    RESOURCE = "Resource"
    ARCHIVE = "Archive"
    DECISION = "Decision"
    REQUIREMENT = "Requirement"
    CODE_ENTITY = "CodeEntity"
    FILE = "File"
    CONVERSATION = "Conversation"


class RelationType(str, Enum):
    """Types of relationships in the knowledge graph."""

    DEPENDS_ON = "DEPENDS_ON"
    IMPLEMENTS = "IMPLEMENTS"
    SUPERSEDES = "SUPERSEDES"
    BELONGS_TO = "BELONGS_TO"
    REFERENCES = "REFERENCES"
    RELATES_TO = "RELATES_TO"
    CONTAINS = "CONTAINS"
    DERIVED_FROM = "DERIVED_FROM"
    INSPIRED_BY = "INSPIRED_BY"


class BaseNode(BaseModel):
    """Base model for all Neo4j nodes."""

    uid: Optional[str] = Field(None, description="Unique identifier (Neo4j node ID)")
    node_type: NodeType = Field(..., description="Type of the node")
    name: str = Field(..., description="Human-readable name")
    description: Optional[str] = Field(None, description="Detailed description")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    @field_validator("metadata", mode="before")
    @classmethod
    def validate_metadata(cls, v: Any) -> dict[str, Any]:
        """Ensure metadata is a dictionary."""
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError("metadata must be a dictionary")
        return v


class ProjectNode(BaseNode):
    """
    Project: A series of tasks linked to a goal with a deadline.
    
    Examples: "Build NeuralCursor", "Van Conversion", "Launch NerdBbB"
    """

    node_type: NodeType = Field(default=NodeType.PROJECT, frozen=True)
    deadline: Optional[datetime] = Field(None, description="Project deadline")
    status: str = Field(default="active", description="active, completed, archived, on-hold")
    goals: list[str] = Field(default_factory=list, description="Project goals")
    technologies: list[str] = Field(default_factory=list, description="Technologies used")


class AreaNode(BaseNode):
    """
    Area: A sphere of activity with a standard to maintain over time.
    
    Examples: "Health & Fitness", "Software Engineering", "Content Creation"
    """

    node_type: NodeType = Field(default=NodeType.AREA, frozen=True)
    standards: list[str] = Field(default_factory=list, description="Standards to maintain")
    focus_level: int = Field(default=5, ge=1, le=10, description="Current focus priority (1-10)")


class ResourceNode(BaseNode):
    """
    Resource: A topic or theme of ongoing interest.
    
    Examples: YouTube videos, articles, documentation, code snippets
    """

    node_type: NodeType = Field(default=NodeType.RESOURCE, frozen=True)
    source_type: str = Field(..., description="youtube, article, documentation, code, etc.")
    source_url: Optional[str] = Field(None, description="Original URL")
    content_hash: Optional[str] = Field(None, description="Hash of content for deduplication")
    tags: list[str] = Field(default_factory=list, description="Categorization tags")


class ArchiveNode(BaseNode):
    """
    Archive: Inactive items from the other three categories.
    
    Completed projects, deprecated code, outdated resources.
    """

    node_type: NodeType = Field(default=NodeType.ARCHIVE, frozen=True)
    archived_from: NodeType = Field(..., description="Original node type")
    archived_at: datetime = Field(default_factory=datetime.utcnow)
    archive_reason: Optional[str] = Field(None, description="Why it was archived")


class DecisionNode(BaseNode):
    """
    Decision: A significant architectural or design decision.
    
    Captures the "why" behind code choices.
    """

    node_type: NodeType = Field(default=NodeType.DECISION, frozen=True)
    context: str = Field(..., description="Context that led to this decision")
    decision: str = Field(..., description="The decision that was made")
    consequences: list[str] = Field(default_factory=list, description="Expected consequences")
    alternatives: list[str] = Field(default_factory=list, description="Alternatives considered")
    rationale: Optional[str] = Field(None, description="Reasoning behind the decision")


class RequirementNode(BaseNode):
    """
    Requirement: A functional or non-functional requirement.
    
    Links decisions to code entities.
    """

    node_type: NodeType = Field(default=NodeType.REQUIREMENT, frozen=True)
    requirement_type: str = Field(..., description="functional, non-functional, constraint")
    priority: str = Field(default="medium", description="high, medium, low")
    status: str = Field(default="pending", description="pending, in-progress, implemented, deprecated")
    acceptance_criteria: list[str] = Field(default_factory=list)


class CodeEntityNode(BaseNode):
    """
    CodeEntity: A significant code structure (class, function, module).
    
    Represents actual code in the filesystem.
    """

    node_type: NodeType = Field(default=NodeType.CODE_ENTITY, frozen=True)
    entity_type: str = Field(..., description="class, function, module, file")
    file_path: str = Field(..., description="Relative path from project root")
    line_start: Optional[int] = Field(None, description="Starting line number")
    line_end: Optional[int] = Field(None, description="Ending line number")
    language: str = Field(..., description="Programming language")
    signature: Optional[str] = Field(None, description="Function/method signature")


class FileNode(BaseNode):
    """
    File: A tracked file in the codebase.
    
    Automatically updated by file system watcher.
    """

    node_type: NodeType = Field(default=NodeType.FILE, frozen=True)
    file_path: str = Field(..., description="Relative path from project root")
    file_type: str = Field(..., description="Extension or category")
    size_bytes: int = Field(..., description="File size")
    last_modified: datetime = Field(..., description="Last modification time")
    content_hash: Optional[str] = Field(None, description="Hash for change detection")


class ConversationNode(BaseNode):
    """
    Conversation: A distilled conversation or chat log.
    
    Created by the Librarian agent from MongoDB chat logs.
    """

    node_type: NodeType = Field(default=NodeType.CONVERSATION, frozen=True)
    summary: str = Field(..., description="Distilled summary of conversation")
    key_points: list[str] = Field(default_factory=list)
    participants: list[str] = Field(default_factory=list)
    mongo_conversation_ids: list[str] = Field(
        default_factory=list, description="References to MongoDB chat logs"
    )


class Relationship(BaseModel):
    """
    Relationship between two nodes in the graph.
    
    Supports multi-hop traversal for architectural reasoning.
    """

    from_uid: str = Field(..., description="Source node UID")
    to_uid: str = Field(..., description="Target node UID")
    relation_type: RelationType = Field(..., description="Type of relationship")
    weight: float = Field(default=1.0, ge=0.0, le=1.0, description="Relationship strength")
    properties: dict[str, Any] = Field(default_factory=dict, description="Additional properties")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("properties", mode="before")
    @classmethod
    def validate_properties(cls, v: Any) -> dict[str, Any]:
        """Ensure properties is a dictionary."""
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError("properties must be a dictionary")
        return v

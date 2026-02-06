"""
API models for the gateway.
"""

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


# === Request Models ===


class CreateNodeRequest(BaseModel):
    """Request to create a node in Neo4j."""

    node_type: str = Field(..., description="Type of node (Project, Decision, etc.)")
    name: str = Field(..., description="Node name")
    description: Optional[str] = Field(None, description="Node description")
    properties: dict[str, Any] = Field(default_factory=dict, description="Additional properties")


class CreateRelationshipRequest(BaseModel):
    """Request to create a relationship between nodes."""

    from_uid: str = Field(..., description="Source node UID")
    to_uid: str = Field(..., description="Target node UID")
    relation_type: str = Field(..., description="Relationship type")
    weight: float = Field(default=1.0, ge=0.0, le=1.0)
    properties: dict[str, Any] = Field(default_factory=dict)


class QueryGraphRequest(BaseModel):
    """Request to query the knowledge graph."""

    cypher: str = Field(..., description="Cypher query")
    parameters: dict[str, Any] = Field(default_factory=dict)


class SaveChatMessageRequest(BaseModel):
    """Request to save a chat message."""

    session_id: str = Field(..., description="Conversation session ID")
    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")
    metadata: dict[str, Any] = Field(default_factory=dict)


class SearchGraphRequest(BaseModel):
    """Request to search the knowledge graph."""

    query: str = Field(..., description="Search query")
    node_types: Optional[list[str]] = Field(None, description="Filter by node types")
    limit: int = Field(default=10, ge=1, le=100)


class FindPathRequest(BaseModel):
    """Request to find path between two nodes."""

    from_uid: str = Field(..., description="Starting node UID")
    to_uid: str = Field(..., description="Target node UID")
    max_depth: int = Field(default=5, ge=1, le=10)
    relation_types: Optional[list[str]] = Field(None, description="Filter by relationship types")


# === Response Models ===


class NodeResponse(BaseModel):
    """Response containing a node."""

    uid: str
    node_type: str
    name: str
    description: Optional[str] = None
    properties: dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class RelationshipResponse(BaseModel):
    """Response containing a relationship."""

    from_uid: str
    to_uid: str
    relation_type: str
    weight: float
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphQueryResponse(BaseModel):
    """Response from a graph query."""

    results: list[dict[str, Any]]
    count: int
    query_time_ms: float


class SchemaInfoResponse(BaseModel):
    """Response containing schema information."""

    constraints: int
    indexes: int
    node_counts: dict[str, int]
    total_nodes: int
    total_relationships: int
    schema_valid: bool


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    neo4j_connected: bool
    mongodb_connected: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    details: dict[str, Any] = Field(default_factory=dict)

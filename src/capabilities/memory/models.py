"""Models for Memory Gateway requests and responses."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class MemoryType(str, Enum):
    """Type of memory operation."""

    STRUCTURAL = "structural"  # Neo4j graph operations
    EPISODIC = "episodic"  # MongoDB document operations
    HYBRID = "hybrid"  # Combined query


class MemoryOperation(str, Enum):
    """Memory operation type."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    QUERY = "query"
    TRAVERSE = "traverse"


class MemoryRequest(BaseModel):
    """Request to the memory gateway."""

    operation: MemoryOperation = Field(..., description="Operation to perform")
    memory_type: MemoryType = Field(..., description="Type of memory to operate on")
    entity_type: Optional[str] = Field(None, description="Entity type (Project, Decision, etc.)")
    entity_id: Optional[str] = Field(None, description="Entity UUID or MongoDB ObjectId")
    data: Optional[Dict[str, Any]] = Field(None, description="Data payload")
    query: Optional[str] = Field(None, description="Query string or Cypher query")
    filters: Optional[Dict[str, Any]] = Field(None, description="Filter parameters")
    limit: Optional[int] = Field(10, description="Result limit")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class MemoryResponse(BaseModel):
    """Response from the memory gateway."""

    success: bool = Field(..., description="Whether operation succeeded")
    memory_type: MemoryType = Field(..., description="Memory type used")
    operation: MemoryOperation = Field(..., description="Operation performed")
    data: Optional[Any] = Field(None, description="Response data")
    error: Optional[str] = Field(None, description="Error message if failed")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ArchitecturalQuery(BaseModel):
    """Query for architectural context and reasoning."""

    file_path: Optional[str] = Field(None, description="Code file path")
    line_number: Optional[int] = Field(None, description="Line number in file")
    entity_uuid: Optional[str] = Field(None, description="Entity UUID")
    query_text: Optional[str] = Field(None, description="Natural language query")
    max_depth: int = Field(default=3, description="Traversal depth")
    include_history: bool = Field(default=True, description="Include decision history")
    include_resources: bool = Field(default=True, description="Include related resources")


class ArchitecturalContext(BaseModel):
    """Architectural context response."""

    file_path: Optional[str] = None
    entity_name: Optional[str] = None
    requirements: List[Dict[str, Any]] = Field(default_factory=list)
    decisions: List[Dict[str, Any]] = Field(default_factory=list)
    code_entities: List[Dict[str, Any]] = Field(default_factory=list)
    resources: List[Dict[str, Any]] = Field(default_factory=list)
    decision_history: List[Dict[str, Any]] = Field(default_factory=list)
    relationships: List[Dict[str, Any]] = Field(default_factory=list)
    summary: Optional[str] = None


class WorkingSet(BaseModel):
    """Current working set for active development."""

    active_projects: List[str] = Field(default_factory=list, description="Active project UUIDs")
    active_files: List[str] = Field(default_factory=list, description="Recently touched file paths")
    core_memory: List[Dict[str, Any]] = Field(default_factory=list, description="High-priority entities")
    cold_storage: List[str] = Field(default_factory=list, description="Archived entity UUIDs")
    last_updated: datetime = Field(default_factory=datetime.utcnow)


class GraphStats(BaseModel):
    """Statistics about the knowledge graph."""

    total_nodes: int = 0
    total_relationships: int = 0
    node_counts: Dict[str, int] = Field(default_factory=dict)
    relationship_counts: Dict[str, int] = Field(default_factory=dict)
    active_projects: int = 0
    archived_projects: int = 0
    last_updated: datetime = Field(default_factory=datetime.utcnow)

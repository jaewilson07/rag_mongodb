"""
FastAPI gateway server for NeuralCursor memory operations.

This serves as the single entry point for all memory operations,
ensuring MemGPT and MCP server communicate with unified data state.
"""

import logging
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from mdrag.validation import ValidationError, validate_mongodb, validate_neo4j

from neuralcursor.brain.mongodb.client import ChatMessage, MongoDBClient
from neuralcursor.brain.neo4j.client import Neo4jClient
from neuralcursor.brain.neo4j.models import (
    CodeEntityNode,
    DecisionNode,
    ProjectNode,
    Relationship,
    RelationType,
    RequirementNode,
    ResourceNode,
)
from neuralcursor.settings import get_settings

from .dependencies import (
    GatewayDependencies,
    close_clients,
    get_gateway_deps,
    get_mongodb_client,
    get_neo4j_client,
    init_clients,
)
from .models import (
    CreateNodeRequest,
    CreateRelationshipRequest,
    FindPathRequest,
    GraphQueryResponse,
    HealthResponse,
    NodeResponse,
    QueryGraphRequest,
    SaveChatMessageRequest,
    SchemaInfoResponse,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup: Validate services first
    settings = get_settings()
    
    try:
        # Validate MongoDB
        await validate_mongodb(settings, strict=False)
        logger.info("✓ MongoDB validation passed")
        
        # Validate Neo4j
        validate_neo4j(
            settings.neo4j_uri,
            settings.neo4j_username,
            settings.neo4j_password,
            settings.neo4j_database,
        )
        logger.info("✓ Neo4j validation passed")
        
        # Validate vLLM if using local LLM endpoints (conditional on URLs being set)
        # NeuralCursor always configures LLM endpoints, so validate them
        from mdrag.validation import validate_vllm
        try:
            validate_vllm(
                settings.reasoning_llm_host,
                settings.embedding_llm_host,
            )
            logger.info("✓ vLLM services validation passed")
        except ValidationError as e:
            logger.warning(f"vLLM validation failed (will degrade to remote APIs if configured):\n{e}")
            # Don't fail startup - LLM orchestrator can gracefully degrade
        
    except ValidationError as e:
        logger.error(f"Validation failed:\n{e}")
        raise RuntimeError("Gateway service validation failed") from e
    
    # Initialize clients
    await init_clients()
    logger.info("gateway_server_started")

    yield

    # Shutdown
    await close_clients()
    logger.info("gateway_server_stopped")


# Initialize FastAPI app
app = FastAPI(
    title="NeuralCursor Memory Gateway",
    description="Unified API for Neo4j and MongoDB memory operations",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Health Check ===


@app.get("/health", response_model=HealthResponse)
async def health_check(deps: GatewayDependencies = Depends(get_gateway_deps)) -> HealthResponse:
    """
    Health check endpoint.
    
    Returns:
        Health status with connection states
    """
    neo4j_connected = False
    mongodb_connected = False

    try:
        # Test Neo4j
        await deps.neo4j.driver.verify_connectivity()
        neo4j_connected = True
    except Exception as e:
        logger.warning("neo4j_health_check_failed", extra={"error": str(e)})

    try:
        # Test MongoDB
        await deps.mongodb.db.command("ping")
        mongodb_connected = True
    except Exception as e:
        logger.warning("mongodb_health_check_failed", extra={"error": str(e)})

    status = "healthy" if (neo4j_connected and mongodb_connected) else "degraded"

    return HealthResponse(
        status=status,
        neo4j_connected=neo4j_connected,
        mongodb_connected=mongodb_connected,
        details={
            "neo4j_uri": get_settings().neo4j_uri,
            "mongodb_database": get_settings().mongodb_database,
        },
    )


# === Neo4j Endpoints ===


@app.post("/graph/nodes", response_model=NodeResponse)
async def create_node(
    request: CreateNodeRequest,
    neo4j: Neo4jClient = Depends(get_neo4j_client),
) -> NodeResponse:
    """
    Create a new node in the knowledge graph.
    
    Args:
        request: Node creation request
        neo4j: Neo4j client
        
    Returns:
        Created node with UID
    """
    # Map node type string to Pydantic model
    node_type_map = {
        "Project": ProjectNode,
        "Decision": DecisionNode,
        "Requirement": RequirementNode,
        "CodeEntity": CodeEntityNode,
        "Resource": ResourceNode,
    }

    node_class = node_type_map.get(request.node_type)
    if not node_class:
        raise HTTPException(status_code=400, detail=f"Unknown node type: {request.node_type}")

    # Create node instance
    node_data = {
        "name": request.name,
        "description": request.description,
        **request.properties,
    }

    try:
        node = node_class(**node_data)
        uid = await neo4j.create_node(node)

        return NodeResponse(
            uid=uid,
            node_type=request.node_type,
            name=request.name,
            description=request.description,
            properties=request.properties,
        )
    except Exception as e:
        logger.exception("node_creation_failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/nodes/{uid}", response_model=NodeResponse)
async def get_node(
    uid: str,
    neo4j: Neo4jClient = Depends(get_neo4j_client),
) -> NodeResponse:
    """
    Get a node by UID.
    
    Args:
        uid: Node unique identifier
        neo4j: Neo4j client
        
    Returns:
        Node data
    """
    node_data = await neo4j.get_node(uid)

    if not node_data:
        raise HTTPException(status_code=404, detail=f"Node not found: {uid}")

    return NodeResponse(
        uid=uid,
        node_type=node_data.get("node_type", "Unknown"),
        name=node_data.get("name", ""),
        description=node_data.get("description"),
        properties=node_data,
    )


@app.post("/graph/relationships")
async def create_relationship(
    request: CreateRelationshipRequest,
    neo4j: Neo4jClient = Depends(get_neo4j_client),
) -> dict[str, Any]:
    """
    Create a relationship between two nodes.
    
    Args:
        request: Relationship creation request
        neo4j: Neo4j client
        
    Returns:
        Success response
    """
    try:
        relation_type = RelationType(request.relation_type)
    except ValueError:
        raise HTTPException(
            status_code=400, detail=f"Invalid relation type: {request.relation_type}"
        )

    relationship = Relationship(
        from_uid=request.from_uid,
        to_uid=request.to_uid,
        relation_type=relation_type,
        weight=request.weight,
        properties=request.properties,
    )

    try:
        created = await neo4j.create_relationship(relationship)
        if not created:
            raise HTTPException(status_code=400, detail="Failed to create relationship")

        return {
            "success": True,
            "from_uid": request.from_uid,
            "to_uid": request.to_uid,
            "relation_type": request.relation_type,
        }
    except Exception as e:
        logger.exception("relationship_creation_failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/graph/query", response_model=GraphQueryResponse)
async def query_graph(
    request: QueryGraphRequest,
    neo4j: Neo4jClient = Depends(get_neo4j_client),
) -> GraphQueryResponse:
    """
    Execute a Cypher query against the knowledge graph.
    
    Args:
        request: Query request
        neo4j: Neo4j client
        
    Returns:
        Query results
    """
    start_time = time.time()

    try:
        results = await neo4j.query(request.cypher, request.parameters)
        query_time_ms = (time.time() - start_time) * 1000

        return GraphQueryResponse(
            results=results,
            count=len(results),
            query_time_ms=query_time_ms,
        )
    except Exception as e:
        logger.exception("graph_query_failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/graph/path")
async def find_path(
    request: FindPathRequest,
    neo4j: Neo4jClient = Depends(get_neo4j_client),
) -> dict[str, Any]:
    """
    Find shortest path between two nodes.
    
    This enables multi-hop architectural reasoning.
    
    Args:
        request: Path finding request
        neo4j: Neo4j client
        
    Returns:
        Path with nodes and relationships
    """
    relation_types = None
    if request.relation_types:
        try:
            relation_types = [RelationType(rt) for rt in request.relation_types]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    try:
        paths = await neo4j.find_path(
            from_uid=request.from_uid,
            to_uid=request.to_uid,
            max_depth=request.max_depth,
            relation_types=relation_types,
        )

        return {
            "paths": paths,
            "count": len(paths),
        }
    except Exception as e:
        logger.exception("path_finding_failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/graph/schema", response_model=SchemaInfoResponse)
async def get_schema_info(
    neo4j: Neo4jClient = Depends(get_neo4j_client),
) -> SchemaInfoResponse:
    """
    Get schema validation information.
    
    Args:
        neo4j: Neo4j client
        
    Returns:
        Schema information
    """
    schema_info = await neo4j.get_schema_info()
    return SchemaInfoResponse(**schema_info)


# === MongoDB Endpoints ===


@app.post("/memory/chat")
async def save_chat_message(
    request: SaveChatMessageRequest,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
) -> dict[str, Any]:
    """
    Save a chat message to episodic memory.
    
    Args:
        request: Chat message request
        mongodb: MongoDB client
        
    Returns:
        Success response
    """
    message = ChatMessage(
        role=request.role,
        content=request.content,
        metadata=request.metadata,
    )

    try:
        await mongodb.save_chat_message(request.session_id, message)
        return {
            "success": True,
            "session_id": request.session_id,
            "message_role": request.role,
        }
    except Exception as e:
        logger.exception("chat_save_failed", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/sessions/{session_id}")
async def get_session(
    session_id: str,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
) -> dict[str, Any]:
    """
    Get a conversation session.
    
    Args:
        session_id: Session identifier
        mongodb: MongoDB client
        
    Returns:
        Session data
    """
    session = await mongodb.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    return session.model_dump()


@app.get("/memory/sessions")
async def get_recent_sessions(
    limit: int = 10,
    project_context: str | None = None,
    mongodb: MongoDBClient = Depends(get_mongodb_client),
) -> dict[str, Any]:
    """
    Get recent conversation sessions.
    
    Args:
        limit: Maximum number of sessions
        project_context: Optional project filter
        mongodb: MongoDB client
        
    Returns:
        List of sessions
    """
    sessions = await mongodb.get_recent_sessions(limit=limit, project_context=project_context)

    return {
        "sessions": [s.model_dump() for s in sessions],
        "count": len(sessions),
    }


if __name__ == "__main__":
    import uvicorn

    settings = get_settings()
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info",
    )

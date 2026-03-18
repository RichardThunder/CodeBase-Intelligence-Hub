"""Request/response schemas for API endpoints."""

from pydantic import BaseModel, Field
from typing import Optional, Any


class ChatRequest(BaseModel):
    """Chat endpoint request."""
    query: str = Field(..., description="User query")
    session_id: str = Field(default="default", description="Session ID for history")
    include_sources: bool = Field(default=True, description="Include source documents in response")


class ChatResponse(BaseModel):
    """Chat endpoint response."""
    answer: str = Field(..., description="Generated answer")
    session_id: str = Field(..., description="Session ID")
    sources: list[dict] = Field(default_factory=list, description="Source documents")
    metadata: dict = Field(default_factory=dict, description="Additional metadata")


class StreamToken(BaseModel):
    """Token for streaming response."""
    token: str = Field(..., description="Token content")
    type: str = Field(default="text", description="Token type (text/end/error)")


class IngestRequest(BaseModel):
    """Ingest endpoint request."""
    repo_path: str = Field(..., description="Path to repository")
    collection: str = Field(default="codebase_v1", description="ChromaDB collection name")
    use_parser: bool = Field(default=True, description="Use language-aware parser")


class IngestResponse(BaseModel):
    """Ingest endpoint response."""
    success: bool = Field(..., description="Whether ingestion succeeded")
    chunks_created: int = Field(default=0, description="Number of chunks created")
    collection: str = Field(..., description="Collection name")
    message: str = Field(default="", description="Status message")


class HealthResponse(BaseModel):
    """Health check response."""
    status: str = Field(default="ok", description="Health status")
    timestamp: str = Field(..., description="Server timestamp")
    services: dict[str, str] = Field(default_factory=dict, description="Service statuses")

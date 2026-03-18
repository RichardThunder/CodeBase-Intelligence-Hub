"""API route handlers."""

from datetime import datetime
from typing import AsyncGenerator
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from langchain_core.language_model import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from api.schemas import (
    ChatRequest,
    ChatResponse,
    IngestRequest,
    IngestResponse,
    HealthResponse,
)
from graph.builder import build_graph
from config.settings import Settings
from memory import update_session_history, get_session_history
from retrieval.ingestion import ingest_repo


def create_routes(
    retriever: BaseRetriever,
    llm: BaseLanguageModel,
    settings: Settings,
) -> APIRouter:
    """Create API routes with dependencies injected.

    Args:
        retriever: Retriever for code search
        llm: Language model for reasoning
        settings: Configuration settings

    Returns:
        APIRouter with all routes registered
    """
    router = APIRouter(prefix="/api", tags=["chat"])

    # Build graph once
    graph = build_graph(retriever, llm, settings)

    @router.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest) -> ChatResponse:
        """Chat endpoint - invoke graph with query.

        Args:
            request: ChatRequest with query and session_id

        Returns:
            ChatResponse with answer and optional sources
        """
        try:
            # Build input state
            history = get_session_history(request.session_id)

            state_input = {
                "user_query": request.query,
                "session_id": request.session_id,
                "history": history,
                "intent": "",
                "next_agent": "",
                "retrieved_chunks": [],
                "analysis_results": [],
                "code_outputs": [],
                "search_results": [],
                "final_answer": "",
                "requires_human_approval": False,
                "human_approval_given": False,
                "error_message": None,
                "iteration_count": 0,
                "timestamps": [],
            }

            # Invoke graph
            result = graph.invoke(state_input)

            answer = result.get("final_answer", "No answer generated")

            # Update history
            update_session_history(request.session_id, "user", request.query)
            update_session_history(request.session_id, "assistant", answer)

            # Extract sources if requested
            sources = []
            if request.include_sources:
                sources = [
                    {
                        "file_path": chunk.get("file_path"),
                        "preview": chunk.get("content", "")[:200],
                    }
                    for chunk in result.get("retrieved_chunks", [])
                ]

            return ChatResponse(
                answer=answer,
                session_id=request.session_id,
                sources=sources,
                metadata={
                    "intent": result.get("intent"),
                    "confidence": result.get("intent_confidence", 0),
                    "iterations": result.get("iteration_count", 0),
                },
            )

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")

    @router.get("/chat/stream")
    async def stream_chat(
        query: str = Query(..., description="User query"),
        session_id: str = Query(default="default", description="Session ID"),
    ) -> AsyncGenerator[str, None]:
        """Stream chat response as Server-Sent Events.

        Args:
            query: User query
            session_id: Session ID for history

        Yields:
            Token strings as SSE format
        """
        try:
            # Build input state
            history = get_session_history(session_id)

            state_input = {
                "user_query": query,
                "session_id": session_id,
                "history": history,
                "intent": "",
                "next_agent": "",
                "retrieved_chunks": [],
                "analysis_results": [],
                "code_outputs": [],
                "search_results": [],
                "final_answer": "",
                "requires_human_approval": False,
                "human_approval_given": False,
                "error_message": None,
                "iteration_count": 0,
                "timestamps": [],
            }

            # Stream graph execution
            for chunk in graph.stream(state_input, stream_mode="values"):
                if "final_answer" in chunk and chunk["final_answer"]:
                    yield f"data: {chunk['final_answer']}\n\n"

            yield "data: [DONE]\n\n"

        except Exception as e:
            yield f"data: Error: {str(e)}\n\n"

    @router.post("/ingest", response_model=IngestResponse)
    async def ingest(
        request: IngestRequest,
        background_tasks: BackgroundTasks,
    ) -> IngestResponse:
        """Ingest repository in background.

        Args:
            request: IngestRequest with repo path
            background_tasks: FastAPI background task queue

        Returns:
            IngestResponse confirming ingestion started
        """
        try:
            # Run ingestion in background
            background_tasks.add_task(
                ingest_repo,
                request.repo_path,
                settings,
                request.use_parser,
            )

            return IngestResponse(
                success=True,
                chunks_created=0,  # Will update after background task completes
                collection=request.collection,
                message=f"Ingestion started for {request.repo_path}",
            )

        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Ingest error: {str(e)}")

    @router.get("/health", response_model=HealthResponse)
    async def health() -> HealthResponse:
        """Health check endpoint.

        Returns:
            HealthResponse with service status
        """
        return HealthResponse(
            status="ok",
            timestamp=datetime.now().isoformat(),
            services={
                "graph": "ready",
                "retriever": "ready",
                "llm": "ready",
                "memory": "ready",
            },
        )

    @router.get("/sessions/{session_id}/history")
    async def get_history(session_id: str) -> dict:
        """Get conversation history for session.

        Args:
            session_id: Session ID

        Returns:
            Dictionary with history list
        """
        history = get_session_history(session_id)
        return {"session_id": session_id, "history": history}

    return router

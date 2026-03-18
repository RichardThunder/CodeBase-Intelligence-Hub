"""FastAPI application entry point with LangServe integration."""

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from langserve import add_routes
from dotenv import load_dotenv

from config.settings import Settings
from retrieval.vectorstore import get_vectorstore
from retrieval.embeddings import get_embeddings
from retrieval.pipeline import build_retrieval_pipeline
from chains.rag import build_rag_chain, build_rag_chain_with_source
from langchain_openai import ChatOpenAI
from api.routes import create_routes


# Global instances
_settings = None
_llm = None
_graph = None
_rag_chain = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown.

    Initialize components on startup, cleanup on shutdown.
    """
    global _settings, _llm, _graph, _rag_chain

    # Startup
    print("⏳ Initializing CodeBase Intelligence Hub API...")

    load_dotenv()
    _settings = Settings()

    # Initialize LLM
    _llm = ChatOpenAI(
        model=_settings.llm_model,
        temperature=0,
        api_key=_settings.openai_api_key.get_secret_value(),
        base_url=_settings.openai_api_base,
    )
    print("✅ LLM initialized")

    # Initialize embeddings and vector store (without loading documents)
    try:
        embeddings = get_embeddings(_settings)
        vectorstore = get_vectorstore(_settings)
        print(f"✅ Vector store initialized: {_settings.chroma_collection}")

        # Initialize with empty retriever - will be built after ingest
        retriever = vectorstore.as_retriever()

        # Build RAG chain with empty retriever
        _rag_chain = build_rag_chain(retriever, _llm)
        print("✅ RAG chain initialized (awaiting document ingestion)")

        # Build LangGraph (imported here to avoid circular dependencies)
        from graph.builder import build_graph
        _graph = build_graph(retriever, _llm, _settings)
        print("✅ LangGraph orchestrator initialized")

        # Register API routes
        api_routes = create_routes(_graph, _llm, _settings)
        app.include_router(api_routes)
        print("✅ API routes registered")

        # Add RAG chain via LangServe
        add_routes(app, _rag_chain, path="/rag")
        print("✅ LangServe RAG endpoint registered")

    except Exception as e:
        print(f"⚠️  Warning during initialization: {e}")
        print("💡 Core services may not be fully initialized")

    print("\n" + "="*60)
    print("🚀 API ready at http://localhost:8000")
    print("="*60)
    print("\n📋 Next steps:")
    print("  1. Open http://localhost:8000")
    print("  2. Enter your project folder path in the sidebar")
    print("  3. Click '📥 Ingest' to index your codebase")
    print("  4. Start asking questions about your code!\n")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("🔌 LangServe Playground: http://localhost:8000/rag/playground")

    yield

    # Shutdown
    print("⏹️  Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="CodeBase Intelligence Hub",
    description="RAG-based codebase Q&A system with multi-agent orchestration",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for local development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
static_dir = Path(__file__).parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/")
async def root():
    """Root endpoint - serve the frontend UI."""
    index_file = Path(__file__).parent.parent / "static" / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))

    # Fallback if index.html doesn't exist
    from fastapi.responses import HTMLResponse
    return HTMLResponse("""
    <html>
        <head>
            <title>CodeBase Intelligence Hub</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; background: #1e1e1e; color: #d4d4d4; }
                h1 { color: #007acc; }
                ul { line-height: 1.8; }
                a { color: #007acc; text-decoration: none; }
                a:hover { text-decoration: underline; }
                code { background: #252526; padding: 2px 5px; border-radius: 3px; }
            </style>
        </head>
        <body>
            <h1>🧠 CodeBase Intelligence Hub</h1>
            <p>RAG-based codebase Q&A system with multi-agent orchestration</p>
            <p><strong>Note:</strong> Frontend UI not found. Please check that static/index.html exists.</p>

            <h2>📚 Documentation</h2>
            <ul>
                <li><a href="/docs">Interactive API docs (Swagger)</a></li>
                <li><a href="/redoc">ReDoc documentation</a></li>
                <li><a href="/rag/playground">LangServe RAG Playground</a></li>
            </ul>
        </body>
    </html>
    """)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )

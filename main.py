"""
CodeBase Intelligence Hub - Main Entry Point

Run the FastAPI server with: python main.py
The frontend UI will be available at: http://localhost:8000
"""


def main() -> None:
    """Start the FastAPI server."""
    import uvicorn
    from api.main import app

    print("\n" + "=" * 60)
    print("🚀 Starting CodeBase Intelligence Hub")
    print("=" * 60)
    print("\n📖 Frontend:     http://localhost:8000")
    print("📚 API Docs:     http://localhost:8000/docs")
    print("🔌 Playground:   http://localhost:8000/rag/playground")
    print("\nPress Ctrl+C to stop the server\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()

#!/usr/bin/env python
"""CLI tool for ingesting a codebase into ChromaDB."""

import argparse
import sys
from pathlib import Path
from dotenv import load_dotenv
from config.settings import Settings
from retrieval.ingestion import ingest_repo


def main():
    """Run codebase ingestion from command line."""
    parser = argparse.ArgumentParser(
        description="Ingest a codebase into ChromaDB for RAG"
    )
    parser.add_argument(
        "--repo-path",
        type=str,
        default=".",
        help="Path to repository root (default: current directory)",
    )
    parser.add_argument(
        "--collection",
        type=str,
        default=None,
        help="ChromaDB collection name (overrides config default)",
    )
    parser.add_argument(
        "--persist-dir",
        type=str,
        default=None,
        help="ChromaDB persist directory (overrides config default)",
    )
    parser.add_argument(
        "--use-parser",
        action="store_true",
        default=True,
        help="Use language-aware parser (default: True)",
    )
    parser.add_argument(
        "--no-parser",
        action="store_true",
        help="Use simple loaders instead of language parser",
    )

    args = parser.parse_args()

    # Load environment
    load_dotenv()

    # Get settings
    settings = Settings()

    # Override settings if provided
    if args.collection:
        settings.chroma_collection = args.collection
    if args.persist_dir:
        settings.chroma_persist_dir = args.persist_dir

    # Validate repo path
    repo_path = Path(args.repo_path)
    if not repo_path.exists():
        print(f"❌ Repository path does not exist: {repo_path}")
        sys.exit(1)

    print(f"📂 Ingesting repository: {repo_path.resolve()}")
    print(f"📦 Collection: {settings.chroma_collection}")
    print(f"💾 Persist dir: {settings.chroma_persist_dir}")
    print()

    try:
        use_parser = not args.no_parser
        chunk_count = ingest_repo(str(repo_path), settings, use_parser=use_parser)

        print()
        print(f"✅ Ingestion complete!")
        print(f"📊 Total chunks created: {chunk_count}")
        print()
        print("You can now use the RAG chain with:")
        print("  from chains.rag import build_rag_chain")
        print("  from retrieval.vectorstore import get_vectorstore")
        print("  chain = build_rag_chain(vectorstore.as_retriever(), llm)")

    except Exception as e:
        print(f"❌ Ingestion failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

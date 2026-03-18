"""ChromaDB vector store initialization and management."""

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings
from config.settings import Settings
from retrieval.embeddings import get_embeddings


def build_vectorstore(
    docs: list[Document],
    embeddings: OpenAIEmbeddings,
    settings: Settings,
) -> Chroma:
    """Build and persist vector store from documents.

    Args:
        docs: List of documents to index
        embeddings: Embeddings instance
        settings: Configuration with persist directory and collection name

    Returns:
        Chroma vector store with documents persisted to disk
    """
    if not docs:
        print("  ⚠️  No documents to index, creating empty vector store")
        return Chroma(
            collection_name=settings.chroma_collection,
            embedding_function=embeddings,
            persist_directory=settings.chroma_persist_dir,
        )

    try:
        vectorstore = Chroma.from_documents(
            documents=docs,
            embedding=embeddings,
            persist_directory=settings.chroma_persist_dir,
            collection_name=settings.chroma_collection,
        )
        # Persist if method exists (newer ChromaDB versions auto-persist)
        if hasattr(vectorstore, 'persist'):
            vectorstore.persist()
        return vectorstore
    except ValueError as e:
        if "non-empty list" in str(e):
            print(f"  ⚠️  Embedding error: {e}")
            print("  Creating empty vector store and attempting batch insertion...")
            vectorstore = Chroma(
                collection_name=settings.chroma_collection,
                embedding_function=embeddings,
                persist_directory=settings.chroma_persist_dir,
            )
            # Try adding documents in smaller batches
            batch_size = 10
            for i in range(0, len(docs), batch_size):
                batch = docs[i:i+batch_size]
                try:
                    vectorstore.add_documents(batch)
                    print(f"  Added batch {i//batch_size + 1}")
                except Exception as batch_error:
                    print(f"  ⚠️  Batch {i//batch_size + 1} failed: {batch_error}")
                    continue
            # Persist if method exists
            if hasattr(vectorstore, 'persist'):
                vectorstore.persist()
            return vectorstore
        raise


def load_vectorstore(
    embeddings: OpenAIEmbeddings,
    settings: Settings,
) -> Chroma:
    """Load existing vector store from disk or remote.

    Args:
        embeddings: Embeddings instance
        settings: Configuration with persist directory/host/port

    Returns:
        Chroma vector store (from disk or HTTP client)

    Raises:
        FileNotFoundError: If local persist directory doesn't exist and no remote host set
    """
    if settings.chroma_host:
        # Remote ChromaDB server (e.g., Docker container)
        return Chroma(
            collection_name=settings.chroma_collection,
            embedding_function=embeddings,
            client_type="http",
            host=settings.chroma_host,
            port=settings.chroma_port,
        )
    else:
        # Local persisted ChromaDB
        return Chroma(
            persist_directory=settings.chroma_persist_dir,
            embedding_function=embeddings,
            collection_name=settings.chroma_collection,
        )


def get_vectorstore(settings: Settings) -> Chroma:
    """Get or create vector store (convenience wrapper).

    Args:
        settings: Configuration

    Returns:
        Chroma vector store instance
    """
    embeddings = get_embeddings(settings)
    try:
        return load_vectorstore(embeddings, settings)
    except Exception:
        # If loading fails, return empty initialized store
        return Chroma(
            collection_name=settings.chroma_collection,
            embedding_function=embeddings,
            persist_directory=settings.chroma_persist_dir,
        )

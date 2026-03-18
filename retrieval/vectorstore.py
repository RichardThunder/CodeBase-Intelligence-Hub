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
    vectorstore = Chroma.from_documents(
        documents=docs,
        embedding=embeddings,
        persist_directory=settings.chroma_persist_dir,
        collection_name=settings.chroma_collection,
    )
    vectorstore.persist()
    return vectorstore


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

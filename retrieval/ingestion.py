"""Document ingestion pipeline: loaders → splitters → vectorstore."""

from pathlib import Path
from langchain_core.documents import Document
from retrieval.loaders import load_codebase_with_parser, load_docs_simple
from retrieval.splitters import split_document
from retrieval.vectorstore import build_vectorstore, get_vectorstore
from retrieval.embeddings import get_embeddings
from config.settings import Settings


def extract_git_metadata(docs: list[Document], repo_path: str) -> list[Document]:
    """Enrich documents with git-based metadata.

    Args:
        docs: List of documents from loaders
        repo_path: Root path of repository

    Returns:
        Documents with added git metadata (repo_root, relative_path, etc.)
    """
    repo_root = Path(repo_path).resolve()
    for doc in docs:
        source = doc.metadata.get("source", "")
        if source:
            try:
                rel_path = Path(source).relative_to(repo_root)
                doc.metadata["repo_root"] = str(repo_root)
                doc.metadata["relative_path"] = str(rel_path)
            except ValueError:
                # Path is not under repo_root, skip enrichment
                pass
    return docs


def ingest_repo(repo_path: str, settings: Settings, use_parser: bool = True) -> int:
    """Ingest entire codebase into vector store.

    Args:
        repo_path: Path to repository root
        settings: Configuration with model/vectorstore settings
        use_parser: Use language-aware parser (True) vs simple loaders (False)

    Returns:
        Total number of chunks ingested
    """
    # Load documents
    if use_parser:
        docs = load_codebase_with_parser(repo_path)
    else:
        docs = load_docs_simple(repo_path)

    # Enrich with git metadata
    docs = extract_git_metadata(docs, repo_path)

    # Split documents
    split_docs = split_document(docs, use_python_for_py=True)

    # Build and persist vector store
    embeddings = get_embeddings(settings)
    vectorstore = build_vectorstore(split_docs, embeddings, settings)

    return len(split_docs)


def ingest_single_document(
    doc_path: str,
    settings: Settings,
    collection_name: str = None,
) -> int:
    """Ingest a single document and add to vector store.

    Args:
        doc_path: Path to single file
        settings: Configuration
        collection_name: Override collection name if provided

    Returns:
        Number of chunks created from document
    """
    from langchain_community.document_loaders import TextLoader

    loader = TextLoader(doc_path, encoding="utf-8")
    docs = loader.load()

    split_docs = split_document(docs, use_python_for_py=False)

    embeddings = get_embeddings(settings)
    vectorstore = get_vectorstore(settings)

    vectorstore.add_documents(split_docs)
    vectorstore.persist()

    return len(split_docs)

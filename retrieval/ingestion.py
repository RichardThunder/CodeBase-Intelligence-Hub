"""Document ingestion pipeline: loaders → splitters → vectorstore."""

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
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


def _add_documents_batch(
    vectorstore,
    batch: list[Document],
    batch_index: int,
    total_batches: int,
) -> int:
    """Add a batch of documents to vectorstore.

    Args:
        vectorstore: Vector store instance
        batch: Batch of documents to add
        batch_index: Current batch index (for progress reporting)
        total_batches: Total number of batches

    Returns:
        Number of documents added
    """
    try:
        vectorstore.add_documents(batch)
        progress = f"({batch_index}/{total_batches})"
        print(f"  📝 Added batch {progress}: {len(batch)} chunks")
        return len(batch)
    except Exception as e:
        print(f"  ❌ Error adding batch {batch_index}: {e}")
        return 0


def ingest_repo(
    repo_path: str,
    settings: Settings,
    use_parser: bool = True,
    num_threads: int = 4,
    batch_size: int = 100,
) -> int:
    """Ingest entire codebase into vector store with multi-threading.

    Args:
        repo_path: Path to repository root
        settings: Configuration with model/vectorstore settings
        use_parser: Use language-aware parser (True) vs simple loaders (False)
        num_threads: Number of threads for document splitting
        batch_size: Number of documents to add per batch

    Returns:
        Total number of chunks ingested
    """
    print(f"\n📥 Ingesting repository from: {repo_path}")

    # Load documents
    print("  🔍 Loading documents...")
    if use_parser:
        docs = load_codebase_with_parser(repo_path)
    else:
        docs = load_docs_simple(repo_path)
    print(f"  ✅ Loaded {len(docs)} documents")

    # Enrich with git metadata
    print("  🏷️  Enriching with metadata...")
    docs = extract_git_metadata(docs, repo_path)

    # Split documents with multi-threading
    print(f"  ✂️  Splitting documents ({num_threads} threads)...")
    split_docs = split_document(docs, use_python_for_py=True, num_threads=num_threads)
    print(f"  ✅ Created {len(split_docs)} chunks")

    # Build vector store and add documents in batches
    print("  🗂️  Building vector store and adding documents...")
    embeddings = get_embeddings(settings)
    vectorstore = build_vectorstore([], embeddings, settings)

    # Add documents in batches with multi-threading
    total_added = 0
    total_batches = (len(split_docs) + batch_size - 1) // batch_size

    if total_batches > 1:
        print(f"  📦 Adding {len(split_docs)} chunks in {total_batches} batches ({num_threads} threads)...")
        with ThreadPoolExecutor(max_workers=min(num_threads, total_batches)) as executor:
            futures = []
            for batch_idx in range(total_batches):
                start_idx = batch_idx * batch_size
                end_idx = min((batch_idx + 1) * batch_size, len(split_docs))
                batch = split_docs[start_idx:end_idx]

                future = executor.submit(
                    _add_documents_batch,
                    vectorstore,
                    batch,
                    batch_idx + 1,
                    total_batches,
                )
                futures.append(future)

            # Collect results
            for future in futures:
                try:
                    added = future.result()
                    total_added += added
                except Exception as e:
                    print(f"  ❌ Batch processing error: {e}")
    else:
        # Single batch - add directly
        vectorstore.add_documents(split_docs)
        total_added = len(split_docs)
        print(f"  ✅ Added {len(split_docs)} chunks")

    # Persist
    vectorstore.persist()
    print(f"\n✅ Ingestion complete: {total_added} chunks indexed")

    return total_added


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

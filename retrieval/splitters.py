from concurrent.futures import ThreadPoolExecutor, as_completed
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_text_splitters import Language
from langchain_core.documents import Document


def get_doc_splitter(chund_size: int = 800, chunk_overlap: int = 150):
    return RecursiveCharacterTextSplitter(
        chunk_size=chund_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )


def get_python_splitter(chunk_size: int = 1000, chunk_overlap: int = 200):
    return RecursiveCharacterTextSplitter.from_language(
        language=Language.PYTHON,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


def _split_single_document(
    doc: Document,
    py_splitter: RecursiveCharacterTextSplitter,
    doc_splitter: RecursiveCharacterTextSplitter,
    use_python_for_py: bool = True,
) -> list[Document]:
    """Split a single document using appropriate splitter."""
    lang = doc.metadata.get("language", "")
    if use_python_for_py and lang == "python":
        return py_splitter.split_documents([doc])
    else:
        return doc_splitter.split_documents([doc])


def split_document(
    docs: list[Document],
    use_python_for_py: bool = True,
    num_threads: int = 4,
) -> list[Document]:
    """Split documents into chunks using multi-threading.

    Args:
        docs: List of documents to split
        use_python_for_py: Use Python-aware splitter for Python files
        num_threads: Number of threads for parallel processing

    Returns:
        List of split documents
    """
    if not docs:
        return []

    # Initialize splitters
    py_splitter = get_python_splitter()
    doc_splitter = get_doc_splitter()

    # Single document - no threading overhead
    if len(docs) == 1:
        return _split_single_document(docs[0], py_splitter, doc_splitter, use_python_for_py)

    # Multi-threaded processing for multiple documents
    out = []
    with ThreadPoolExecutor(max_workers=min(num_threads, len(docs))) as executor:
        # Submit all tasks
        future_to_doc = {
            executor.submit(
                _split_single_document,
                doc,
                py_splitter,
                doc_splitter,
                use_python_for_py,
            ): doc
            for doc in docs
        }

        # Collect results as they complete
        for future in as_completed(future_to_doc):
            try:
                split_docs = future.result()
                out.extend(split_docs)
            except Exception as e:
                doc = future_to_doc[future]
                print(f"⚠️  Error splitting document {doc.metadata.get('source', 'unknown')}: {e}")

    return out

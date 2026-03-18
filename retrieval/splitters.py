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


def split_document(docs: list[Document], use_python_for_py: bool = True):
    py_splitter = get_python_splitter()
    doc_splitter = get_doc_splitter()
    out = []
    for doc in docs:
        lang = doc.metadata.get("language", "")
        if use_python_for_py and lang == "python":
            out.extend(py_splitter.split_documents([doc]))
        else:
            out.extend(doc_splitter.split_documents([doc]))
    return out

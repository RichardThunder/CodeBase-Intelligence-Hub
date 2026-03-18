from pathlib import Path
from langchain_community.document_loaders import (
    DirectoryLoader,
    TextLoader,
    UnstructuredMarkdownLoader,
    PythonLoader,
)
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers import LanguageParser
from langchain_core.documents import Document


def load_docs_simple(dir_path: str) -> list[Document]:
    docs = []
    loaders = [
        DirectoryLoader(
            dir_path,
            glob="**/*.py",
            loader_cls=PythonLoader,
            loader_kwargs={"encoding": "utf-8"},
            show_progress=True,
        ),
        DirectoryLoader(
            dir_path,
            glob="*/*.md",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
            show_progress=True,
        ),
    ]

    for loader in loaders:
        docs.extend(loader.load())
    return docs


def load_codebase_with_parser(repo_path: str) -> list[Document]:

    loader = GenericLoader.from_filesystem(
        repo_path,
        glob="**/*.py",
        suffixes=[".py"],
        parser=LanguageParser(language="python", parser_threshold=500),
        show_progress=True,
    )
    docs = loader.load()
    for doc in docs:
        path = doc.metadata.get("source", "")
        doc.metadata["file_path"] = path
        doc.metadata["language"] = "python"
    return docs


if __name__ == "__main__":
    # docs = load_docs_simple(".")
    # print(docs)
    # doc_sources = [doc.metadata["source"] for doc in docs]
    # print("Loaded document sources:", doc_sources)

    docs = load_codebase_with_parser(".")
    doc_sources = [doc.metadata["source"] for doc in docs]
    print("Loaded document sources:", doc_sources)

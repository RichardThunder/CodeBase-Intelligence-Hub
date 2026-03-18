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
    """Load Python and Markdown files, excluding virtual environments and caches.

    Args:
        repo_path: Path to repository root

    Returns:
        List of Documents with parsed Python and Markdown code
    """
    from pathlib import Path
    import fnmatch

    # Directories to exclude
    EXCLUDE_DIRS = {
        ".venv", "venv", "env", ".env",
        "__pycache__", ".pytest_cache", ".mypy_cache",
        "node_modules", ".git", ".idea", ".vscode",
        "dist", "build", "*.egg-info",
        ".next", ".svelte-kit",
    }

    def should_exclude(path_str: str) -> bool:
        """Check if path should be excluded."""
        path = Path(path_str)
        # Check each part of the path
        for part in path.parts:
            if part in EXCLUDE_DIRS or any(fnmatch.fnmatch(part, pattern) for pattern in EXCLUDE_DIRS):
                return True
        return False

    print("  🔍 Loading Python files...")
    # Load Python files with error handling
    loader = GenericLoader.from_filesystem(
        repo_path,
        glob="**/*.py",
        suffixes=[".py"],
        parser=LanguageParser(language="python", parser_threshold=500),
        show_progress=False,  # Disable progress to avoid clutter with errors
    )

    filtered_docs = []
    skipped_count = 0

    try:
        for doc in loader.lazy_load():
            path = doc.metadata.get("source", "")
            if not should_exclude(path):
                doc.metadata["file_path"] = path
                doc.metadata["language"] = "python"
                filtered_docs.append(doc)
    except UnicodeDecodeError as e:
        print(f"  ⚠️  Skipping file with encoding error: {e}")
        skipped_count += 1
    except Exception as e:
        print(f"  ⚠️  Error loading Python files: {e}")

    print(f"  ✅ Loaded {len(filtered_docs)} Python files")

    print("  🔍 Loading Markdown files...")
    # Also load Markdown files with error handling
    try:
        md_loader = DirectoryLoader(
            repo_path,
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8", "autodetect_encoding": True},
            show_progress=False,
        )
        md_docs = md_loader.load()
    except Exception as e:
        print(f"  ⚠️  Error loading Markdown files: {e}")
        md_docs = []

    # Filter Markdown docs
    filtered_md_docs = []
    for doc in md_docs:
        path = doc.metadata.get("source", "")
        if not should_exclude(path):
            doc.metadata["file_path"] = path
            doc.metadata["language"] = "markdown"
            filtered_md_docs.append(doc)

    print(f"  ✅ Loaded {len(filtered_md_docs)} Markdown files")

    return filtered_docs + filtered_md_docs


if __name__ == "__main__":
    # docs = load_docs_simple(".")
    # print(docs)
    # doc_sources = [doc.metadata["source"] for doc in docs]
    # print("Loaded document sources:", doc_sources)

    docs = load_codebase_with_parser(".")
    doc_sources = [doc.metadata["source"] for doc in docs]
    print("Loaded document sources:", doc_sources)

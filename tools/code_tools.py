"""Code analysis and search tools for agents."""

import ast
import os
from pathlib import Path
from typing import Any, Optional
from langchain_core.tools import tool
from langchain_core.retrievers import BaseRetriever


@tool
def codebase_search(query: str, retriever: BaseRetriever, top_k: int = 5) -> str:
    """Search the codebase for code snippets matching the query.

    Args:
        query: Natural language search query
        retriever: Retriever instance (passed by closure)
        top_k: Number of results to return

    Returns:
        Formatted search results with file paths and code snippets
    """
    try:
        docs = retriever.invoke(query)[:top_k]
        if not docs:
            return "No relevant code snippets found."

        results = []
        for i, doc in enumerate(docs, 1):
            source = doc.metadata.get("file_path", doc.metadata.get("source", "unknown"))
            content = doc.page_content[:300]
            results.append(f"【结果 {i}】{source}\n{content}...")

        return "\n\n".join(results)
    except Exception as e:
        return f"Search error: {str(e)}"


@tool
def symbol_lookup(
    symbol_name: str,
    repo_path: str = ".",
    file_path: Optional[str] = None,
) -> str:
    """Look up function/class definitions by name using AST.

    Args:
        symbol_name: Name of function, class, or variable to find
        repo_path: Root path to search (default: current dir)
        file_path: Specific file to search (optional)

    Returns:
        Location and definition of symbol, or "not found" message
    """
    repo_path = Path(repo_path)

    if file_path:
        # Search specific file
        file_to_search = Path(file_path)
        if not file_to_search.is_absolute():
            file_to_search = repo_path / file_to_search
        files_to_check = [file_to_search] if file_to_search.exists() else []
    else:
        # Search all Python files
        files_to_check = list(repo_path.glob("**/*.py"))

    results = []

    for file in files_to_check:
        try:
            with open(file, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read())

            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if node.name == symbol_name:
                        results.append(
                            f"Function '{symbol_name}' at {file}:{node.lineno}"
                        )
                elif isinstance(node, ast.ClassDef):
                    if node.name == symbol_name:
                        results.append(
                            f"Class '{symbol_name}' at {file}:{node.lineno}"
                        )
                elif isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == symbol_name:
                            results.append(
                                f"Variable '{symbol_name}' at {file}:{node.lineno}"
                            )
        except (SyntaxError, UnicodeDecodeError):
            continue

    if results:
        return "\n".join(results)
    return f"Symbol '{symbol_name}' not found in {repo_path}"


@tool
def file_tree_view(path_prefix: str = ".", max_depth: int = 3) -> str:
    """Generate a directory tree view of the repository.

    Args:
        path_prefix: Root path for tree
        max_depth: Maximum depth to traverse

    Returns:
        ASCII tree representation
    """
    root = Path(path_prefix)
    if not root.exists():
        return f"Path not found: {path_prefix}"

    lines = []

    def walk_dir(path: Path, prefix: str = "", depth: int = 0):
        if depth > max_depth:
            return

        try:
            items = sorted(path.iterdir())
        except PermissionError:
            return

        # Filter out common unimportant dirs
        skip_dirs = {
            "__pycache__",
            ".git",
            ".venv",
            "node_modules",
            ".egg-info",
            ".pytest_cache",
        }
        items = [i for i in items if i.name not in skip_dirs]

        for i, item in enumerate(items):
            is_last = i == len(items) - 1
            current_prefix = "└── " if is_last else "├── "
            lines.append(f"{prefix}{current_prefix}{item.name}")

            if item.is_dir() and not item.name.startswith("."):
                next_prefix = prefix + ("    " if is_last else "│   ")
                walk_dir(item, next_prefix, depth + 1)

    lines.append(root.name + "/")
    walk_dir(root, "", 0)

    return "\n".join(lines)


def get_code_tools(retriever: BaseRetriever) -> list:
    """Create and return all code analysis tools.

    Args:
        retriever: Retriever instance for codebase_search

    Returns:
        List of Tool objects ready for use in agents
    """
    tools = []

    # Create codebase_search with retriever bound
    @tool
    def search(query: str, top_k: int = 5) -> str:
        """Search codebase for relevant code snippets."""
        return codebase_search.invoke({
            "query": query,
            "top_k": top_k,
        })

    search_tool = search
    search_tool.func = lambda query, top_k=5: codebase_search.invoke({
        "query": query,
        "top_k": top_k,
    })

    # Actually, let's just wrap the search function properly
    from langchain_core.tools import Tool

    search_tool = Tool(
        name="codebase_search",
        description="Search the codebase for code snippets matching a query",
        func=lambda query: codebase_search.invoke({"query": query}),
    )

    tools.extend([
        search_tool,
        Tool(
            name="symbol_lookup",
            description="Look up function/class definitions by name using AST",
            func=lambda symbol_name: symbol_lookup.invoke({"symbol_name": symbol_name}),
        ),
        Tool(
            name="file_tree_view",
            description="Generate a directory tree view of the repository",
            func=lambda path_prefix=".": file_tree_view.invoke({
                "path_prefix": path_prefix
            }),
        ),
    ])

    return tools

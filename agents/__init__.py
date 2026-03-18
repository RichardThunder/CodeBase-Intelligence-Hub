"""Agents package - thin wrapper around LangGraph.

Agents are built as nodes in the LangGraph workflow defined in graph/builder.py.
This package provides convenience exports for external use.
"""

from graph.builder import build_graph, build_graph_from_settings

__all__ = [
    "build_graph",
    "build_graph_from_settings",
]

"""Build and compile the LangGraph workflow."""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.language_model import BaseLanguageModel
from langchain_core.retrievers import BaseRetriever
from config.settings import Settings
from graph.state import AgentState
from graph.nodes import (
    orchestrator_node,
    retrieval_node,
    analysis_node,
    code_node,
    search_node,
    synthesizer_node,
    human_approval_node,
)


def build_graph(
    retriever: BaseRetriever,
    llm: BaseLanguageModel,
    settings: Settings,
) -> "CompiledStateGraph":
    """Build complete LangGraph workflow.

    Args:
        retriever: BaseRetriever for code search
        llm: BaseLanguageModel for reasoning
        settings: Configuration settings

    Returns:
        Compiled StateGraph ready for invocation
    """
    workflow = StateGraph(AgentState)

    # Add node functions as closures with dependencies injected
    def orchestrator_wrapper(state):
        return orchestrator_node(state, llm)

    def retrieval_wrapper(state):
        return retrieval_node(state, retriever)

    def analysis_wrapper(state):
        return analysis_node(state, llm)

    def code_wrapper(state):
        return code_node(state, llm)

    # Register all nodes
    workflow.add_node("orchestrator", orchestrator_wrapper)
    workflow.add_node("retrieval", retrieval_wrapper)
    workflow.add_node("analysis", analysis_wrapper)
    workflow.add_node("code", code_wrapper)
    workflow.add_node("search", search_node)
    workflow.add_node("synthesizer", synthesizer_node)
    workflow.add_node("human_approval", human_approval_node)

    # Entry point
    workflow.set_entry_point("orchestrator")

    # Conditional routing from orchestrator
    def route_by_intent(state):
        agent = state.get("next_agent", "retrieval")
        return agent

    workflow.add_conditional_edges(
        "orchestrator",
        route_by_intent,
        {
            "retrieval": "retrieval",
            "analysis": "analysis",
            "code": "code",
            "search": "search",
            "synthesizer": "synthesizer",
        },
    )

    # Retrieval → Synthesizer (unless analysis needed)
    def route_after_retrieval(state):
        if state.get("intent") == "explanation":
            return "analysis"
        return "synthesizer"

    workflow.add_conditional_edges(
        "retrieval",
        route_after_retrieval,
        {
            "analysis": "analysis",
            "synthesizer": "synthesizer",
        },
    )

    # Analysis → Synthesizer
    workflow.add_edge("analysis", "synthesizer")

    # Code generation → Human approval or Synthesizer
    def route_after_code(state):
        if state.get("requires_human_approval"):
            return "human_approval"
        return "synthesizer"

    workflow.add_conditional_edges(
        "code",
        route_after_code,
        {
            "human_approval": "human_approval",
            "synthesizer": "synthesizer",
        },
    )

    # Search → Synthesizer
    workflow.add_edge("search", "synthesizer")

    # Human approval → Synthesizer (after approval)
    workflow.add_edge("human_approval", "synthesizer")

    # Synthesizer → END
    workflow.add_edge("synthesizer", END)

    # Compile with checkpointer for state persistence
    graph = workflow.compile(checkpointer=MemorySaver())

    return graph


def build_graph_from_settings(
    retriever: BaseRetriever,
    llm: BaseLanguageModel,
    settings: Settings = None,
) -> "CompiledStateGraph":
    """Convenience wrapper that uses default settings if not provided.

    Args:
        retriever: BaseRetriever for code search
        llm: BaseLanguageModel for reasoning
        settings: Optional configuration (uses Settings() if None)

    Returns:
        Compiled StateGraph
    """
    if settings is None:
        settings = Settings()

    return build_graph(retriever, llm, settings)

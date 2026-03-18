"""LangGraph state definition for multi-agent orchestration."""

from typing import Annotated, Optional, Any
from typing_extensions import TypedDict
import operator


class AgentState(TypedDict):
    """State passed through the LangGraph workflow.

    Tracks:
    - User input and session context
    - Intent classification and routing
    - Results from each agent type (accumulated)
    - Approval/error states
    """

    # Core input
    user_query: str
    session_id: str

    # Conversation history
    history: list[dict]  # [{"role": "user"/"assistant", "content": str}, ...]

    # Intent routing
    intent: str  # "code_lookup", "explanation", "bug_analysis", "general_qa"
    intent_confidence: float
    next_agent: str  # "retrieval", "analysis", "code", "search", "synthesizer"

    # Agent outputs (accumulated)
    retrieved_chunks: Annotated[list[dict], operator.add]
    analysis_results: Annotated[list[dict], operator.add]
    code_outputs: Annotated[list[dict], operator.add]
    search_results: Annotated[list[dict], operator.add]

    # Control flow
    final_answer: str
    requires_human_approval: bool
    human_approval_given: bool  # Set by external approval mechanism
    error_message: Optional[str]
    iteration_count: int

    # Metadata
    timestamps: Annotated[list[dict], operator.add]  # {"node": str, "timestamp": float}

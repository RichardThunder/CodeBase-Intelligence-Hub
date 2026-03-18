"""Node functions for LangGraph orchestration."""

import json
import re
from typing import Any
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser, JsonOutputParser
from langchain_core.retrievers import BaseRetriever
from graph.state import AgentState
from tools import get_code_tools, get_git_tools
from config.prompts import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    ANALYSIS_SYSTEM_PROMPT,
    CODE_GENERATION_SYSTEM_PROMPT,
    SYNTHESIZER_SYSTEM_PROMPT,
)


def clean_json_output(text: str) -> str:
    """Clean JSON output that might be wrapped in markdown code blocks.

    Handles formats like:
    - ```json\n{...}\n```
    - ```\n{...}\n```
    - Plain JSON
    """
    # Remove markdown code blocks
    text = re.sub(r'^```(?:json)?\s*\n?', '', text)
    text = re.sub(r'\n?```\s*$', '', text)
    return text.strip()


class IntentClassification(BaseModel):
    """LLM output for intent classification."""
    intent: str = Field(
        description="Intent type: code_lookup, explanation, bug_analysis, or general_qa"
    )
    confidence: float = Field(ge=0, le=1, description="Confidence 0-1")
    reasoning: str = Field(description="Brief reasoning")


def timestamp_node_entry(state: AgentState, node_name: str) -> dict:
    """Record node execution timestamp."""
    return {
        "timestamps": [
            {
                "node": node_name,
                "timestamp": datetime.now().isoformat(),
            }
        ]
    }


def orchestrator_node(
    state: AgentState,
    llm: BaseLanguageModel,
) -> dict:
    """Intent classification and routing orchestrator.

    Classifies user intent and determines next agent to invoke.
    """
    # Early return if already classified
    if state.get("intent") and state.get("next_agent"):
        return {}

    # Classify intent using production prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", ORCHESTRATOR_SYSTEM_PROMPT),
        ("human", "{query}"),
    ])

    # Use custom JSON parser with markdown cleanup
    parser = JsonOutputParser(pydantic_object=IntentClassification)
    chain = prompt | llm | StrOutputParser() | (lambda x: json.loads(clean_json_output(x))) | (lambda x: IntentClassification(**x))

    try:
        classification = chain.invoke({"query": state["user_query"]})
    except Exception as e:
        # Fallback: try with structured output
        print(f"⚠️  Custom parsing failed: {e}, trying structured output...")
        structured_llm = llm.with_structured_output(IntentClassification)
        fallback_chain = prompt | structured_llm
        classification = fallback_chain.invoke({"query": state["user_query"]})

    # Route to appropriate agent
    intent = classification.intent.lower()
    routing_map = {
        "code_lookup": "retrieval",
        "explanation": "analysis",
        "bug_analysis": "analysis",
        "general_qa": "retrieval",
    }
    next_agent = routing_map.get(intent, "retrieval")

    return {
        "intent": intent,
        "intent_confidence": classification.confidence,
        "next_agent": next_agent,
        "timestamps": timestamp_node_entry(state, "orchestrator")["timestamps"],
    }


def retrieval_node(
    state: AgentState,
    retriever: BaseRetriever,
) -> dict:
    """Retrieval agent: fetch relevant code snippets."""
    if state.get("retrieved_chunks"):
        return {}  # Already retrieved

    try:
        docs = retriever.invoke(state["user_query"])

        retrieved_chunks = [
            {
                "file_path": doc.metadata.get("file_path", doc.metadata.get("source", "unknown")),
                "content": doc.page_content,
                "metadata": doc.metadata,
            }
            for doc in docs
        ]

        return {
            "retrieved_chunks": retrieved_chunks,
            "next_agent": "analysis" if state["intent"] == "explanation" else "synthesizer",
            "timestamps": timestamp_node_entry(state, "retrieval")["timestamps"],
        }
    except Exception as e:
        return {
            "error_message": f"Retrieval error: {str(e)}",
            "next_agent": "synthesizer",
            "timestamps": timestamp_node_entry(state, "retrieval")["timestamps"],
        }


def analysis_node(
    state: AgentState,
    llm: BaseLanguageModel,
) -> dict:
    """Analysis agent: analyze code and provide insights."""
    if state.get("analysis_results"):
        return {}  # Already analyzed

    if not state.get("retrieved_chunks"):
        return {
            "error_message": "No retrieved chunks for analysis",
            "next_agent": "synthesizer",
        }

    # Format context from retrieved chunks
    # Escape curly braces to prevent LangChain template parsing
    context = "\n\n".join([
        f"【{chunk['file_path']}】\n{chunk['content'][:500].replace('{', '{{').replace('}', '}}')}"
        for chunk in state["retrieved_chunks"][:3]
    ])

    prompt = ChatPromptTemplate.from_messages([
        ("system", ANALYSIS_SYSTEM_PROMPT),
        ("human", f"""User Question: {state['user_query']}

Code Context:
{context}

Please provide detailed analysis."""),
    ])

    analysis = prompt | llm | StrOutputParser()
    result = analysis.invoke({})

    return {
        "analysis_results": [
            {
                "analysis": result,
                "chunks_analyzed": len(state.get("retrieved_chunks", [])),
            }
        ],
        "next_agent": "synthesizer",
        "timestamps": timestamp_node_entry(state, "analysis")["timestamps"],
    }


def code_node(
    state: AgentState,
    llm: BaseLanguageModel,
) -> dict:
    """Code generation agent: generate or fix code.

    This agent requires human approval before execution.
    """
    # Plan code generation using production prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", CODE_GENERATION_SYSTEM_PROMPT),
        ("human", state["user_query"]),
    ])

    code_gen = prompt | llm | StrOutputParser()
    generated_code = code_gen.invoke({})

    return {
        "code_outputs": [
            {
                "generated_code": generated_code,
                "requires_approval": True,
            }
        ],
        "requires_human_approval": True,
        "next_agent": "human_approval" if True else "synthesizer",
        "timestamps": timestamp_node_entry(state, "code")["timestamps"],
    }


def search_node(
    state: AgentState,
) -> dict:
    """Web search agent: find external information.

    Placeholder - would integrate with DuckDuckGo or Tavily.
    """
    # In production, would call external search API
    return {
        "search_results": [
            {
                "query": state["user_query"],
                "results": "Search not configured",
            }
        ],
        "next_agent": "synthesizer",
        "timestamps": timestamp_node_entry(state, "search")["timestamps"],
    }


def synthesizer_node(
    state: AgentState,
    llm: BaseLanguageModel,
) -> dict:
    """Synthesizer: aggregate all results into final answer."""
    # Aggregate results from all agents
    aggregated_context = []

    if state.get("retrieved_chunks"):
        chunks_content = []
        for chunk in state["retrieved_chunks"][:5]:  # Limit to 5 chunks
            file_path = chunk.get("file_path", "unknown")
            content = chunk.get("content", "")[:500]  # Limit content length
            # Escape curly braces in code to prevent LangChain template parsing
            escaped_content = content.replace("{", "{{").replace("}", "}}")
            chunks_content.append(f"【{file_path}】\n{escaped_content}")

        if chunks_content:
            aggregated_context.append(
                "Retrieved Code Snippets:\n" + "\n\n".join(chunks_content)
            )

    if state.get("analysis_results"):
        aggregated_context.append(
            f"分析结果: {state['analysis_results'][0].get('analysis', '')[:300]}"
        )

    if state.get("code_outputs"):
        aggregated_context.append(
            f"生成代码: {state['code_outputs'][0].get('generated_code', '')[:300]}"
        )

    if state.get("search_results"):
        aggregated_context.append(f"外部搜索结果: {state['search_results'][0]}")

    context_str = "\n".join(aggregated_context) if aggregated_context else "无特定结果"

    prompt = ChatPromptTemplate.from_messages([
        ("system", SYNTHESIZER_SYSTEM_PROMPT),
        ("human", f"""User Question: {state['user_query']}

Available Information:
{context_str}

Please generate the final answer."""),
    ])

    synthesizer = prompt | llm | StrOutputParser()
    final_answer = synthesizer.invoke({})

    return {
        "final_answer": final_answer,
        "iteration_count": state.get("iteration_count", 0) + 1,
        "timestamps": timestamp_node_entry(state, "synthesizer")["timestamps"],
    }


def human_approval_node(state: AgentState) -> dict:
    """Wait for human approval before executing generated code.

    This node interrupts the workflow and waits for external confirmation.
    In LangGraph, this is typically handled via graph.invoke with
    interrupt_on="human_approval" or via checkpointer.
    """
    return {
        "requires_human_approval": True,
        "human_approval_given": state.get("human_approval_given", False),
    }

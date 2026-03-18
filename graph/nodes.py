"""Node functions for LangGraph orchestration."""

from typing import Any
from datetime import datetime
from pydantic import BaseModel, Field
from langchain_core.language_models import BaseLanguageModel
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.retrievers import BaseRetriever
from graph.state import AgentState
from tools import get_code_tools, get_git_tools


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

    # Classify intent
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """对用户查询进行意图分类。返回一个 JSON 对象，包含：
- intent: code_lookup(代码位置查询), explanation(解释说明), bug_analysis(问题分析), general_qa(通用问答)
- confidence: 0-1置信度
- reasoning: 简短理由

只返回 JSON，不要其他文本。""",
        ),
        ("human", "{query}"),
    ])

    structured_llm = llm.with_structured_output(IntentClassification)
    chain = prompt | structured_llm

    classification = chain.invoke({"query": state["user_query"]})

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
    context = "\n\n".join([
        f"【{chunk['file_path']}】\n{chunk['content'][:500]}"
        for chunk in state["retrieved_chunks"][:3]
    ])

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """你是一个代码分析专家。基于以下代码片段，提供深入的分析和解释。
分析应包括：
1. 代码的主要功能
2. 关键设计模式
3. 可能的改进点
4. 与其他模块的关系""",
        ),
        ("human", f"""用户问题：{state['user_query']}

代码上下文：
{context}

请提供详细分析。"""),
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
    # Plan code generation
    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """你是一个代码生成专家。根据用户需求和代码库上下文，生成或建议代码。
生成的代码必须：
1. 遵循现有代码风格
2. 使用现有的工具和库
3. 包含必要的错误处理
4. 有清晰的注释""",
        ),
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
        aggregated_context.append(
            f"检索到的代码片段({len(state['retrieved_chunks'])}个)"
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
        (
            "system",
            """你是一个代码库问答助手。根据以下信息综合生成最终答案。
答案应该：
1. 准确回答用户问题
2. 引用相关代码片段
3. 提供清晰的解释
4. 突出重点信息""",
        ),
        ("human", f"""用户问题: {state['user_query']}

可用信息:
{context_str}

请生成最终答案。"""),
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

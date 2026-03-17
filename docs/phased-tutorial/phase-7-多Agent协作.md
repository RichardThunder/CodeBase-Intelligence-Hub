# Phase 7：多 Agent 协作

本阶段目标：在 Phase 6 的图上扩展为 **Orchestrator + 多个专家 Agent**（至少 Retrieval、Analysis），实现意图路由、多节点协作与结果聚合。

---

## 1. 设计指导

### 1.1 多 Agent 模式

- **Orchestrator（编排者）**：唯一入口，负责「意图分类 + 任务分解 + 路由」。不直接做检索或写代码，只决定「下一步调用哪个 Agent」。
- **专家 Agent**：每个负责一类能力（检索、分析、代码生成、搜索等），有独立工具集或逻辑，通过 State 与 Orchestrator 通信。
- **状态汇聚**：各专家把结果写进 State 的对应列表（如 `retrieved_chunks`、`analysis_results`），用 `Annotated[List, operator.add]` 累积；最后由 **Synthesizer** 统一生成面向用户的答案。

### 1.2 路由策略

- Orchestrator 输出：`intent`（或 `next_agent`）、可选 `subtasks`。
- 条件边：`intent → retrieval_agent | analysis_agent | synthesizer | END`。
- 每个专家执行完后**回到 Orchestrator**（或直接到 Synthesizer），由 Orchestrator 决定「是否再派发」或「收尾」。本阶段可简化为：Orchestrator → 单次派发到一个专家 → 该专家写 State → 再到 Synthesizer → END。

### 1.3 设计原则

- Orchestrator 的**意图枚举**与路由表要清晰，便于后续加 Code/Search Agent。
- 专家节点**只读** `user_query` 和已有 State，**只写** 自己负责的字段，避免互相覆盖。
- Synthesizer 只做「读全量 State → 生成 final_answer」，不做工具调用。

---

## 2. 需要实现的功能

- [ ] 扩展 `AgentState`：增加 `analysis_results`（列表）、可选 `subtasks`。
- [ ] 实现 **analysis_node**：输入为 `user_query` + `retrieved_chunks`，调用 LLM 做「代码逻辑解释 / 简单推理」，结果 append 到 `analysis_results`。
- [ ] 扩展 **orchestrator_node**：意图分类输出 `next_agent`（retrieval | analysis | synthesize），并写回 State。
- [ ] 条件边：Orchestrator 根据 `next_agent` 路由到 `retrieval_agent`、`analysis_agent` 或 `synthesizer`。
- [ ] 边：`retrieval_agent` → `orchestrator`（或直接 `retrieval_agent` → `synthesizer`）；`analysis_agent` → `orchestrator` 或 `synthesizer`；`synthesizer` → END。
- [ ] 实现 **synthesizer_node**：汇总 `retrieved_chunks`、`analysis_results` 与 `user_query`，生成 `final_answer`。
- [ ] 对「需要检索+分析」的 query（如「这段代码是干什么的？有没有安全隐患？」）跑通全图。

---

## 3. 示例代码

### 3.1 扩展 State

```python
# graph/state.py
from typing import TypedDict, Annotated, List
import operator

class AgentState(TypedDict):
    user_query: str
    intent: str
    next_agent: str  # retrieval | analysis | synthesize | end
    retrieved_chunks: Annotated[List[dict], operator.add]
    analysis_results: Annotated[List[dict], operator.add]
    final_answer: str
    error_message: str | None
```

### 3.2 意图分类（带 next_agent）

```python
# graph/nodes.py（续）
class OrchestratorOutput(BaseModel):
    intent: str
    next_agent: str  # retrieval | analysis | synthesize | end
    reason: str

def orchestrator_node(state: dict) -> dict:
    llm = get_llm().with_structured_output(OrchestratorOutput)
    prompt = ChatPromptTemplate.from_messages([
        ("system", """根据用户问题决定下一步：
- 需要查代码/定义/位置 → next_agent=retrieval
- 需要解释/分析/推理（且已有检索结果时可分析）→ next_agent=analysis
- 可直接总结或无需再查 → next_agent=synthesize
只返回 next_agent 和简短 reason。"""),
        ("human", "{query}"),
    ])
    result = (prompt | llm).invoke({"query": state["user_query"]})
    return {"intent": result.intent, "next_agent": result.next_agent}
```

### 3.3 Retrieval 与 Analysis 节点

```python
def retrieval_node(state: dict, retriever) -> dict:
    docs = retriever.invoke(state["user_query"])
    chunks = [{"content": d.page_content, "source": d.metadata.get("file_path", "")} for d in docs]
    return {"retrieved_chunks": chunks}

def analysis_node(state: dict) -> dict:
    """基于已检索内容做解释/分析，结果写入 analysis_results。"""
    chunks = state.get("retrieved_chunks", [])
    context = "\n\n".join([c.get("content", "") for c in chunks])
    llm = get_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是代码分析专家。根据以下代码片段，对用户问题给出简洁分析（逻辑、用途、潜在问题等）。"),
        ("human", "上下文：\n{context}\n\n用户问题：{question}"),
    ])
    out = (prompt | llm).invoke({"context": context, "question": state["user_query"]})
    return {"analysis_results": [{"content": out.content}]}
```

### 3.4 Synthesizer

```python
def synthesizer_node(state: dict) -> dict:
    chunks = state.get("retrieved_chunks", [])
    analyses = state.get("analysis_results", [])
    context_str = "\n\n".join([f"[{c.get('source')}]\n{c.get('content')}" for c in chunks])
    analysis_str = "\n\n".join([a.get("content", "") for a in analyses])
    llm = get_llm()
    prompt = ChatPromptTemplate.from_messages([
        ("system", "根据「检索到的代码」和「分析结果」汇总回答用户问题。若没有相关内容则说明。\n检索内容：\n{context}\n\n分析：\n{analysis}"),
        ("human", "{question}"),
    ])
    answer = (prompt | llm).invoke({
        "context": context_str or "（无）",
        "analysis": analysis_str or "（无）",
        "question": state["user_query"],
    })
    return {"final_answer": answer.content}
```

### 3.5 图构建（多 Agent 路由）

```python
# graph/builder.py
from langgraph.graph import StateGraph, END

def route_orchestrator(state: dict) -> str:
    return state.get("next_agent", "synthesize")

def build_graph(retriever):
    workflow = StateGraph(AgentState)

    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("retrieval_agent", lambda s: retrieval_node(s, retriever))
    workflow.add_node("analysis_agent", analysis_node)
    workflow.add_node("synthesizer", synthesizer_node)

    workflow.set_entry_point("orchestrator")
    workflow.add_conditional_edges(
        "orchestrator",
        route_orchestrator,
        {
            "retrieval": "retrieval_agent",
            "analysis": "analysis_agent",
            "synthesize": "synthesizer",
            "end": END,
        },
    )
    workflow.add_edge("retrieval_agent", "orchestrator")  # 检索完再回编排决定是否分析
    workflow.add_edge("analysis_agent", "synthesizer")    # 分析完直接汇总
    workflow.add_edge("synthesizer", END)

    return workflow.compile()
```

注意：上面是「检索 → 再回 Orchestrator」的写法；若希望「检索后直接分析再合成」，可改为 `retrieval_agent → analysis_agent → synthesizer`，由 Orchestrator 在第一次就输出「先 retrieval 再 analysis」的规划（例如通过 subtasks）。这里给出一种简单形态，你可按需调整边。

---

## 4. 需要导入的包和环境

与 Phase 6 相同；确保 `graph/state.py` 与各节点、builder 使用同一 State 定义。

---

## 5. 本阶段小结

- **Orchestrator** 负责意图与路由，**专家节点** 负责执行并写 State，**Synthesizer** 负责汇总生成答案。
- **条件边** 根据 State 中 `next_agent` 决定下一节点；**普通边** 固定流转（如 retrieval → orchestrator，synthesizer → END）。
- 多 Agent 协作 = 一张图 + 多节点 + 清晰的状态读写分工。

下一步：[Phase 8：记忆、流式与 API](./phase-8-记忆流式与API.md)——Memory、流式输出、FastAPI/LangServe。

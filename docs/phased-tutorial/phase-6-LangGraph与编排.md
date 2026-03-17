# Phase 6：LangGraph 与编排

本阶段目标：理解 LangGraph 的 **StateGraph**、**节点**、**边**（普通边与条件边），能实现一个「意图分类 → 单一路由」的小图，为 Phase 7 多 Agent 协作打基础。

---

## 1. 设计指导

### 1.1 为什么用图而不是手写循环

- **显式状态**：图有一个统一的 **State**（TypedDict），每个节点读/写 State 的若干字段，数据流清晰。
- **条件路由**：可以根据 State 中某字段（如 intent）决定下一步走哪个节点，无需在代码里写一堆 if/else。
- **可观测与断点**：LangSmith 等能按「节点」展示 Trace；配合 checkpointer 还可做 Human-in-the-Loop 暂停。

### 1.2 核心概念

| 概念 | 说明 |
|------|------|
| **State** | TypedDict，所有节点输入/输出都是「对 State 的更新」；LangGraph 会用 reducer（如 `operator.add`）合并列表类字段。 |
| **节点** | 函数 `(state) -> partial_state`，返回要更新的键值对。 |
| **边** | `add_edge("A", "B")` 表示 A 执行完一定到 B；`add_conditional_edges("A", fn, map)` 表示 A 执行完后根据 `fn(state)` 的返回值在 map 里选下一节点。 |
| **入口** | `set_entry_point("orchestrator")` 表示图从该节点开始。 |
| **END** | 从某节点连到 `END` 表示图结束。 |

### 1.3 设计原则

- State 设计要**一次想好主字段**，避免后面频繁改 TypedDict（可先简单，再扩展）。
- 条件边函数**只依赖 State**，保持纯函数，便于测试。
- 本阶段图尽量小：**orchestrator（意图分类）→ retrieval 节点 → synthesizer → END**，先不引入多 Agent 分支。

---

## 2. 需要实现的功能

- [ ] 定义 `AgentState` TypedDict，至少包含：`user_query`、`intent`、`retrieved_chunks`、`final_answer`。
- [ ] 实现 `orchestrator_node(state)`：调用 LLM 做意图分类（如 simple_lookup / code_explanation），把结果写回 `state["intent"]`。
- [ ] 实现 `retrieval_node(state)`：根据 `user_query` 调用 Retriever，把结果写回 `state["retrieved_chunks"]`。
- [ ] 实现 `synthesizer_node(state)`：根据 `retrieved_chunks` 和 `user_query` 调用 LLM 生成 `final_answer`。
- [ ] 用 `StateGraph` 建图：入口 orchestrator → 条件边（本阶段可简化为总是去 retrieval）→ retrieval → synthesizer → END。
- [ ] 对一条 query 跑通 `graph.invoke({"user_query": "..."})`，并打印 `final_answer`。

---

## 3. 示例代码

### 3.1 State 定义

```python
# graph/state.py
from typing import TypedDict, Annotated, List
import operator

class AgentState(TypedDict):
    user_query: str
    intent: str
    retrieved_chunks: Annotated[List[dict], operator.add]  # 列表累积
    final_answer: str
    error_message: str | None
```

### 3.2 节点实现

```python
# graph/nodes.py
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel

# 意图分类输出结构
class IntentOutput(BaseModel):
    intent: str  # simple_lookup | code_explanation | other
    reason: str

def get_llm():
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)

def orchestrator_node(state: dict) -> dict:
    """根据 user_query 做意图分类，写入 intent。"""
    llm = get_llm().with_structured_output(IntentOutput)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "对用户问题做意图分类。只返回：simple_lookup（查定义/位置）、code_explanation（解释逻辑/原因）、other。"),
        ("human", "{query}"),
    ])
    result = (prompt | llm).invoke({"query": state["user_query"]})
    return {"intent": result.intent}

def make_retrieval_node(retriever):
    """返回依赖 retriever 的 retrieval 节点（闭包注入）。"""
    def retrieval_node(state: dict) -> dict:
        docs = retriever.invoke(state["user_query"])
        chunks = [{"content": d.page_content, "source": d.metadata.get("file_path", "")} for d in docs]
        return {"retrieved_chunks": chunks}
    return retrieval_node

def synthesizer_node(state: dict) -> dict:
    """根据检索结果生成最终回答。"""
    llm = get_llm()
    context = "\n\n".join([f"[{c.get('source','')}]\n{c['content']}" for c in state.get("retrieved_chunks", [])])
    prompt = ChatPromptTemplate.from_messages([
        ("system", "根据以下上下文回答用户问题。若无关则说明。\n上下文：\n{context}"),
        ("human", "{question}"),
    ])
    answer = (prompt | llm).invoke({"context": context, "question": state["user_query"]})
    return {"final_answer": answer.content}
```

### 3.3 条件路由与图构建

```python
# graph/builder.py
from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes import orchestrator_node, make_retrieval_node, synthesizer_node

def route_after_orchestrator(state: dict) -> str:
    """Orchestrator 之后：本阶段一律走 retrieval，后续可扩展。"""
    return "retrieval"

def build_graph(retriever):
    workflow = StateGraph(AgentState)

    workflow.add_node("orchestrator", orchestrator_node)
    workflow.add_node("retrieval", make_retrieval_node(retriever))
    workflow.add_node("synthesizer", synthesizer_node)

    workflow.set_entry_point("orchestrator")
    workflow.add_conditional_edges("orchestrator", route_after_orchestrator, {"retrieval": "retrieval"})
    workflow.add_edge("retrieval", "synthesizer")
    workflow.add_edge("synthesizer", END)

    return workflow.compile()
```

### 3.4 调用

```python
# 使用
from retrieval.ingestion import ingest_directory
from retrieval.vectorstore import build_vectorstore, get_retriever
from graph.builder import build_graph

docs = ingest_directory(".")
vs = build_vectorstore(docs)
retriever = get_retriever(vs, k=5)
graph = build_graph(retriever)

result = graph.invoke({"user_query": "主入口在哪里？"})
print(result["final_answer"])
```

### 3.5 流式（按节点）

```python
# 流式会按节点产出 state 更新
for event in graph.stream({"user_query": "主入口在哪？"}):
    print(event)  # 每个 key 是节点名，value 是该节点返回的 partial state
```

---

## 4. 需要导入的包和环境

### 4.1 本阶段依赖

```toml
langgraph>=0.2.0
langchain-openai>=1.1.11
langchain-core>=1.2.19
pydantic>=2.0
```

```bash
uv add langgraph langchain-openai langchain-core pydantic
```

### 4.2 环境

- 已有 Retriever（Phase 3）；`graph/builder.py` 中通过参数传入。
- `OPENAI_API_KEY` 可用。

---

## 5. 本阶段小结

- **StateGraph**：用 TypedDict 定义 State，节点返回「部分 State 更新」，图负责合并。
- **条件边**：`add_conditional_edges("orchestrator", route_fn, {"retrieval": "retrieval", "end": END})`，根据 State 决定下一节点。
- **节点**：纯函数 `(state) -> dict`，可注入 retriever 等依赖（通过闭包或参数）。
- 下一步会在同一张图上增加 **多个子 Agent 节点**（retrieval_agent、analysis_agent 等），由 orchestrator 路由到不同节点。

下一步：[Phase 7：多 Agent 协作](./phase-7-多Agent协作.md)——Orchestrator 路由到多个专家 Agent、结果聚合。

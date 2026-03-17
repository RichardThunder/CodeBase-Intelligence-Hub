# Phase 5：工具与单 Agent

本阶段目标：学会用 LangChain 定义工具（@tool、StructuredTool）、绑定到 LLM，并实现「单 Agent」的 ReAct 循环（推理 → 选工具 → 执行 → 再推理），为多 Agent 打基础。

---

## 1. 设计指导

### 1.1 工具（Tool）在 LangChain 中的角色

- **Tool**：可被 LLM 调用的函数，有名称、描述、参数 Schema（常用 Pydantic）。LLM 根据描述决定是否调用以及传什么参数。
- **bind_tools**：把 Tool 列表绑定到 ChatModel，模型输出中会包含 `tool_calls`；应用层解析 `tool_calls` 并执行对应函数，把结果再塞回消息列表，继续让模型生成，直到模型不再调工具、直接给出最终回答。

### 1.2 ReAct 与单 Agent

- **ReAct**：Reasoning + Acting。Agent 循环：  
  `用户消息 → LLM(含工具) → 若 tool_calls 则执行工具 → 工具结果作为新消息 → 再调 LLM → … → 最终文本`。
- **单 Agent**：只有一个「大脑」（一个 LLM + 一套工具），本阶段不引入 Orchestrator，只做「一个 Agent 调用多个工具」的循环。

### 1.3 设计原则

- 工具**描述要清晰**：说明「何时用、何时不用」，减少幻觉调用。
- **参数用 Pydantic**：便于校验和自动生成 schema，减少格式错误。
- 循环要有**终止条件**：例如最多 N 轮工具调用，或模型返回无 tool_calls 的 AIMessage。

---

## 2. 需要实现的功能

- [ ] 用 `@tool` 或 `StructuredTool` 定义 2～3 个工具（例如：`codebase_search` 用 Phase 3 的 Retriever、`symbol_lookup` 模拟或简单实现、`get_current_time` 做占位）。
- [ ] 用 `llm.bind_tools(tools)` 得到可调工具的 LLM，并写一个循环：处理 `tool_calls`、执行工具、把结果 append 到 messages，再调用 LLM，直到没有 tool_calls。
- [ ] 用自然语言问 2～3 个问题，观察 Agent 是否选对工具并返回合理结果。
- [ ] （可选）用 LangGraph 的 `create_react_agent` 或手写一个最小图（一个节点：invoke LLM，条件边：有 tool_calls → 工具节点 → 回到 LLM），体验「图」与「循环」的等价性。

---

## 3. 示例代码

### 3.1 定义工具

```python
# tools/code_tools.py
from langchain_core.tools import tool
from langchain_core.documents import Document

# 假设从外部注入 retriever，这里用简单函数示意
_retriever = None

def set_retriever(r):
    global _retriever
    _retriever = r

@tool
def codebase_search(query: str, top_k: int = 5) -> str:
    """在代码库中按语义搜索与 query 相关的代码片段。当用户问「某功能在哪」「哪里实现了某某」时使用。"""
    if _retriever is None:
        return "检索未初始化。"
    docs = _retriever.invoke(query)
    return "\n\n".join([f"[{d.metadata.get('file_path', '')}]\n{d.page_content}" for d in docs[:top_k]])

@tool
def symbol_lookup(symbol_name: str) -> str:
    """精确查找函数或类的定义位置。当用户明确给出符号名（如 UserService、login）时使用。"""
    if _retriever is None:
        return "检索未初始化。"
    docs = _retriever.invoke(symbol_name)
    return "\n\n".join([f"[{d.metadata.get('file_path', '')}]\n{d.page_content}" for d in docs[:3]])
```

### 3.2 使用 Pydantic 的 StructuredTool（可选）

```python
# tools/code_tools.py（续）
from pydantic import BaseModel, Field

class CodebaseSearchInput(BaseModel):
    query: str = Field(description="自然语言描述要查找的代码功能或概念")
    top_k: int = Field(default=5, description="返回结果数量")

# 可以这样定义同名工具，覆盖上面的 @tool
# codebase_search = StructuredTool.from_function(
#     func=lambda query, top_k=5: _search_impl(query, top_k),
#     name="codebase_search",
#     description="在代码库中按语义搜索...",
#     args_schema=CodebaseSearchInput,
# )
```

### 3.3 Agent 循环（手写 ReAct）

```python
# agents/single_agent.py
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from tools.code_tools import codebase_search, symbol_lookup, set_retriever

def run_agent_loop(user_query: str, retriever, max_turns: int = 5) -> str:
    set_retriever(retriever)
    tools = [codebase_search, symbol_lookup]
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools(tools)
    messages = [HumanMessage(content=user_query)]

    for _ in range(max_turns):
        response = llm.invoke(messages)
        if not response.tool_calls:
            return response.content
        for tc in response.tool_calls:
            tool_name = tc["name"]
            tool_args = tc.get("args", {})
            chosen = next((t for t in tools if t.name == tool_name), None)
            if not chosen:
                messages.append(ToolMessage(content=f"未知工具: {tool_name}", tool_call_id=tc["id"]))
                continue
            result = chosen.invoke(tool_args)
            messages.append(ToolMessage(content=str(result), tool_call_id=tc["id"]))
        messages.append(AIMessage(content=response.content or "", tool_calls=response.tool_calls))
    return "达到最大轮数，未得到最终回答。"
```

### 3.4 使用示例

```python
# 在 main 或脚本中
from retrieval.ingestion import ingest_directory
from retrieval.vectorstore import build_vectorstore, get_retriever
from agents.single_agent import run_agent_loop

docs = ingest_directory(".")
vs = build_vectorstore(docs)
retriever = get_retriever(vs, k=5)
answer = run_agent_loop("主入口在哪里？哪里调用了配置？", retriever)
print(answer)
```

### 3.5 用 LangGraph 的 create_react_agent（可选）

```python
# 需要：uv add langgraph
from langgraph.prebuilt import create_react_agent

llm = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools(tools)
agent = create_react_agent(llm, tools)
# 输入格式: {"messages": [HumanMessage(content="...")]}
result = agent.invoke({"messages": [HumanMessage(content="主入口在哪？")]})
# result["messages"][-1].content 为最终回答
```

---

## 4. 需要导入的包和环境

### 4.1 本阶段依赖

```toml
langchain-core>=0.3.0
langchain-openai>=0.2.0
pydantic>=2.0
```

若用 `create_react_agent`：

```bash
uv add langgraph
```

### 4.2 环境

- 已有 Retriever（Phase 3/4 的向量库与 retriever）。
- `OPENAI_API_KEY` 可用。

---

## 5. 本阶段小结

- **@tool**：函数加描述，LangChain 会生成 schema；复杂参数用 **StructuredTool + Pydantic**。
- **bind_tools**：LLM 输出可能包含 `tool_calls`；应用负责执行并追加 `ToolMessage`，再继续调用 LLM。
- **单 Agent 循环**：用户消息 → LLM → 若有 tool_calls 则执行并追加消息 → 再 LLM，直到无 tool_calls，最后一条 AIMessage 的 content 即为最终答案。
- **LangGraph create_react_agent**：等价于上述循环的图实现，为 Phase 6 的「自定义图」做铺垫。

下一步：[Phase 6：LangGraph 与编排](./phase-6-LangGraph与编排.md)——StateGraph、自定义节点与条件边。

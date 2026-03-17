# Phase 8：记忆、流式与 API

本阶段目标：为对话增加**记忆**（多轮上下文）、对图或链做**流式输出**、并通过 **FastAPI** 或 **LangServe** 暴露 HTTP API，形成可用的服务形态。

---

## 1. 设计指导

### 1.1 记忆（Memory）

- **问题**：多轮对话时，上一轮的问题与答案要作为上下文传给 LLM，否则无法理解「它」「这段代码」等指代。
- **常见做法**：
  - **短期**：保留最近 N 轮 HumanMessage/AIMessage，拼进当前 prompt。
  - **中期**：用 LLM 对历史做摘要，节省 token。
  - **长期**：把重要信息向量化存检索（本项目可选）。
- 本阶段先做**短期记忆**：在调用图/链前，从「会话存储」里取出最近几轮消息，与当前 query 一起作为 `user_query` 或作为 messages 列表传给模型。

### 1.2 流式输出

- **链**：`chain.stream(input)` 已支持 token 级流式。
- **图**：`graph.stream(input)` 按**节点**流式产出 state 更新；若要对**最终回答**做 token 流式，需在 Synthesizer 内用 LLM 的 `stream()` 并通过回调或生成器把 token 推到客户端。
- **API**：SSE（Server-Sent Events）或 WebSocket，每收到 token 就发 `data: {...}\n\n`。

### 1.3 API 层

- **FastAPI**：手写 `POST /chat`、`POST /chat/stream`，在路由里调用图或链。
- **LangServe**：`add_routes(app, chain, path="/rag")` 可自动得到 `/rag/invoke`、`/rag/stream` 等，适合快速暴露已有链；图需要包装成 Runnable 再挂上去。

---

## 2. 需要实现的功能

- [ ] 实现**简单对话记忆**：用内存 dict 按 `session_id` 存最近 5 条 `(human, ai)` 对，在调用链/图前拼成「历史 + 当前 question」的上下文（或 messages 列表）。
- [ ] 对 RAG 链或图的 Synthesizer 做 **token 流式**：在 API 中返回 SSE，每收到一个 token 就推送。
- [ ] 用 **FastAPI** 提供 `POST /chat`（同步）和 `POST /chat/stream`（SSE），请求体含 `query`、`session_id`（可选）。
- [ ] （可选）用 **LangServe** 的 `add_routes` 把 RAG 链挂到 `/rag`，体验自动生成的 invoke/stream 端点。

---

## 3. 示例代码

### 3.1 简单对话记忆

```python
# memory/simple.py
from collections import deque
from typing import Optional

# session_id -> 最近 N 条 (human, ai)
_store: dict[str, deque[tuple[str, str]]] = {}
MAX_HISTORY = 5

def get_history(session_id: str) -> list[tuple[str, str]]:
    return list(_store.get(session_id, deque()))

def add_turn(session_id: str, human: str, ai: str) -> None:
    if session_id not in _store:
        _store[session_id] = deque(maxlen=MAX_HISTORY)
    _store[session_id].append((human, ai))

def format_history_for_prompt(history: list[tuple[str, str]]) -> str:
    if not history:
        return ""
    lines = []
    for h, a in history:
        lines.append(f"用户: {h}\n助手: {a}")
    return "\n\n".join(lines)
```

### 3.2 带记忆的 RAG 调用

在调用 RAG 链时，把「历史 + 当前问题」合成一个增强的 question，或把历史放进 system prompt：

```python
# 方式一：把历史拼进 question（简单）
from memory.simple import get_history, format_history_for_prompt

def build_query_with_history(session_id: str, question: str) -> str:
    hist = get_history(session_id)
    if not hist:
        return question
    prefix = "历史对话：\n" + format_history_for_prompt(hist) + "\n\n当前问题："
    return prefix + question
```

### 3.3 FastAPI 同步 + 流式

```python
# api/main.py
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import os
from dotenv import load_dotenv
load_dotenv()

# 假设已有 graph 和 rag_chain
from retrieval.ingestion import ingest_directory
from retrieval.vectorstore import build_vectorstore, get_retriever
from graph.builder import build_graph
from memory.simple import get_history, add_turn, format_history_for_prompt

app = FastAPI()
# 启动时建图（实际可放 lifespan 或依赖注入）
_retriever = None
_graph = None

@app.on_event("startup")
def startup():
    global _retriever, _graph
    docs = ingest_directory(".")
    vs = build_vectorstore(docs)
    _retriever = get_retriever(vs, k=5)
    _graph = build_graph(_retriever)

class ChatRequest(BaseModel):
    query: str
    session_id: str = "default"

class ChatResponse(BaseModel):
    answer: str
    session_id: str

@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    # 可选：把历史拼进上下文，这里简化直接用 query
    result = _graph.invoke({"user_query": req.query})
    answer = result.get("final_answer", "")
    add_turn(req.session_id, req.query, answer)
    return ChatResponse(answer=answer, session_id=req.session_id)
```

### 3.4 流式端点（SSE）

若要在 Synthesizer 里做 token 流式，需要 Synthesizer 节点支持「流式生成」并把 token 通过队列或回调传出；这里用「图跑完后对最终答案做逐字模拟流式」示意结构，实际可改为在 Synthesizer 内用 `llm.stream()` 写到一个 asyncio.Queue，由 API 从队列读并推 SSE：

```python
@app.post("/chat/stream")
async def chat_stream(req: ChatRequest):
    async def generate():
        result = await _graph.ainvoke({"user_query": req.query})
        answer = result.get("final_answer", "")
        add_turn(req.session_id, req.query, answer)
        # 简单按字符流式（实际可用 LLM.stream 在节点内流式）
        for ch in answer:
            yield f"data: {json.dumps({'token': ch})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache"},
    )
```

### 3.5 LangServe 挂载链（可选）

```python
# 需要：uv add langserve
from langserve import add_routes
from chains.rag import build_rag_chain

# 用已有 retriever 建链
rag_chain = build_rag_chain(_retriever)
add_routes(app, rag_chain, path="/rag")
# 自动得到：POST /rag/invoke, POST /rag/stream 等
```

---

## 4. 需要导入的包和环境

### 4.1 本阶段依赖

```toml
fastapi>=0.115.0
uvicorn>=0.30.0
```

若用 LangServe：

```toml
langserve>=0.2.0
```

```bash
uv add fastapi uvicorn langserve
```

### 4.2 环境

- 同前；启动方式：`uvicorn api.main:app --reload --port 8000`。

---

## 5. 本阶段小结

- **记忆**：按 session 存最近 N 轮对话，在调用前拼进 prompt 或 messages，即可支持多轮指代。
- **流式**：链用 `stream()`；图可对最终答案或 Synthesizer 内 LLM 做 token 流式，通过 SSE 推给前端。
- **API**：FastAPI 手写 /chat、/chat/stream；LangServe 可快速把链暴露为 invoke/stream 端点。

至此，你已经完成从「最小链」到「多 Agent 图 + 记忆 + 流式 API」的完整路径；可再结合系统功能文档做检索增强（混合检索、Rerank）、Code Agent、Human-in-the-Loop 等扩展。

---

**全系列阶段索引**：[00-总览与阶段索引](./00-总览与阶段索引.md)

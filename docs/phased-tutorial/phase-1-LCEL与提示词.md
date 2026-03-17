# Phase 1：LCEL 与提示词

本阶段目标：掌握 LCEL（LangChain Expression Language）的链式组合、多输入并行、以及结构化输出，为后续 RAG 和 Agent 打基础。

---

## 1. 设计指导

### 1.1 什么是 LCEL

- LCEL 用 `|` 把 **Runnable** 串成链，每个组件都是 `Runnable[Input, Output]`。
- 好处：自动支持 `invoke`、`stream`、`batch`，以及与 LangSmith 的集成。
- 旧版 `LLMChain` 已废弃，新代码一律用 LCEL 构建链。

### 1.2 常用 Runnable 组件

| 组件 | 作用 | 典型用法 |
|------|------|----------|
| `ChatPromptTemplate` | 把变量填进模板，输出 `PromptValue` | 系统提示 + 用户输入 |
| `RunnablePassthrough` | 把输入原样或部分传递下去 | 与 `RunnableParallel` 配合 |
| `RunnableParallel` | 多路分支，输出 dict | 同时准备 context 与 question |
| `RunnableLambda` | 任意 Python 函数封装成 Runnable | 格式化、过滤 |
| `StrOutputParser` / `JsonOutputParser` | 把模型输出解析成 str 或 dict | 链的最后一环 |

### 1.3 设计原则

- **链的输入/输出要明确**：例如 RAG 链输入 `{"question": str}`，输出 `str` 或 `{"answer": str, "sources": list}`。
- **复杂逻辑用 RunnableParallel 拆开**：例如「同时取检索结果和记忆」，再合并进 prompt。

---

## 2. 需要实现的功能

- [ ] 用 LCEL 写一条「多变量」提示链（例如带 `context` 和 `question`），并 `invoke`。
- [ ] 使用 `RunnableParallel` 同时准备多个输入（如模拟的 context + question），再送入同一 prompt。
- [ ] 使用 `with_structured_output(Pydantic 模型)` 让 LLM 返回 JSON，并解析成对象。
- [ ] 对同一链调用 `stream()`，观察 token 流式输出。

---

## 3. 示例代码

### 3.1 多变量提示链（为 RAG 做准备）

```python
# chains/simple_rag_style.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain_openai import ChatOpenAI

def build_simple_rag_chain(llm):
    prompt = ChatPromptTemplate.from_messages([
        ("system", """你根据以下上下文回答用户问题。如果上下文中没有相关信息，请说明。
上下文：
{context}
"""),
        ("human", "{question}"),
    ])
    return (
        RunnablePassthrough.assign(
            context=lambda x: x.get("context", "（无）"),
        )
        | prompt
        | llm
        | StrOutputParser()
    )

# 使用示例
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    chain = build_simple_rag_chain(llm)
    out = chain.invoke({
        "context": "本项目使用 LangChain 和 LangGraph 构建代码库问答。",
        "question": "这个项目用了什么技术？",
    })
    print(out)
```

### 3.2 RunnableParallel：多路输入

```python
# 同时传入 context、question、extra（模拟多路准备）
from langchain_core.runnables import RunnableParallel, RunnablePassthrough

def build_parallel_chain(llm):
    prompt = ChatPromptTemplate.from_messages([
        ("system", "上下文：{context}\n额外信息：{extra}"),
        ("human", "{question}"),
    ])
    # 输入为 {"question": "...", "context": "...", "extra": "..."}
    # 这里用 Parallel 只是为了演示结构，实际可来自不同来源
    setup = RunnableParallel(
        context=RunnablePassthrough.assign(
            context=lambda x: x.get("context", ""),
        ) | (lambda x: x["context"]),
        question=RunnablePassthrough.pick("question"),
        extra=lambda x: x.get("extra", "无"),
    )
    # 合并成 prompt 需要的 keys
    def merge(inputs):
        return {
            "context": inputs["context"] if isinstance(inputs["context"], str) else inputs.get("context", ""),
            "question": inputs["question"],
            "extra": inputs.get("extra", "无"),
        }
    return setup | merge | prompt | llm | StrOutputParser()
```

更常见的用法是「检索器 + 格式化」与 question 并行（Phase 4 会做）：

```python
# 典型 RAG 骨架（Phase 4 会实现 retriever）
# RunnableParallel({
#     "context": retriever | format_docs,
#     "question": RunnablePassthrough.pick("question"),
# })
```

### 3.3 结构化输出（Pydantic）

```python
# chains/structured_chain.py
from pydantic import BaseModel, Field
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

class IntentResult(BaseModel):
    """意图分类结果"""
    intent: str = Field(description="如：code_lookup, explanation, bug_analysis")
    confidence: float = Field(ge=0, le=1, description="置信度 0-1")
    reason: str = Field(description="简短理由")

def build_intent_chain(llm):
    prompt = ChatPromptTemplate.from_messages([
        ("system", "对用户问题做意图分类，返回 JSON。"),
        ("human", "{query}"),
    ])
    structured_llm = llm.with_structured_output(IntentResult)
    return prompt | structured_llm

# 使用
if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    load_dotenv()
    llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    chain = build_intent_chain(llm)
    result: IntentResult = chain.invoke({"query": "UserService 的 login 方法在哪定义的？"})
    print(result.intent, result.confidence, result.reason)
```

### 3.4 流式输出

```python
# 同一链直接 .stream()
chain = prompt | llm | StrOutputParser()
for chunk in chain.stream({"question": "用三句话介绍 LangChain"}):
    print(chunk, end="", flush=True)
print()
```

---

## 4. 需要导入的包和环境

### 4.1 本阶段依赖

与 Phase 0 相同，无需新增包。若未装 Pydantic 2：

```bash
uv add pydantic
# 或 pip install pydantic
```

### 4.2 环境

与 Phase 0 一致：`.env` 中有 `OPENAI_API_KEY`，Python 3.11+。

---

## 5. 本阶段小结

- **LCEL**：用 `|` 组合 Runnable，输入输出类型清晰，支持 invoke/stream/batch。
- **RunnableParallel**：多路准备输入，再合并进 prompt，为 RAG「检索 + question」并行打基础。
- **with_structured_output(Pydantic)**：保证模型输出可解析为结构化对象，便于意图分类、工具参数等。
- **stream()**：同一链即可流式输出，无需改结构。

下一步：[Phase 2：文档加载与分块](./phase-2-文档加载与分块.md)——DocumentLoader、TextSplitter、为代码库摄入做准备。

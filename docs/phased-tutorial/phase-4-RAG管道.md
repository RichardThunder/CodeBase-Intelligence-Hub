# Phase 4：RAG 管道

本阶段目标：把「检索 + 提示 + 生成」串成完整 RAG 链，掌握上下文格式化、链的组装，并可选接触 RAGAS 做质量评估。

---

## 1. 设计指导

### 1.1 RAG 数据流

```
用户问题 → Retriever → 若干 Document
                    → 格式化为一段 context 字符串
                    → Prompt(context=..., question=...) → LLM → 答案
```

- **检索**：Phase 3 的 Retriever，`invoke(question)` 得到 `List[Document]`。
- **格式化**：把 Document 列表转成「带来源的」字符串，便于 LLM 引用且便于你溯源（file_path、行号等）。
- **生成**：用 LCEL 组合 `RunnableParallel({"context": retriever | format, "question": passthrough}) | prompt | llm | parser`。

### 1.2 设计原则

- **context 长度可控**：对 Document 内容做截断或限制条数，避免超出模型 context window。
- **答案可溯源**：在 prompt 中要求「引用时注明来源」，并在 metadata 中保留 file_path。

### 1.3 与系统功能文档的对应

- 系统文档中的「三阶段检索」（多路召回、元数据过滤、Rerank）可在后续迭代中加；本阶段先做**单路向量检索 + 格式化 + 生成**，把主链路跑通。

---

## 2. 需要实现的功能

- [ ] 实现 `format_docs(docs: List[Document]) -> str`，每条带 `source` 或 `file_path`。
- [ ] 用 LCEL 组装 RAG 链：`RunnableParallel(context=retriever | format_docs, question=RunnablePassthrough.pick("question")) | prompt | llm | StrOutputParser`。
- [ ] 对 3～5 个问题做端到端调用，检查答案是否用到检索到的内容。
- [ ] （可选）跑 RAGAS 的 faithfulness / answer_relevancy（需准备少量 question + ground_truth）。

---

## 3. 示例代码

### 3.1 上下文格式化

```python
# chains/rag_utils.py
from langchain_core.documents import Document

def format_docs(docs: list[Document]) -> str:
    """把 Document 列表格式化为 RAG 的 context 字符串"""
    parts = []
    for i, doc in enumerate(docs):
        path = doc.metadata.get("file_path", doc.metadata.get("source", "unknown"))
        parts.append(f"[{i+1}] 来源: {path}\n{doc.page_content}")
    return "\n\n---\n\n".join(parts)
```

### 3.2 RAG 链

```python
# chains/rag.py
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_openai import ChatOpenAI
from .rag_utils import format_docs

SYSTEM_RAG = """你是一个代码库助手。请仅根据下面「上下文」中的内容回答用户问题。
如果上下文中没有相关信息，请明确说「在提供的上下文中未找到相关信息」。
回答时请注明引用自哪个来源（如 [1] 来源: path/to/file.py）。
上下文：
{context}
"""

def build_rag_chain(retriever, llm=None):
    if llm is None:
        import os
        from dotenv import load_dotenv
        load_dotenv()
        llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_RAG),
        ("human", "{question}"),
    ])
    return (
        RunnableParallel({
            "context": retriever | format_docs,
            "question": RunnablePassthrough.pick("question"),
        })
        | prompt
        | llm
        | StrOutputParser()
    )
```

### 3.3 使用示例

```python
# 在脚本或 main 中
from retrieval.vectorstore import build_vectorstore, get_retriever
from retrieval.ingestion import ingest_directory
from chains.rag import build_rag_chain

docs = ingest_directory(".")
vs = build_vectorstore(docs)
retriever = get_retriever(vs, k=5)
rag = build_rag_chain(retriever)

answer = rag.invoke({"question": "本项目的主入口在哪里？"})
print(answer)
```

### 3.4 流式 RAG

```python
# 同一链支持 stream
for chunk in rag.stream({"question": "什么是 RAG？"}):
    print(chunk, end="", flush=True)
```

### 3.5 RAGAS 初体验（可选）

```bash
uv add ragas
```

```python
# evaluation/ragas_simple.py
from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from langchain_openai import ChatOpenAI
from langchain_openai import OpenAIEmbeddings

# 需要准备 dataset: list of {"question", "answer", "contexts", "ground_truth"}
dataset = [
    {
        "question": "主入口在哪里？",
        "answer": "...",      # 模型生成的答案
        "contexts": ["..."],  # 检索到的 context 列表
        "ground_truth": "主入口在 main.py",
    },
]
result = evaluate(
    dataset=dataset,
    metrics=[faithfulness, answer_relevancy],
    llm=ChatOpenAI(model="gpt-4o-mini"),
    embeddings=OpenAIEmbeddings(model="text-embedding-3-small"),
)
print(result)
```

---

## 4. 需要导入的包和环境

### 4.1 本阶段依赖

与 Phase 1 + Phase 3 一致；若用 RAGAS 则增加：

```bash
uv add ragas
```

### 4.2 环境

- 已有向量库（Phase 3 产出）或现场 `ingest_directory` + `build_vectorstore`。
- `OPENAI_API_KEY` 可用。

---

## 5. 本阶段小结

- **RAG 链**：`RunnableParallel(context=retriever | format_docs, question=...) | prompt | llm | parser`。
- **format_docs**：统一把 Document 列表变成带来源的 context 字符串，便于引用与溯源。
- **RAGAS**：可对已有 question/answer/contexts/ground_truth 做 faithfulness、answer_relevancy 等评估，为后续优化检索/分块提供依据。

下一步：[Phase 5：工具与单 Agent](./phase-5-工具与单Agent.md)——@tool、bind_tools、ReAct 单 Agent。

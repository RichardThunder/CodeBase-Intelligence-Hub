# Phase 3：向量存储与检索

本阶段目标：把 Phase 2 的 Document 列表写入向量库，学会 Embeddings、VectorStore、Retriever 的用法，并能用自然语言查询得到相关 chunk。

---

## 1. 设计指导

### 1.1 概念关系

- **Embeddings**：文本 → 向量。LangChain 用 `Embeddings` 接口封装（如 `OpenAIEmbeddings`）。
- **VectorStore**：存 (vector, metadata, optional id)，支持相似度搜索。本项目用 **Chroma** 做本地开发（无需额外服务），生产可用 Qdrant。
- **Retriever**：抽象「查询 → 返回相关 Document 列表」。`VectorStore.as_retriever()` 即得到 Retriever。

### 1.2 检索流程

1. 摄入：Document 列表 → Embeddings 得到向量 → 写入 VectorStore。
2. 查询：用户问题 → Embeddings 得到 query 向量 → VectorStore 相似度搜索 → 返回 top-k Document。

### 1.3 设计原则

- **存储与检索解耦**：摄入脚本只负责建库；应用侧只依赖 `Retriever` 接口，便于以后换成 EnsembleRetriever、Rerank 等。
- **元数据一起存**：Chroma 支持 metadata，便于后续按 language、file_path 过滤。

---

## 2. 需要实现的功能

- [ ] 使用 `OpenAIEmbeddings`（或兼容接口）将一段文本转为向量，并打印维度。
- [ ] 使用 Chroma 创建集合，把 Phase 2 产出的 Document 列表 `add_documents` 写入。
- [ ] 用 `vectorstore.as_retriever(search_kwargs={"k": 5})` 做查询，对 2～3 个自然语言问题打印返回的 chunk 内容与 metadata。
- [ ] （可选）实现「按 metadata 过滤」的检索（如只查 `language=="python"`）。

---

## 3. 示例代码

### 3.1 Embeddings 与向量维度

```python
# retrieval/embeddings.py
import os
from langchain_openai import OpenAIEmbeddings

def get_embeddings():
    return OpenAIEmbeddings(
        model="text-embedding-3-small",  # 或 text-embedding-3-large
        api_key=os.getenv("OPENAI_API_KEY"),
    )

if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()
    emb = get_embeddings()
    vec = emb.embed_query("什么是 RAG？")
    print("维度:", len(vec))
```

### 3.2 写入 Chroma 与检索

```python
# retrieval/vectorstore.py
import os
from langchain_chroma import Chroma
from langchain_openai import OpenAIEmbeddings
from langchain_core.documents import Document

def get_embeddings():
    return OpenAIEmbeddings(
        model="text-embedding-3-small",
        api_key=os.getenv("OPENAI_API_KEY"),
    )

def build_vectorstore(documents: list[Document], persist_directory: str = "./chroma_db"):
    """将 Document 列表写入 Chroma 并返回 VectorStore"""
    embeddings = get_embeddings()
    return Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=persist_directory,
    )

def get_retriever(vectorstore, k: int = 5):
    return vectorstore.as_retriever(search_type="similarity", search_kwargs={"k": k})
```

### 3.3 端到端：摄入 + 建库 + 查询

```python
# scripts/run_retrieval.py
import os
import sys
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, ".")
from retrieval.ingestion import ingest_directory
from retrieval.vectorstore import build_vectorstore, get_retriever

def main():
    repo_path = sys.argv[1] if len(sys.argv) > 1 else "."
    persist_dir = sys.argv[2] if len(sys.argv) > 2 else "./chroma_db"

    print("加载并分块...")
    docs = ingest_directory(repo_path)
    print(f"文档数: {len(docs)}")

    print("写入向量库...")
    vs = build_vectorstore(docs, persist_directory=persist_dir)

    retriever = get_retriever(vs, k=5)
    queries = [
        "哪里定义了配置或设置？",
        "主入口或 main 函数在哪里？",
    ]
    for q in queries:
        print(f"\n查询: {q}")
        for i, doc in enumerate(retriever.invoke(q)):
            print(f"  [{i+1}] {doc.metadata.get('file_path', '')} -> {doc.page_content[:80]}...")
    print("\n完成。")

if __name__ == "__main__":
    main()
```

### 3.4 带 metadata 过滤的 Retriever（可选）

```python
# 仅检索 Python 文件
retriever = vs.as_retriever(
    search_type="similarity",
    search_kwargs={
        "k": 5,
        "filter": {"language": "python"},
    },
)
```

Chroma 的 filter 语法见其文档；不同 VectorStore 的 filter 写法略有差异，这里仅作示例。

---

## 4. 需要导入的包和环境

### 4.1 本阶段依赖

```toml
langchain-chroma>=0.1.0
chromadb>=0.4.0
langchain-openai>=0.2.0
```

```bash
uv add langchain-chroma chromadb langchain-openai
```

### 4.2 环境

- `OPENAI_API_KEY` 在 `.env` 中。
- 本地无需启动 Chroma 服务，`Chroma.from_documents(..., persist_directory=...)` 会本地持久化。

---

## 5. 本阶段小结

- **Embeddings**：`embed_documents`（批量）、`embed_query`（单条），由 OpenAI 等 provider 实现。
- **VectorStore**：`from_documents` 建库，`as_retriever()` 得到 Retriever；Chroma 适合本地开发。
- **Retriever**：`invoke(query)` 返回 `List[Document]`，与 LCEL 可组合：`retriever | format_docs` 作为 RAG 的 context 来源。

下一步：[Phase 4：RAG 管道](./phase-4-RAG管道.md)——检索 + 提示 + 生成，完整 RAG 链与简单评估。

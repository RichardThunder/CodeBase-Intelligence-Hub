# Phase 2：文档加载与分块

本阶段目标：掌握 LangChain 的 Document、Loader、TextSplitter，实现「从本地目录加载代码/文档并切成 chunk」，为向量检索做准备。

---

## 1. 设计指导

### 1.1 Document 与 Loader

- **Document**：`langchain_core.documents.Document`，通常有 `page_content`（文本）和 `metadata`（如 source、language）。
- **Loader**：把外部数据转成 `Document` 列表。常见：
  - 本地目录/文件：`DirectoryLoader`、`GenericLoader`、按语言解析的 `LanguageParser`。
  - 代码库场景：按后缀过滤（`.py`、`.md` 等），并为每个文件附加路径、语言等元数据。

### 1.2 分块策略（Chunking）

- **为什么分块**：向量模型有长度限制；按「语义单元」分块能提高检索精度。
- **代码**：按函数/类边界优于按固定字符切（见系统功能文档 §9.3）。可用 `RecursiveCharacterTextSplitter.from_language(Language.PYTHON)` 做语言感知切分。
- **文档**：Markdown 可用 `RecursiveCharacterTextSplitter` 按段落/标题切，或后续阶段用 `SemanticChunker`（需 embedding）。
- **父子文档**（ParentDocumentRetriever）：先按小 chunk 检索，再返回大 chunk 给 LLM，本阶段可只做「一种子块大小」，Phase 3/4 再上父文档。

### 1.3 设计原则

- 加载与分块**解耦**：Loader 只负责产出 `List[Document]`；Splitter 接收 Document 列表并返回更多、更小的 Document。
- 元数据**尽量保留**：file_path、language、symbol_type 等，检索和 RAG 都会用到。

---

## 2. 需要实现的功能

- [ ] 用 `DirectoryLoader` 或 `GenericLoader` 加载指定目录下的 `.py` 和 `.md` 文件，得到 `List[Document]`。
- [ ] 为每个 Document 附加 `metadata`：`source`（路径）、`language`（根据后缀推断）。
- [ ] 使用 `RecursiveCharacterTextSplitter` 对文档分块（chunk_size/chunk_overlap 可调）。
- [ ] （可选）对 Python 文件使用 `RecursiveCharacterTextSplitter.from_language(Language.PYTHON)`，对比与通用 splitter 的效果差异。
- [ ] 写一个简单脚本：指定 `repo_path`，输出「加载 + 分块后」的 chunk 数量和若干样例。

---

## 3. 示例代码

### 3.1 依赖

```bash
uv add langchain-community
# 或 pip install langchain-community
```

### 3.2 通用目录加载（代码 + Markdown）

```python
# retrieval/loaders.py
from pathlib import Path
from langchain_community.document_loaders import (
    DirectoryLoader,
    TextLoader,
    UnstructuredMarkdownLoader,
)
from langchain_community.document_loaders.generic import GenericLoader
from langchain_community.document_loaders.parsers import LanguageParser
from langchain_core.documents import Document

# 方式一：按后缀用不同 loader 的 DirectoryLoader
def load_docs_simple(dir_path: str) -> list[Document]:
    docs = []
    loaders = [
        DirectoryLoader(
            dir_path,
            glob="**/*.py",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
        ),
        DirectoryLoader(
            dir_path,
            glob="**/*.md",
            loader_cls=TextLoader,
            loader_kwargs={"encoding": "utf-8"},
        ),
    ]
    for loader in loaders:
        docs.extend(loader.load())
    return docs
```

### 3.3 使用 LanguageParser（代码解析，保留结构）

```python
# 需要安装：pip install unstructured
# retrieval/loaders.py（续）
def load_codebase_with_parser(repo_path: str) -> list[Document]:
    """使用 LanguageParser 解析代码，便于按函数/类分块"""
    loader = GenericLoader.from_filesystem(
        repo_path,
        glob="**/*.py",
        suffixes=[".py"],
        parser=LanguageParser(language="python", parser_threshold=500),
    )
    docs = loader.load()
    for doc in docs:
        path = doc.metadata.get("source", "")
        doc.metadata["file_path"] = path
        doc.metadata["language"] = "python"
    return docs
```

若未装 `unstructured`，可先用 `TextLoader` 读原始文本，仅做分块练习。

### 3.4 分块：通用 + Python 感知

```python
# retrieval/splitters.py
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_text_splitters import Language

# 通用分块（文档、配置等）
def get_doc_splitter(chunk_size: int = 800, chunk_overlap: int = 150):
    return RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )

# Python 代码分块（按函数/类边界更友好）
def get_python_splitter(chunk_size: int = 1000, chunk_overlap: int = 200):
    return RecursiveCharacterTextSplitter.from_language(
        language=Language.PYTHON,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

def split_documents(docs: list[Document], use_python_for_py: bool = True):
    from langchain_core.documents import Document
    py_splitter = get_python_splitter()
    doc_splitter = get_doc_splitter()
    out = []
    for doc in docs:
        lang = doc.metadata.get("language", "")
        if use_python_for_py and lang == "python":
            out.extend(py_splitter.split_documents([doc]))
        else:
            out.extend(doc_splitter.split_documents([doc]))
    return out
```

### 3.5 端到端：加载 + 元数据 + 分块

```python
# retrieval/ingestion.py
from pathlib import Path
from .loaders import load_docs_simple  # 或 load_codebase_with_parser
from .splitters import split_documents

def ingest_directory(dir_path: str) -> list:
    """摄入目录：加载 → 分块，返回 Document 列表"""
    raw = load_docs_simple(dir_path)
    for d in raw:
        p = d.metadata.get("source", "")
        d.metadata["file_path"] = str(Path(p).relative_to(dir_path)) if dir_path in p else p
        d.metadata["language"] = "python" if p.endswith(".py") else "markdown"
    return split_documents(raw)
```

### 3.6 可运行脚本

```python
# scripts/run_ingestion.py
import sys
sys.path.insert(0, ".")
from retrieval.ingestion import ingest_directory

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "."
    docs = ingest_directory(path)
    print(f"总 chunk 数: {len(docs)}")
    for i, d in enumerate(docs[:3]):
        print(f"--- chunk {i+1} ---")
        print(d.metadata)
        print(d.page_content[:200] + "...")
```

---

## 4. 需要导入的包和环境

### 4.1 本阶段依赖

```toml
langchain-core>=0.3.0
langchain-community>=0.3.0
langchain-text-splitters>=0.3.0
```

```bash
uv add langchain-community langchain-text-splitters
```

若使用 `LanguageParser`，需：

```bash
uv add unstructured
```

### 4.2 环境

- Python 3.11+。
- 准备一个本地目录（如当前项目或任意小 repo），用于跑 `ingest_directory`。

---

## 5. 本阶段小结

- **Document**：`page_content` + `metadata`，Loader 产出、Splitter 消费。
- **Loader**：`DirectoryLoader`、`GenericLoader` + `LanguageParser`，按需选。
- **TextSplitter**：`RecursiveCharacterTextSplitter`、`from_language(Language.PYTHON)`，代码用语言感知分块更友好。
- 管道：**加载 → 补元数据 → 分块**，为下一阶段「向量化 + 检索」提供输入。

下一步：[Phase 3：向量存储与检索](./phase-3-向量存储与检索.md)——Embeddings、Chroma、Retriever。

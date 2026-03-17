# 分阶段依赖说明

各阶段**新增**需要安装的包，便于你按阶段安装而不一次性装全量。

---

## Phase 0

```bash
uv add langchain-core langchain-openai python-dotenv openai pydantic-settings
# 或
pip install langchain-core langchain-openai python-dotenv openai pydantic-settings
```

---

## Phase 1

无新增；若未装 pydantic：

```bash
uv add pydantic
```

---

## Phase 2

```bash
uv add langchain-community langchain-text-splitters
# 若使用 LanguageParser
uv add unstructured
```

---

## Phase 3

```bash
uv add langchain-chroma chromadb
```

---

## Phase 4

无新增。若使用 RAGAS：

```bash
uv add ragas
```

---

## Phase 5

```bash
uv add langgraph
```

---

## Phase 6 / 7

同 Phase 5，已具备。

---

## Phase 8

```bash
uv add fastapi uvicorn
# 若使用 LangServe
uv add langserve
```

---

## 全量（Phase 0～8 一次装齐）

在项目根目录执行：

```bash
uv add \
  langchain-core \
  langchain-openai \
  langchain-community \
  langchain-text-splitters \
  langchain-chroma \
  chromadb \
  langgraph \
  fastapi \
  uvicorn \
  python-dotenv \
  openai \
  pydantic \
  pydantic-settings
```

可选：`unstructured`、`ragas`、`langserve`。

---

## 扩展：调用国产大模型 GLM（智谱）

- **推荐方式**：使用 LangChain `ChatOpenAI` + 智谱 base_url，**无需新增依赖**，只需在 `.env` 配置 `ZHIPU_API_KEY`。见 [extra-调用国产大模型GLM.md](./extra-调用国产大模型GLM.md)。
- **可选**：使用智谱官方 SDK 时可按官方文档安装：
  ```bash
  pip install zai-sdk    # 新 SDK
  # 或
  pip install zhipuai    # 旧版
  ```

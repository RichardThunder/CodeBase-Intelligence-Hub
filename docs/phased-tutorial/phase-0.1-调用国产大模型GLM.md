# 教学：如何调用国产大模型 GLM（智谱）

本节约你在项目中接入**智谱 AI 的 GLM 系列模型**（如 GLM-4、GLM-4.7），可与 Phase 0 / Phase 1 的链无缝替换，便于在无法使用 OpenAI 时改用国产模型。

**参考文档**：[智谱开放平台 - GLM-4.7](https://docs.bigmodel.cn/cn/guide/models/text/glm-4.7#python)

---

## 1. 设计指导

### 1.1 智谱 API 与 LangChain 的两种接入方式

| 方式 | 说明 | 适用场景 |
|------|------|----------|
| **OpenAI 兼容 Base URL** | 智谱 v4 接口与 OpenAI Chat Completions 兼容，用 `ChatOpenAI(base_url=..., api_key=...)` 即可 | 与现有 LangChain 链/图零改动，只换 LLM 实例 |
| **官方 SDK（zhipuai / zai-sdk）** | 使用智谱官方 Python SDK，支持思考模式、流式等 | 需要智谱独有能力（如 thinking、reasoning_content）或非 LangChain 场景 |
| **LangChain ChatZhipuAI** | `langchain_community.chat_models.ChatZhipuAI` | 社区封装，可能随版本迭代；若可用则与 ChatOpenAI 用法一致 |

本教学**重点写「OpenAI 兼容 + ChatOpenAI」**，这样你在 Phase 0～8 中只需统一「换一个 LLM 工厂」即可切到 GLM；再简要给出官方 SDK 的调用方式，便于对照官方文档。

### 1.2 智谱 v4 接口要点（来自官方文档）

- **Base URL**：`https://open.bigmodel.cn/api/paas/v4`
- **认证**：`Authorization: Bearer <API Key>`
- **模型名**：如 `glm-4`、`glm-4-flash`、`glm-4.7`、`glm-4.7-flash` 等
- **思考模式**：请求体可带 `thinking: { "type": "enabled" }`（官方 SDK 支持；OpenAI 兼容模式下部分客户端可能需额外处理）
- **流式**：`stream: true`，流式 chunk 中可能有 `reasoning_content`（思考过程）与 `content`（最终回复）

---

## 2. 需要实现的功能

- [ ] 在 `.env` 中配置智谱 API Key（如 `ZHIPU_API_KEY`）。
- [ ] 用 **ChatOpenAI + base_url** 创建 GLM 的 LangChain 聊天模型，并跑通一条最小链（同 Phase 0）。
- [ ] （可选）用智谱官方 Python SDK（zhipuai 或 zai-sdk）写一次基础调用与流式调用，理解消息格式。
- [ ] 在项目里提供「LLM 工厂」：根据配置返回 OpenAI 或 GLM，便于 Phase 1～8 统一切换模型。

---

## 3. 示例代码

### 3.1 环境变量

在 `.env` 中增加（不要提交到 Git）：

```bash
# 智谱开放平台 API Key：https://open.bigmodel.cn/
ZHIPU_API_KEY=your-zhipu-api-key-here
```

可选：若希望默认用 GLM，可加：

```bash
# 可选：默认使用 GLM（否则用 OPENAI_API_KEY）
DEFAULT_LLM_PROVIDER=zhipu
```

### 3.2 方式一：LangChain ChatOpenAI + 智谱 Base URL（推荐）

智谱 v4 接口与 OpenAI Chat Completions 兼容，只需把 `base_url` 指到智谱、`api_key` 用智谱 Key、`model` 填智谱模型名即可。

```python
# config/llm_factory.py
import os
from langchain_openai import ChatOpenAI

# 智谱 v4 文档：https://docs.bigmodel.cn/cn/guide/models/text/glm-4.7#python
ZHIPU_BASE_URL = "https://open.bigmodel.cn/api/paas/v4"

def get_glm_chat_model(
    model: str = "glm-4-flash",
    temperature: float = 0,
    api_key: str | None = None,
):
    """返回可用于 LangChain 链的智谱 GLM 聊天模型（OpenAI 兼容接口）。"""
    key = api_key or os.getenv("ZHIPU_API_KEY")
    if not key:
        raise ValueError("请设置环境变量 ZHIPU_API_KEY 或在调用时传入 api_key")
    return ChatOpenAI(
        model=model,
        temperature=temperature,
        api_key=key,
        base_url=ZHIPU_BASE_URL,
    )

def get_llm(provider: str | None = None):
    """统一 LLM 工厂：根据环境变量或参数返回 OpenAI 或 GLM。"""
    provider = provider or os.getenv("DEFAULT_LLM_PROVIDER", "openai")
    if provider.lower() == "zhipu":
        return get_glm_chat_model()
    return ChatOpenAI(model="gpt-4o-mini", temperature=0)
```

**最小链示例（与 Phase 0 一致，仅换 LLM）**：

```python
# main_glm.py
import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from config.llm_factory import get_glm_chat_model

load_dotenv()

def main():
    llm = get_glm_chat_model(model="glm-4-flash", temperature=0)
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个代码库助手，用简洁中文回答。"),
        ("human", "{question}"),
    ])
    chain = prompt | llm | StrOutputParser()
    answer = chain.invoke({"question": "什么是 RAG？用一句话说明。"})
    print(answer)

if __name__ == "__main__":
    main()
```

### 3.3 方式二：智谱官方 Python SDK（对照官方文档）

官方文档推荐使用 **zai-sdk**（新）或 **zhipuai**（旧）。以下以文档中的接口为准。

**安装**：

```bash
# 新 SDK（文档推荐）
pip install zai-sdk
# 或旧版
pip install zhipuai
```

**基础调用（zai-sdk）**——摘自 [GLM-4.7 文档](https://docs.bigmodel.cn/cn/guide/models/text/glm-4.7#python)：

```python
from zai import ZhipuAiClient
import os

client = ZhipuAiClient(api_key=os.getenv("ZHIPU_API_KEY"))

response = client.chat.completions.create(
    model="glm-4.7",
    messages=[
        {"role": "user", "content": "作为一名营销专家，请为我的产品创作一个吸引人的口号"},
        {"role": "assistant", "content": "当然，要创作一个吸引人的口号，请告诉我一些关于您产品的信息"},
        {"role": "user", "content": "智谱AI开放平台"}
    ],
    thinking={"type": "enabled"},
    max_tokens=65536,
    temperature=1.0,
)
print(response.choices[0].message)
```

**流式调用（zai-sdk）**：

```python
response = client.chat.completions.create(
    model="glm-4.7",
    messages=[{"role": "user", "content": "智谱AI开放平台"}],
    thinking={"type": "enabled"},
    stream=True,
    max_tokens=65536,
    temperature=1.0,
)
for chunk in response:
    if chunk.choices[0].delta.reasoning_content:
        print(chunk.choices[0].delta.reasoning_content, end='', flush=True)
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end='', flush=True)
```

**旧版 zhipuai**（文档中「Python(旧)」）：

```python
from zhipuai import ZhipuAI

client = ZhipuAI(api_key=os.getenv("ZHIPU_API_KEY"))
response = client.chat.completions.create(
    model="glm-4.7",
    messages=[
        {"role": "user", "content": "你好"},
    ],
    thinking={"type": "enabled"},
    max_tokens=1024,
    temperature=0.8,
)
print(response.choices[0].message)
```

在 **LangChain 链中**若要坚持用官方 SDK，需要自己封装成 LangChain 的 `BaseChatModel`（实现 `_generate` 等），工作量较大；**推荐在 LangChain 项目里直接用「方式一」ChatOpenAI + base_url**，即可复用所有 Phase 0～8 的链与图。

### 3.4 在现有 Phase 1 / RAG 链中切换为 GLM

只需把原来的 `ChatOpenAI(...)` 换成 `get_glm_chat_model()` 或 `get_llm()` 即可，链结构不变：

```python
# 原 Phase 1 / Phase 4 写法
# from langchain_openai import ChatOpenAI
# llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)

# 改为 GLM
from config.llm_factory import get_glm_chat_model
llm = get_glm_chat_model(model="glm-4-flash", temperature=0)

# 后续 chain = prompt | llm | ... 不变
```

### 3.5 （可选）LangChain Community ChatZhipuAI

若你使用的 `langchain_community` 版本中已包含并更新了 `ChatZhipuAI`（支持 v4），可以这样用：

```python
# 需安装：pip install langchain-community
from langchain_community.chat_models import ChatZhipuAI

llm = ChatZhipuAI(
    model="glm-4-flash",
    temperature=0,
    api_key=os.getenv("ZHIPU_API_KEY"),
)
# 与 ChatOpenAI 一样参与 LCEL 链
chain = prompt | llm | StrOutputParser()
```

注意：社区版可能随智谱 API 升级而有延迟或差异，若遇到 429 或参数不兼容，可优先用「方式一」OpenAI 兼容 base_url。

---

## 4. 需要导入的包和环境

### 4.1 方式一（推荐：LangChain + 智谱 OpenAI 兼容）

**无需新增包**。现有项目若已安装 `langchain-openai`，只需在 `.env` 中配置 `ZHIPU_API_KEY` 即可。

### 4.2 方式二：智谱官方 SDK

```bash
# 新 SDK（文档推荐）
pip install zai-sdk
# 或旧版
pip install zhipuai
```

### 4.3 环境

- **API Key**：在 [智谱开放平台](https://open.bigmodel.cn/) 申请，写入 `.env` 的 `ZHIPU_API_KEY`。
- **网络**：能访问 `https://open.bigmodel.cn`。
- **模型名**：按文档与计费选择，如 `glm-4-flash`（轻量）、`glm-4`、`glm-4.7`、`glm-4.7-flash` 等。

---

## 5. 本节约你掌握的内容

- **智谱 v4 与 OpenAI 接口兼容**：用 `ChatOpenAI(base_url=智谱v4, api_key=ZHIPU_API_KEY, model=glm-xxx)` 即可在 LangChain 中使用 GLM。
- **统一 LLM 工厂**：通过 `get_llm(provider="zhipu")` 或环境变量 `DEFAULT_LLM_PROVIDER=zhipu`，可在不改链/图代码的前提下切换国产模型。
- **官方 SDK**：需要思考模式、流式 reasoning_content 等时，可对照 [官方 GLM-4.7 文档](https://docs.bigmodel.cn/cn/guide/models/text/glm-4.7#python) 使用 `zai-sdk` 或 `zhipuai`；在 LangChain 中仍推荐用 base_url 方式以复用现有链与图。

---

**相关链接**

- 智谱 GLM-4.7 文档（含 cURL / Python / Java）：<https://docs.bigmodel.cn/cn/guide/models/text/glm-4.7#python>
- 智谱 API 参考：<https://docs.bigmodel.cn/api-reference/模型-api/对话补全>
- LangChain 使用自定义 base_url：<https://docs.langchain.com/oss/python/langchain/models>（OpenAI-compatible API）

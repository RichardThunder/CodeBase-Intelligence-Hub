# Phase 0：环境与 LangChain 初识

本阶段目标：搭好开发环境，跑通第一条「Prompt → LLM → 输出」的链，建立对 LangChain 模块划分的直观认识。

---

## 1. 设计指导

### 1.1 为什么要先做「最小链」

- LangChain 的核心抽象是 **Runnable**：输入 → 输出，可组合。一条「链」就是多个 Runnable 的管道。
- 先不碰 RAG、Agent，只做「用户输入 → 模型 → 文本输出」，能让你专注理解：
  - **langchain_core**：Prompt、LLM、OutputParser、Runnable 接口。
  - **langchain_openai**（或其它 provider）：对 OpenAI API 的封装。
- 设计原则：**每一步都可单独测试**。后面阶段会在这条链前面加「检索」、后面加「解析」，形成 RAG 链。

### 1.2 LangChain 包结构（建立心智模型）

```
langchain_core       → 核心抽象：Runnable, Prompt, Message, Document
langchain_openai     → OpenAI ChatModels, Embeddings
langchain_community  → 各类 Loader、Tool、集成（DB、API）
langgraph            → 图与多 Agent 编排（Phase 6 再用）
```

本阶段只用 **langchain_core** + **langchain_openai** 即可。

---

## 2. 需要实现的功能

- [ ] 创建 Python 3.11+ 虚拟环境并安装依赖。
- [ ] 配置环境变量（如 `OPENAI_API_KEY`），不把 key 写进代码。
- [ ] 写一条最小链：固定系统提示 + 用户输入 → ChatOpenAI → 取文本内容。
- [ ] 在本地运行并打印输出，确认端到端通畅。

---

## 3. 示例代码

### 3.1 环境变量与配置

创建 `.env`（不要提交到 Git）：

```bash
# .env
OPENAI_API_KEY=sk-your-key-here
OPENAI_API_BASE=https://api.openai.com/v1  # 若用代理可改
```

创建 `config/settings.py`，用 `pydantic-settings` 读环境变量（可选，Phase 0 也可直接用 `os.getenv`）：

```python
# config/settings.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    openai_api_key: str = ""
    openai_api_base: str | None = None

    class Config:
        env_file = ".env"
        extra = "ignore"
```

### 3.2 最小链：Prompt → LLM → 字符串

```python
# main.py（Phase 0 版本）
import os
from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI

load_dotenv()

def main():
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个代码库助手，用简洁中文回答。"),
        ("human", "{question}"),
    ])
    llm = ChatOpenAI(
        model="gpt-4o-mini",
        temperature=0,
        api_key=os.getenv("OPENAI_API_KEY"),
        base_url=os.getenv("OPENAI_API_BASE"),
    )
    parser = StrOutputParser()

    # 链：prompt | llm | parser
    chain = prompt | llm | parser

    answer = chain.invoke({"question": "什么是 RAG？用一句话说明。"})
    print(answer)

if __name__ == "__main__":
    main()
```

要点：
- `ChatPromptTemplate.from_messages` 支持 system/human/ai 角色，`{question}` 为变量。
- `StrOutputParser()` 把 `AIMessage` 转成 `str`。
- `prompt | llm | parser` 即 LCEL 写法：按顺序执行，上一段输出作为下一段输入。

---

## 4. 需要导入的包和环境

### 4.1 本阶段依赖

```toml
# 在 pyproject.toml 的 [project] dependencies 中加入，或单独安装：
langchain-core>=1.2.19
langchain-openai>=1.1.11
python-dotenv>=1.2.2
openai>=2.28.0
pydantic-settings>=2.13.1   # 若用 config/settings.py
```

安装命令（在项目根目录）：

```bash
# 使用 uv
uv add langchain-core langchain-openai python-dotenv openai pydantic-settings

# 或 pip
pip install langchain-core langchain-openai python-dotenv openai pydantic-settings
```

### 4.2 环境要求

- **Python**：3.11 或 3.12。
- **网络**：能访问 OpenAI API（或你配置的 base_url）。
- **.env**：在项目根目录，且 `.gitignore` 已包含 `.env`。

---

## 5. 本阶段小结

- 你已跑通 **最小 LangChain 链**：`Prompt → LLM → StrOutputParser`。
- 知道 **LCEL** 的管道写法：`a | b | c` 表示数据依次流过 a、b、c。
- 知道 **langchain_core** 提供 Prompt/OutputParser，**langchain_openai** 提供 ChatOpenAI。

下一步：[Phase 1：LCEL 与提示词](./phase-1-LCEL与提示词.md)——深入 LCEL、多步链、结构化输出。

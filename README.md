# CodeBase Intelligence Hub

一个基于 RAG (检索增强生成) 的代码库智能问答系统，使用 LangChain、LangGraph 和多智能体模式构建。

**项目性质**: 学习项目 - 从基础 LangChain 用法逐步进阶到多智能体编排和 API 服务

## 🎯 核心特性

- **RAG 管道**: 使用 ChromaDB 向量存储实现高效的语义检索
- **多智能体架构**: 基于 LangGraph 的状态图编排多个专用智能体
- **LLM 兼容性**: 支持任何 OpenAI 兼容的 API（默认配置 GLM/Zhipu AI）
- **流式响应**: 通过 FastAPI + LangServe 提供实时流式 API
- **文本处理**: 支持代码和文档的智能分割与索引
- **灵活配置**: 基于 Pydantic Settings 的环境变量配置系统

## 📋 前置要求

- Python >= 3.11
- OpenAI 兼容 API 密钥
  - 示例: GLM (智谱清言) 的 API 端点: `https://open.bigmodel.cn/api/paas/v4`
  - 也支持 OpenAI、Azure OpenAI 等其他兼容服务

## 🚀 快速开始

### 1. 环境配置

```bash
# 克隆并进入项目目录
cd CodeBase-Intelligence-Hub

# 复制环境配置模板
cp .env.example .env

# 编辑 .env 填入 API 密钥和基础 URL
# 必需变量:
# - OPENAI_API_KEY=your_api_key_here
# - OPENAI_API_BASE=https://your-api-base-url/api/paas/v4
```

### 2. 安装依赖

使用 uv (推荐):
```bash
uv sync
```

或使用 pip:
```bash
pip install -e .
```

安装开发工具 (可选):
```bash
uv sync --extra dev
```

### 3. 运行应用

启动主程序:
```bash
uv run python main.py
# 或
python main.py
```

启动 API 服务器:
```bash
uv run python api/serve.py
# 服务可在 http://localhost:8000 访问
```

## 📁 项目结构

项目按学习阶段递增增长:

| 目录 | 阶段 | 功能描述 |
|------|------|--------|
| `main.py` | 0–1 | 入口点；基础 LangChain 链 |
| `config/` | 1+ | Pydantic 配置管理 (`settings.py`) |
| `retrieval/` | 2+ | 文档加载、文本分割、向量存储 |
| `chains/` | 1+ | LCEL 链定义；RAG 链 (`rag.py`) |
| `agents/` | 5+ | ReAct 模式的工具使用智能体 |
| `graph/` | 6+ | LangGraph 状态图定义 |
| `api/` | 8 | FastAPI + LangServe HTTP 服务 |
| `docs/` | — | 学习教程和设计文档 |

## 🔄 核心数据流

```
用户查询
  ↓
LangGraph 编排器
  ↓
路由到专用智能体 (检索、推理等)
  ↓
ChromaDB 向量检索
  ↓
结果聚合
  ↓
FastAPI/LangServe 流式响应
```

## 🛠 主要技术栈

### 核心框架
- **LangChain** - LLM 应用开发框架
- **LangGraph** - 多智能体编排
- **LangServe** - LLM 应用 REST API 服务

### LLM & 向量
- **ChatOpenAI** (OpenAI 兼容 API)
- **ChromaDB** - 向量数据库
- **Sentence Transformers** - 文本嵌入模型

### Web 框架
- **FastAPI** - 现代异步 Web 框架
- **Uvicorn** - ASGI 服务器
- **SSE Starlette** - 服务器发送事件支持

### 工具库
- **Pydantic** - 数据验证和配置管理
- **python-dotenv** - 环境变量加载
- **Unstructured** - 文档解析
- **rank-bm25** - BM25 关键词搜索

## 📖 核心概念

### LCEL (LangChain Expression Language)
使用管道操作符 (`|`) 组合链:
```python
chain = prompt | llm | parser
```

### 配置管理
所有配置通过环境变量管理，在 `config/settings.py` 中定义:
```python
from config.settings import Settings
settings = Settings()
print(settings.openai_api_key)
```

### RAG 流程
1. **加载**: 使用 `retrieval/` 中的加载器读取代码文件
2. **分割**: 根据文件类型智能分割文本
3. **嵌入**: 使用 Sentence Transformers 转换为向量
4. **存储**: 保存到 ChromaDB
5. **检索**: 基于语义相似度查询相关代码片段

## 🧪 开发工具

项目包含完整的开发工具链:

```bash
# 代码质量检查
uv run ruff check .           # Linting
uv run pyright --verifytypes . # Type checking
uv run pylint src/           # Code quality
uv run radon mi .            # 可维护性指数

# 安全性检查
uv run bandit -r src/        # 安全漏洞扫描
uv run semgrep --config=p/owasp-top-ten src/
uv run pip-audit             # 依赖漏洞检查

# 单元测试
uv run pytest                # 运行所有测试
uv run pytest --cov         # 覆盖率报告
```

## 🔐 环境变量

必需配置:
- `OPENAI_API_KEY` - LLM 提供商的 API 密钥
- `OPENAI_API_BASE` - API 基础 URL

可选配置:
- `LOG_LEVEL` - 日志级别 (default: `INFO`)
- `CHROMA_DB_PATH` - ChromaDB 数据库路径 (default: `./chroma_db`)
- `MODEL_NAME` - 使用的模型名称

参考 `.env.example` 获取完整列表。

## 📚 学习资源

详细的学习教程和阶段说明，请参考:
- `docs/phased-tutorial/00-总览与阶段索引.md` - 完整学习路线图
- 各阶段的代码注释和设计文档

## 🤝 贡献指南

欢迎提交 PR 和 Issue。请确保:

1. 遵循项目的代码风格 (由 Ruff 定义)
2. 添加必要的测试用例
3. 更新相关文档
4. 通过所有质量检查:
   ```bash
   uv run ruff check --fix .
   uv run pyright --verifytypes .
   uv run pytest
   ```

## 📝 项目状态

- **当前版本**: 1.0.1
- **主要特性**: 基础 RAG 管道、多智能体编排、API 服务
- **开发阶段**: 学习项目 - 持续迭代中

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## 🆘 常见问题

### Q: 如何更换 LLM 提供商?
A: 修改 `.env` 中的 `OPENAI_API_BASE` 和 `OPENAI_API_KEY`，或在 `config/settings.py` 中修改 `ChatOpenAI` 初始化参数。

### Q: 支持哪些文件类型?
A: 项目使用 `Unstructured` 库，支持代码文件、文档、PDF 等多种格式。详见 `retrieval/loaders.py`。

### Q: 如何自定义向量检索?
A: 修改 `retrieval/` 中的相关文件，调整分割策略或嵌入模型。

### Q: 如何扩展智能体功能?
A: 在 `agents/` 目录中添加新的智能体类，在 `graph/` 中的状态图中注册。

## 📞 联系方式

如有问题，欢迎提交 GitHub Issue。

---

**🎓 学习目标**: 通过逐步构建完整的 RAG 系统，深入理解 LangChain、LangGraph 和 AI 应用架构的最佳实践。

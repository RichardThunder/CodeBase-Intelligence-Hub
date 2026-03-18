# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

CodeBase Intelligence Hub is a **learning project** for building a RAG-based codebase Q&A system using LangChain, LangGraph, and multi-agent patterns. The project is structured as a phased tutorial progressing from basic LangChain usage through multi-agent orchestration and API serving.

The LLM backend uses an **OpenAI-compatible API** — currently configured to use GLM (Zhipu AI) models but can work with any OpenAI-compatible endpoint.

## Environment Setup

```bash
# Copy env template and fill in API keys
cp .env.example .env

# Install dependencies with uv (preferred)
uv sync

# Or with pip
pip install -e .
```

Required `.env` variables:

- `OPENAI_API_KEY` — API key for the LLM provider
- `OPENAI_API_BASE` — Base URL (e.g., `https://open.bigmodel.cn/api/paas/v4` for GLM)

## Commands

```bash
# Run the main entry point
uv run python main.py
# or
python main.py

# Run a specific phase script (once implemented)
uv run python -m retrieval.loaders
```

There is currently no test runner or linter configured in `pyproject.toml`.

## Architecture

The project directory grows incrementally across phases (see `docs/phased-tutorial/00-总览与阶段索引.md`):

| Directory | Phase | Purpose |
|-----------|-------|---------|
| `main.py` | 0–1 | Entry point; minimal LangChain chain |
| `config/settings.py` | 1+ | Pydantic-based settings loaded from `.env` |
| `retrieval/` | 2+ | Document loaders, text splitters, vector store |
| `chains/` | 1+ | LCEL chain definitions; `rag.py` added in Phase 4 |
| `agents/` | 5+ | Tool-using agents with ReAct pattern |
| `graph/` | 6+ | LangGraph `StateGraph` definitions (state, builder) |
| `api/` | 8 | FastAPI + LangServe HTTP endpoint |

**Core data flow (final system):** User query → LangGraph orchestrator → routes to specialist agents (retrieval agent uses ChromaDB vector store) → results aggregated → streamed response via FastAPI/LangServe.

**Key LangChain patterns used:**

- LCEL (`prompt | llm | parser`) for chain composition
- `ChatOpenAI` with custom `base_url` for OpenAI-compatible providers
- `langchain_chroma` + `langchain_text_splitters` for RAG pipeline
- `StateGraph` from LangGraph for multi-agent orchestration
- `LangServe` for serving chains as REST endpoints

## Configuration

`config/settings.py` uses `pydantic-settings` with `BaseSettings` — all config comes from environment variables or `.env` file. The `Settings` class is the single source of truth for runtime config; prefer importing from it over `os.getenv()` directly.

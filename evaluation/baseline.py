"""Naive single-LCEL-chain RAG baseline.

Uses pure cosine similarity retrieval (no MMR, no BM25, no MultiQuery).
Reuses chains/rag.py and retrieval/vectorstore.py to ensure identical
formatting and LLM config — only the retriever strategy differs.
"""

import time
from langchain_openai import ChatOpenAI
from config.settings import Settings
from retrieval.vectorstore import load_vectorstore
from retrieval.embeddings import get_embeddings
from chains.rag import build_rag_chain_with_source


def build_baseline_retriever(settings: Settings, k: int = 5):
    """Pure cosine similarity retriever — no MMR, BM25, or MultiQuery.

    Args:
        settings: Configuration for embeddings and vectorstore
        k: Number of documents to retrieve

    Returns:
        Chroma retriever using cosine similarity search
    """
    embeddings = get_embeddings(settings)
    vectorstore = load_vectorstore(embeddings, settings)
    return vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k},
    )


def build_baseline_llm(settings: Settings) -> ChatOpenAI:
    """Build LLM identical to advanced system."""
    return ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key.get_secret_value(),
        base_url=settings.openai_api_base or "https://api.openai.com/v1",
        temperature=0,
    )


def run_baseline(question: str, settings: Settings) -> dict:
    """Run naive RAG on a single question.

    Args:
        question: User question
        settings: Configuration

    Returns:
        dict with keys:
          - answer: str
          - retrieved_files: list[str]  (file_path from each source)
          - latency_ms: float
    """
    retriever = build_baseline_retriever(settings, k=5)
    llm = build_baseline_llm(settings)
    chain = build_rag_chain_with_source(retriever, llm)

    start = time.perf_counter()
    result = chain.invoke({"question": question})
    latency_ms = (time.perf_counter() - start) * 1000

    retrieved_files = [
        src.get("file_path", "unknown")
        for src in result.get("sources", [])
    ]

    return {
        "answer": result.get("answer", ""),
        "retrieved_files": retrieved_files,
        "latency_ms": latency_ms,
    }

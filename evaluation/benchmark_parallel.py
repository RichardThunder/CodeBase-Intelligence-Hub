"""Benchmark comparing original vs parallel-optimized systems.

This script measures the performance impact of parallelization:
- Original: Sequential execution
- Parallel: Concurrent vector + BM25 retrieval
"""

import time
from config.settings import Settings
from evaluation.dataset import DATASET
from evaluation.baseline import run_baseline
from retrieval.embeddings import get_embeddings
from retrieval.vectorstore import load_vectorstore
from retrieval.pipeline import build_retrieval_pipeline
from retrieval.pipeline_parallel import build_retrieval_pipeline_parallel
from langchain_openai import ChatOpenAI
from langchain_core.documents import Document


def test_retrieval_latency():
    """Compare retrieval latency: original vs parallel."""
    print("\n" + "=" * 60)
    print("📊 Retrieval Pipeline Latency Comparison")
    print("=" * 60)

    settings = Settings()
    embeddings = get_embeddings(settings)
    vectorstore = load_vectorstore(embeddings, settings)
    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key.get_secret_value(),
        base_url=settings.openai_api_base,
        temperature=0,
    )

    # Prepare documents for BM25
    all_docs_result = vectorstore._collection.get(include=["documents", "metadatas"])
    bm25_docs = [
        Document(page_content=text, metadata=meta)
        for text, meta in zip(
            all_docs_result["documents"], all_docs_result["metadatas"]
        )
    ]

    # Build retrievers
    print("\n📦 Building retrievers...")
    original_retriever = build_retrieval_pipeline(vectorstore, bm25_docs, llm, settings)
    parallel_retriever = build_retrieval_pipeline_parallel(
        vectorstore, bm25_docs, llm, settings
    )

    # Test queries
    test_queries = [
        "Where is the BM25 retriever built?",
        "What function handles intent classification?",
        "What is the AgentState definition?",
        "How does the synthesizer work?",
        "What is the retrieval pipeline?",
    ]

    results = []

    for query in test_queries:
        print(f"\n📝 Query: {query[:50]}...")

        # Original retrieval
        start = time.perf_counter()
        try:
            original_docs = original_retriever.invoke(query)
            original_time = (time.perf_counter() - start) * 1000
        except Exception as e:
            print(f"  ❌ Original failed: {e}")
            original_time = None
            original_docs = []

        # Parallel retrieval
        start = time.perf_counter()
        try:
            parallel_docs = parallel_retriever.invoke(query)
            parallel_time = (time.perf_counter() - start) * 1000
        except Exception as e:
            print(f"  ⚠️  Parallel failed: {e}")
            parallel_time = None
            parallel_docs = []

        # Results
        if original_time and parallel_time:
            speedup = original_time / parallel_time
            improvement = (1 - parallel_time / original_time) * 100

            print(f"  Original:  {original_time:7.0f}ms ({len(original_docs)} docs)")
            print(f"  Parallel:  {parallel_time:7.0f}ms ({len(parallel_docs)} docs)")
            print(
                f"  Speedup:   {speedup:.2f}x ({improvement:+.1f}%) {'✅' if speedup > 1 else '❌'}"
            )

            results.append(
                {
                    "query": query,
                    "original_ms": original_time,
                    "parallel_ms": parallel_time,
                    "speedup": speedup,
                    "improvement_pct": improvement,
                }
            )

    # Summary
    if results:
        print("\n" + "=" * 60)
        print("📈 Summary")
        print("=" * 60)

        avg_original = sum(r["original_ms"] for r in results) / len(results)
        avg_parallel = sum(r["parallel_ms"] for r in results) / len(results)
        avg_speedup = sum(r["speedup"] for r in results) / len(results)

        print(f"\n✅ Average Original:   {avg_original:7.0f}ms")
        print(f"✅ Average Parallel:   {avg_parallel:7.0f}ms")
        print(f"✅ Average Speedup:    {avg_speedup:.2f}x")
        print(f"✅ Overall Improvement: {(1 - avg_parallel/avg_original)*100:+.1f}%")

        print("\n📊 Detailed Results:")
        print(f"{'Query':<40} {'Original':>10} {'Parallel':>10} {'Speedup':>8}")
        print("-" * 70)
        for r in results:
            query_short = r["query"][:35] + "..."
            print(
                f"{query_short:<40} {r['original_ms']:>9.0f}ms {r['parallel_ms']:>9.0f}ms {r['speedup']:>7.2f}x"
            )


if __name__ == "__main__":
    test_retrieval_latency()

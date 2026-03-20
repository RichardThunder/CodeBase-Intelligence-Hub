"""CLI benchmark runner comparing baseline vs. advanced RAG systems.

Usage:
    uv run python -m evaluation.benchmark
    uv run python -m evaluation.benchmark --subset code_lookup explanation
    uv run python -m evaluation.benchmark --skip-llm-eval
    uv run python -m evaluation.benchmark --enable-rerank
    uv run python -m evaluation.benchmark --output results/my_run.json
"""

import argparse
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path

from config.settings import Settings
from evaluation.dataset import DATASET, get_dataset_subset, QAPair
from evaluation.baseline import run_baseline
from evaluation.metrics import (
    retrieval_recall_at_k,
    retrieval_precision_at_k,
    evaluate_answer,
)


RESULTS_DIR = Path(__file__).parent / "results"
ALL_CATEGORIES = ["code_lookup", "explanation", "bug_analysis", "general_qa", "git_history"]


def build_advanced_system(settings: Settings):
    """Build the advanced multi-agent graph + retriever.

    Returns:
        (graph, retriever) tuple
    """
    from langchain_openai import ChatOpenAI
    from retrieval.vectorstore import load_vectorstore
    from retrieval.embeddings import get_embeddings
    from retrieval.pipeline import build_retrieval_pipeline
    from graph.builder import build_graph_from_settings

    llm = ChatOpenAI(
        model=settings.llm_model,
        api_key=settings.openai_api_key.get_secret_value(),
        base_url=settings.openai_api_base or "https://api.openai.com/v1",
        temperature=0,
    )

    embeddings = get_embeddings(settings)
    vectorstore = load_vectorstore(embeddings, settings)

    # BM25 needs all stored documents — fetch from vectorstore
    # Use a large k to get a representative sample for BM25 indexing
    all_docs_result = vectorstore._collection.get(include=["documents", "metadatas"])
    from langchain_core.documents import Document
    bm25_docs = [
        Document(page_content=text, metadata=meta)
        for text, meta in zip(
            all_docs_result["documents"],
            all_docs_result["metadatas"],
        )
    ]

    retriever = build_retrieval_pipeline(vectorstore, bm25_docs, llm, settings)
    graph = build_graph_from_settings(retriever, llm, settings)

    return graph, retriever


def run_advanced(question: str, graph) -> dict:
    """Run the multi-agent graph on a single question.

    Args:
        question: User question
        graph: Compiled LangGraph

    Returns:
        dict with answer, retrieved_files, latency_ms
    """
    from graph.state import AgentState

    initial_state: AgentState = {
        "user_query": question,
        "session_id": str(uuid.uuid4()),
        "history": [],
        "intent": "",
        "intent_confidence": 0.0,
        "next_agent": "",
        "retrieved_chunks": [],
        "analysis_results": [],
        "code_outputs": [],
        "search_results": [],
        "final_answer": "",
        "requires_human_approval": False,
        "human_approval_given": False,
        "error_message": None,
        "iteration_count": 0,
        "timestamps": [],
    }

    config = {"configurable": {"thread_id": str(uuid.uuid4())}}

    start = time.perf_counter()
    result = graph.invoke(initial_state, config=config)
    latency_ms = (time.perf_counter() - start) * 1000

    retrieved_files = [
        chunk.get("file_path", "unknown")
        for chunk in result.get("retrieved_chunks", [])
    ]

    return {
        "answer": result.get("final_answer", ""),
        "retrieved_files": retrieved_files,
        "latency_ms": latency_ms,
    }


def evaluate_pair(
    qa: QAPair,
    baseline_result: dict,
    advanced_result: dict,
    settings: Settings,
    skip_llm_eval: bool,
    k: int = 5,
) -> dict:
    """Compute all metrics for one QA pair."""
    # Retrieval metrics (deterministic)
    baseline_recall = retrieval_recall_at_k(
        baseline_result["retrieved_files"], qa.relevant_files, k
    )
    baseline_precision = retrieval_precision_at_k(
        baseline_result["retrieved_files"], qa.relevant_files, k
    )
    advanced_recall = retrieval_recall_at_k(
        advanced_result["retrieved_files"], qa.relevant_files, k
    )
    advanced_precision = retrieval_precision_at_k(
        advanced_result["retrieved_files"], qa.relevant_files, k
    )

    # Answer quality (LLM judge)
    baseline_quality = evaluate_answer(
        qa.question,
        qa.expected_answer,
        baseline_result["answer"],
        settings,
        skip_llm_eval=skip_llm_eval,
    )
    advanced_quality = evaluate_answer(
        qa.question,
        qa.expected_answer,
        advanced_result["answer"],
        settings,
        skip_llm_eval=skip_llm_eval,
    )

    return {
        "id": qa.id,
        "category": qa.category,
        "difficulty": qa.difficulty,
        "requires_git": qa.requires_git,
        "question": qa.question,
        "baseline": {
            "answer": baseline_result["answer"],
            "retrieved_files": baseline_result["retrieved_files"],
            "latency_ms": baseline_result["latency_ms"],
            "recall_at_k": baseline_recall,
            "precision_at_k": baseline_precision,
            "faithfulness": baseline_quality["faithfulness"],
            "relevance": baseline_quality["relevance"],
            "resolution": baseline_quality["resolution"],
        },
        "advanced": {
            "answer": advanced_result["answer"],
            "retrieved_files": advanced_result["retrieved_files"],
            "latency_ms": advanced_result["latency_ms"],
            "recall_at_k": advanced_recall,
            "precision_at_k": advanced_precision,
            "faithfulness": advanced_quality["faithfulness"],
            "relevance": advanced_quality["relevance"],
            "resolution": advanced_quality["resolution"],
        },
    }


def run_benchmark(
    categories: list[str] | None,
    skip_llm_eval: bool,
    output_path: Path,
    enable_rerank: bool,
) -> None:
    """Main benchmark loop."""
    # Settings — optionally override enable_rerank
    settings = Settings()
    if enable_rerank:
        settings = Settings(enable_rerank=True)

    # Dataset
    if categories:
        dataset = get_dataset_subset(categories)
    else:
        dataset = DATASET

    print(f"\n{'='*60}")
    print(f"Benchmark: {len(dataset)} QA pairs")
    print(f"  Categories: {categories or ALL_CATEGORIES}")
    print(f"  Skip LLM eval: {skip_llm_eval}")
    print(f"  Enable rerank: {enable_rerank}")
    print(f"  Output: {output_path}")
    print(f"{'='*60}\n")

    # Build advanced system once (shared across all pairs)
    print("Building advanced system...")
    graph, _ = build_advanced_system(settings)
    print("Advanced system ready.\n")

    records = []
    for i, qa in enumerate(dataset, 1):
        print(f"[{i}/{len(dataset)}] {qa.id} ({qa.category})")
        print(f"  Q: {qa.question[:80]}...")

        # Run baseline
        print("  Running baseline...")
        try:
            baseline_result = run_baseline(qa.question, settings)
            print(f"  Baseline latency: {baseline_result['latency_ms']:.0f}ms")
        except Exception as e:
            print(f"  Baseline ERROR: {e}")
            baseline_result = {"answer": f"ERROR: {e}", "retrieved_files": [], "latency_ms": 0.0}

        # Run advanced
        print("  Running advanced...")
        try:
            advanced_result = run_advanced(qa.question, graph)
            print(f"  Advanced latency: {advanced_result['latency_ms']:.0f}ms")
        except Exception as e:
            print(f"  Advanced ERROR: {e}")
            advanced_result = {"answer": f"ERROR: {e}", "retrieved_files": [], "latency_ms": 0.0}

        # Compute metrics
        print("  Computing metrics...")
        record = evaluate_pair(qa, baseline_result, advanced_result, settings, skip_llm_eval)
        records.append(record)

        # Print answers
        print("\n  📋 Baseline Answer:")
        baseline_answer = baseline_result["answer"][:300] if baseline_result["answer"] else "(empty)"
        print(f"    {baseline_answer}{'...' if len(baseline_result.get('answer', '')) > 300 else ''}")

        print("\n  📋 Advanced Answer:")
        advanced_answer = advanced_result["answer"][:300] if advanced_result["answer"] else "(empty)"
        print(f"    {advanced_answer}{'...' if len(advanced_result.get('answer', '')) > 300 else ''}")

        print(
            f"\n  Recall: baseline={record['baseline']['recall_at_k']:.2f} "
            f"advanced={record['advanced']['recall_at_k']:.2f}"
        )
        if not skip_llm_eval:
            print(
                f"  Faithfulness: baseline={record['baseline']['faithfulness']['normalized']:.2f} "
                f"advanced={record['advanced']['faithfulness']['normalized']:.2f}"
            )
        print()

        # Write partial results after each pair (crash-safe)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        _write_results(output_path, records, settings, categories, enable_rerank)

    print(f"\nBenchmark complete. Results written to: {output_path}")
    _print_summary(records)


def _write_results(
    output_path: Path,
    records: list[dict],
    settings: Settings,
    categories: list[str] | None,
    enable_rerank: bool,
) -> None:
    payload = {
        "meta": {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "llm_model": settings.llm_model,
            "embedding_model": settings.embedding_model,
            "chroma_collection": settings.chroma_collection,
            "enable_rerank": enable_rerank,
            "categories": categories,
            "total_pairs": len(records),
        },
        "records": records,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def _print_summary(records: list[dict]) -> None:
    """Print aggregate metrics to stdout."""
    def avg(values):
        return sum(values) / len(values) if values else 0.0

    b_recall = avg([r["baseline"]["recall_at_k"] for r in records])
    a_recall = avg([r["advanced"]["recall_at_k"] for r in records])
    b_prec = avg([r["baseline"]["precision_at_k"] for r in records])
    a_prec = avg([r["advanced"]["precision_at_k"] for r in records])
    b_faith = avg([r["baseline"]["faithfulness"]["normalized"] for r in records])
    a_faith = avg([r["advanced"]["faithfulness"]["normalized"] for r in records])
    b_rel = avg([r["baseline"]["relevance"]["normalized"] for r in records])
    a_rel = avg([r["advanced"]["relevance"]["normalized"] for r in records])
    b_res = avg([r["baseline"]["resolution"]["score"] for r in records])
    a_res = avg([r["advanced"]["resolution"]["score"] for r in records])
    b_lat = avg([r["baseline"]["latency_ms"] for r in records])
    a_lat = avg([r["advanced"]["latency_ms"] for r in records])

    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    print(f"{'Metric':<28} {'Baseline':>10} {'Advanced':>10} {'Delta':>10}")
    print("-"*60)
    print(f"{'Retrieval Recall@5':<28} {b_recall:>9.1%} {a_recall:>9.1%} {a_recall-b_recall:>+9.1%}")
    print(f"{'Retrieval Precision@5':<28} {b_prec:>9.1%} {a_prec:>9.1%} {a_prec-b_prec:>+9.1%}")
    print(f"{'Faithfulness':<28} {b_faith:>9.1%} {a_faith:>9.1%} {a_faith-b_faith:>+9.1%}")
    print(f"{'Relevance':<28} {b_rel:>9.1%} {a_rel:>9.1%} {a_rel-b_rel:>+9.1%}")
    print(f"{'Resolution Rate':<28} {b_res:>9.1%} {a_res:>9.1%} {a_res-b_res:>+9.1%}")
    print(f"{'Avg Latency (ms)':<28} {b_lat:>9.0f} {a_lat:>9.0f} {a_lat-b_lat:>+9.0f}")
    print("="*60)


def main():
    parser = argparse.ArgumentParser(
        description="Benchmark baseline vs. advanced RAG systems"
    )
    parser.add_argument(
        "--subset",
        nargs="+",
        choices=ALL_CATEGORIES,
        default=None,
        help="Run only these categories (default: all)",
    )
    parser.add_argument(
        "--skip-llm-eval",
        action="store_true",
        help="Skip LLM judge metrics (retrieval metrics only, much faster)",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output JSON file path (default: evaluation/results/benchmark_TIMESTAMP.json)",
    )
    parser.add_argument(
        "--enable-rerank",
        action="store_true",
        help="Enable CrossEncoder reranking in the advanced system",
    )
    args = parser.parse_args()

    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    default_output = RESULTS_DIR / f"benchmark_{timestamp}.json"
    output_path = Path(args.output) if args.output else default_output

    run_benchmark(
        categories=args.subset,
        skip_llm_eval=args.skip_llm_eval,
        output_path=output_path,
        enable_rerank=args.enable_rerank,
    )


if __name__ == "__main__":
    main()

"""Generate a markdown comparison report from benchmark results JSON.

Usage:
    uv run python -m evaluation.report evaluation/results/benchmark_TIMESTAMP.json
    uv run python -m evaluation.report evaluation/results/benchmark_TIMESTAMP.json --output report.md
"""

import argparse
import json
import statistics
import sys
from pathlib import Path


def load_results(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def compute_stats(records: list[dict]) -> dict:
    """Compute aggregate and per-category statistics."""

    def avg(values):
        return sum(values) / len(values) if values else 0.0

    def p50(values):
        return statistics.median(values) if values else 0.0

    def p95(values):
        if not values:
            return 0.0
        return statistics.quantiles(values, n=20)[18]  # 95th percentile

    def extract(records, system, field, subfield=None):
        result = []
        for r in records:
            val = r[system][field]
            if subfield:
                val = val[subfield]
            result.append(val)
        return result

    # Overall stats
    overall = {
        "baseline": {
            "recall": avg(extract(records, "baseline", "recall_at_k")),
            "precision": avg(extract(records, "baseline", "precision_at_k")),
            "faithfulness": avg(extract(records, "baseline", "faithfulness", "normalized")),
            "relevance": avg(extract(records, "baseline", "relevance", "normalized")),
            "resolution": avg(extract(records, "baseline", "resolution", "score")),
            "latency_p50": p50(extract(records, "baseline", "latency_ms")),
            "latency_p95": p95(extract(records, "baseline", "latency_ms")),
        },
        "advanced": {
            "recall": avg(extract(records, "advanced", "recall_at_k")),
            "precision": avg(extract(records, "advanced", "precision_at_k")),
            "faithfulness": avg(extract(records, "advanced", "faithfulness", "normalized")),
            "relevance": avg(extract(records, "advanced", "relevance", "normalized")),
            "resolution": avg(extract(records, "advanced", "resolution", "score")),
            "latency_p50": p50(extract(records, "advanced", "latency_ms")),
            "latency_p95": p95(extract(records, "advanced", "latency_ms")),
        },
    }

    # Per-category stats
    categories = sorted({r["category"] for r in records})
    by_category = {}
    for cat in categories:
        cat_records = [r for r in records if r["category"] == cat]
        by_category[cat] = {
            "n": len(cat_records),
            "baseline": {
                "recall": avg(extract(cat_records, "baseline", "recall_at_k")),
                "precision": avg(extract(cat_records, "baseline", "precision_at_k")),
                "faithfulness": avg(extract(cat_records, "baseline", "faithfulness", "normalized")),
                "resolution": avg(extract(cat_records, "baseline", "resolution", "score")),
            },
            "advanced": {
                "recall": avg(extract(cat_records, "advanced", "recall_at_k")),
                "precision": avg(extract(cat_records, "advanced", "precision_at_k")),
                "faithfulness": avg(extract(cat_records, "advanced", "faithfulness", "normalized")),
                "resolution": avg(extract(cat_records, "advanced", "resolution", "score")),
            },
        }

    return {"overall": overall, "by_category": by_category}


def format_delta(a: float, b: float, pct: bool = True) -> str:
    delta = a - b
    if pct:
        return f"{delta:+.1%}"
    return f"{delta:+.0f}"


def generate_report(results: dict) -> str:
    meta = results["meta"]
    records = results["records"]
    stats = compute_stats(records)
    ov = stats["overall"]
    b = ov["baseline"]
    a = ov["advanced"]

    lines = []
    lines.append("## Benchmark Results\n")
    lines.append(f"**Date:** {meta['timestamp']}")
    lines.append(f"**Model:** {meta['llm_model']}  |  **Embeddings:** {meta['embedding_model']}")
    lines.append(f"**Collection:** {meta['chroma_collection']}  |  **Rerank:** {meta['enable_rerank']}")
    lines.append(f"**QA Pairs:** {meta['total_pairs']}")
    lines.append("")

    lines.append("### Overall Metrics\n")
    lines.append("| Metric | Baseline | Advanced | Delta |")
    lines.append("|--------|----------|----------|-------|")
    lines.append(f"| Retrieval Recall@5    | {b['recall']:.1%} | {a['recall']:.1%} | {format_delta(a['recall'], b['recall'])} |")
    lines.append(f"| Retrieval Precision@5 | {b['precision']:.1%} | {a['precision']:.1%} | {format_delta(a['precision'], b['precision'])} |")
    lines.append(f"| Answer Faithfulness   | {b['faithfulness']:.1%} | {a['faithfulness']:.1%} | {format_delta(a['faithfulness'], b['faithfulness'])} |")
    lines.append(f"| Answer Relevance      | {b['relevance']:.1%} | {a['relevance']:.1%} | {format_delta(a['relevance'], b['relevance'])} |")
    lines.append(f"| Resolution Rate       | {b['resolution']:.1%} | {a['resolution']:.1%} | {format_delta(a['resolution'], b['resolution'])} |")
    lines.append(f"| Latency p50 (ms)      | {b['latency_p50']:.0f} | {a['latency_p50']:.0f} | {format_delta(a['latency_p50'], b['latency_p50'], pct=False)} |")
    lines.append(f"| Latency p95 (ms)      | {b['latency_p95']:.0f} | {a['latency_p95']:.0f} | {format_delta(a['latency_p95'], b['latency_p95'], pct=False)} |")
    lines.append("")

    lines.append("### Per-Category Breakdown\n")
    lines.append("| Category | n | B Recall | A Recall | B Faithfulness | A Faithfulness | B Resol | A Resol |")
    lines.append("|----------|---|----------|----------|----------------|----------------|---------|---------|")
    for cat, cstats in stats["by_category"].items():
        cb = cstats["baseline"]
        ca = cstats["advanced"]
        lines.append(
            f"| {cat} | {cstats['n']} "
            f"| {cb['recall']:.1%} | {ca['recall']:.1%} "
            f"| {cb['faithfulness']:.1%} | {ca['faithfulness']:.1%} "
            f"| {cb['resolution']:.1%} | {ca['resolution']:.1%} |"
        )
    lines.append("")

    lines.append("### Notable Examples\n")
    # Best and worst improvements by recall
    improvements = sorted(
        records,
        key=lambda r: r["advanced"]["recall_at_k"] - r["baseline"]["recall_at_k"],
        reverse=True,
    )
    if improvements:
        best = improvements[0]
        lines.append(f"**Biggest recall improvement:** `{best['id']}` ({best['category']})")
        lines.append(f"> {best['question'][:120]}")
        lines.append(f"> Baseline recall: {best['baseline']['recall_at_k']:.2f} → Advanced: {best['advanced']['recall_at_k']:.2f}")
        lines.append("")

        worst = improvements[-1]
        if worst["baseline"]["recall_at_k"] > worst["advanced"]["recall_at_k"]:
            lines.append(f"**Biggest recall regression:** `{worst['id']}` ({worst['category']})")
            lines.append(f"> {worst['question'][:120]}")
            lines.append(
                f"> Baseline recall: {worst['baseline']['recall_at_k']:.2f} → "
                f"Advanced: {worst['advanced']['recall_at_k']:.2f}"
            )
            lines.append("")

    lines.append("---")
    lines.append("*Generated by `evaluation/report.py`*")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Generate markdown report from benchmark results JSON"
    )
    parser.add_argument("results_file", help="Path to benchmark results JSON")
    parser.add_argument(
        "--output",
        default=None,
        help="Write report to this file (default: print to stdout)",
    )
    args = parser.parse_args()

    results_path = Path(args.results_file)
    if not results_path.exists():
        print(f"Error: {results_path} does not exist", file=sys.stderr)
        sys.exit(1)

    results = load_results(results_path)
    report = generate_report(results)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(report, encoding="utf-8")
        print(f"Report written to: {output_path}")
    else:
        print(report)


if __name__ == "__main__":
    main()

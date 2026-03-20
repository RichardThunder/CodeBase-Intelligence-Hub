# 并行 LLM 与基线模型基准测试指南

## 📊 基准测试策略

### 1. 测试维度

```
┌─────────────────────────────────────────────────────┐
│  并行 LLM vs 基线基准测试                            │
├─────────────────────────────────────────────────────┤
│                                                     │
│  A. 性能指标                                        │
│     ├─ 延迟 (Latency)                              │
│     ├─ 吞吐量 (Throughput)                         │
│     ├─ 并发能力 (Concurrency)                      │
│     └─ 资源使用 (Resource Usage)                   │
│                                                     │
│  B. 质量指标                                        │
│     ├─ 准确性 (Accuracy)                           │
│     ├─ 一致性 (Consistency)                        │
│     └─ 可靠性 (Reliability)                        │
│                                                     │
│  C. 成本指标                                        │
│     ├─ API 调用次数                                 │
│     ├─ Token 消耗                                   │
│     └─ 成本效益 (Cost per query)                   │
│                                                     │
└─────────────────────────────────────────────────────┘
```

---

## 🏗️ 实现框架

### 第一步：设计实验

```python
# 1. 基线系统 (Baseline)
# ─────────────────────
Sequential Execution:
  Query → Orchestrator (LLM)
       → Retrieval (LLM)
       → Analysis (LLM)
       → Synthesizer (LLM)

总耗时: T = T_orch + T_retr + T_ana + T_synt
例如: 3s + 10s + 10s + 20s = 43s

# 2. 并行系统 (Parallel)
# ──────────────────────
Parallel Execution:
  Query → Orchestrator (LLM)
       ↓
       ├─→ Retrieval (LLM)  ┐
       ├─→ Analysis (LLM)   ├─ 并行执行
       └─→ Code (LLM)       ┘
       ↓
       → Synthesizer (LLM)

总耗时: T = T_orch + max(T_retr, T_ana, T_code) + T_synt
例如: 3s + max(10s, 10s, 5s) + 20s = 33s

加速比: 43s / 33s = 1.30x (30% 改进)
```

---

## 📈 实现代码框架

### 方案 A: 简单延迟测试

```python
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

class LatencyBenchmark:
    """简单的延迟基准测试"""

    def benchmark_sequential(self, tasks: list[Callable]) -> dict:
        """顺序执行基准"""
        start = time.perf_counter()
        results = []

        for task in tasks:
            result = task()
            results.append(result)

        latency = (time.perf_counter() - start) * 1000
        return {
            "latency_ms": latency,
            "results": results,
            "model": "sequential"
        }

    def benchmark_parallel(self, tasks: list[Callable]) -> dict:
        """并行执行基准"""
        start = time.perf_counter()

        with ThreadPoolExecutor(max_workers=len(tasks)) as executor:
            futures = [executor.submit(task) for task in tasks]
            results = [f.result() for f in futures]

        latency = (time.perf_counter() - start) * 1000
        return {
            "latency_ms": latency,
            "results": results,
            "model": "parallel"
        }

    def compare(self, tasks: list[Callable]) -> dict:
        """对比两种方式"""
        sequential = self.benchmark_sequential(tasks)
        parallel = self.benchmark_parallel(tasks)

        speedup = sequential["latency_ms"] / parallel["latency_ms"]
        improvement = (1 - parallel["latency_ms"] / sequential["latency_ms"]) * 100

        return {
            "sequential_ms": sequential["latency_ms"],
            "parallel_ms": parallel["latency_ms"],
            "speedup": speedup,
            "improvement_pct": improvement
        }

# 使用示例
# ────────
benchmark = LatencyBenchmark()

# 定义要并行执行的任务
tasks = [
    lambda: llm_orchestrator(query),      # ~3s
    lambda: llm_retrieval(query),         # ~10s
    lambda: llm_analysis(query),          # ~10s
    lambda: llm_code(query),              # ~5s
]

results = benchmark.compare(tasks)
print(f"顺序: {results['sequential_ms']:.0f}ms")
print(f"并行: {results['parallel_ms']:.0f}ms")
print(f"加速: {results['speedup']:.2f}x")
```

---

### 方案 B: 完整的基准测试框架

```python
import time
import json
from dataclasses import dataclass
from typing import List, Dict
from concurrent.futures import ThreadPoolExecutor, as_completed

@dataclass
class BenchmarkResult:
    """单个查询的基准结果"""
    query_id: str
    question: str
    baseline_ms: float
    parallel_ms: float
    speedup: float
    baseline_answer: str
    parallel_answer: str
    baseline_recall: float
    parallel_recall: float
    accuracy_match: bool  # 两个系统是否返回相同答案

class ParallelBenchmark:
    """完整的并行基准测试框架"""

    def __init__(self, baseline_system, parallel_system, dataset):
        self.baseline = baseline_system
        self.parallel = parallel_system
        self.dataset = dataset

    def run_query(self, system, question: str) -> Dict:
        """运行单个查询"""
        start = time.perf_counter()
        result = system.invoke(question)
        latency = (time.perf_counter() - start) * 1000

        return {
            "answer": result.get("answer", ""),
            "latency_ms": latency,
            "retrieved_files": result.get("retrieved_files", []),
        }

    def benchmark_query(self, query_id: str, question: str) -> BenchmarkResult:
        """基准测试单个查询（并行运行两个系统）"""

        # 并行执行两个系统
        with ThreadPoolExecutor(max_workers=2) as executor:
            baseline_future = executor.submit(self.run_query, self.baseline, question)
            parallel_future = executor.submit(self.run_query, self.parallel, question)

            baseline_result = baseline_future.result()
            parallel_result = parallel_future.result()

        # 计算指标
        speedup = baseline_result["latency_ms"] / parallel_result["latency_ms"]
        accuracy_match = baseline_result["answer"][:50] == parallel_result["answer"][:50]

        return BenchmarkResult(
            query_id=query_id,
            question=question,
            baseline_ms=baseline_result["latency_ms"],
            parallel_ms=parallel_result["latency_ms"],
            speedup=speedup,
            baseline_answer=baseline_result["answer"],
            parallel_answer=parallel_result["answer"],
            baseline_recall=self._calculate_recall(baseline_result),
            parallel_recall=self._calculate_recall(parallel_result),
            accuracy_match=accuracy_match,
        )

    def run_full_benchmark(self) -> List[BenchmarkResult]:
        """运行完整基准测试"""
        results = []

        for i, qa in enumerate(self.dataset, 1):
            print(f"[{i}/{len(self.dataset)}] {qa.id}")

            result = self.benchmark_query(qa.id, qa.question)
            results.append(result)

            print(f"  Baseline:  {result.baseline_ms:7.0f}ms")
            print(f"  Parallel:  {result.parallel_ms:7.0f}ms")
            print(f"  Speedup:   {result.speedup:6.2f}x {'✅' if result.speedup > 1 else '⚠️'}")
            print()

        return results

    def generate_report(self, results: List[BenchmarkResult]) -> Dict:
        """生成基准测试报告"""

        avg_baseline = sum(r.baseline_ms for r in results) / len(results)
        avg_parallel = sum(r.parallel_ms for r in results) / len(results)
        avg_speedup = sum(r.speedup for r in results) / len(results)

        accuracy_matches = sum(1 for r in results if r.accuracy_match) / len(results)

        return {
            "total_queries": len(results),
            "avg_baseline_ms": avg_baseline,
            "avg_parallel_ms": avg_parallel,
            "avg_speedup": avg_speedup,
            "improvement_pct": (1 - avg_parallel / avg_baseline) * 100,
            "accuracy_match_rate": accuracy_matches,
            "details": [
                {
                    "query_id": r.query_id,
                    "baseline_ms": r.baseline_ms,
                    "parallel_ms": r.parallel_ms,
                    "speedup": r.speedup,
                }
                for r in results
            ]
        }

    def _calculate_recall(self, result: Dict) -> float:
        # 实现你的 recall 计算逻辑
        return 1.0

# 使用示例
benchmark = ParallelBenchmark(
    baseline_system=baseline_graph,
    parallel_system=parallel_graph,
    dataset=DATASET
)

results = benchmark.run_full_benchmark()
report = benchmark.generate_report(results)

print("=" * 60)
print("📊 基准测试报告")
print("=" * 60)
print(f"平均基线延迟:    {report['avg_baseline_ms']:.0f}ms")
print(f"平均并行延迟:    {report['avg_parallel_ms']:.0f}ms")
print(f"平均加速比:      {report['avg_speedup']:.2f}x")
print(f"性能提升:        {report['improvement_pct']:+.1f}%")
print(f"准确性匹配率:    {report['accuracy_match_rate']:.1%}")
```

---

### 方案 C: 并发负载测试

```python
import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import List

class ConcurrencyBenchmark:
    """并发负载基准测试"""

    def __init__(self, system, dataset: List[str]):
        self.system = system
        self.dataset = dataset

    def benchmark_concurrent_load(self, max_concurrent: int = 5) -> Dict:
        """测试并发处理能力"""

        start = time.perf_counter()

        with ThreadPoolExecutor(max_workers=max_concurrent) as executor:
            futures = [
                executor.submit(self.system.invoke, query)
                for query in self.dataset
            ]

            results = []
            for future in as_completed(futures):
                results.append(future.result())

        total_time = (time.perf_counter() - start) * 1000

        return {
            "total_queries": len(self.dataset),
            "total_time_ms": total_time,
            "avg_latency_ms": total_time / len(self.dataset),
            "throughput_qps": len(self.dataset) / (total_time / 1000),
            "concurrent_workers": max_concurrent,
        }

# 使用示例
concurrency_benchmark = ConcurrencyBenchmark(parallel_system, test_queries)

for num_workers in [1, 2, 4, 8]:
    concurrency_benchmark.benchmark_concurrent_load(max_concurrent=num_workers)
```

---

## 📋 测试清单

### 在实施基准测试时需要验证：

- [ ] **隔离**: 每个测试运行在独立环境
- [ ] **预热**: 第一个查询前进行 JIT 编译优化
- [ ] **重复**: 每个查询运行多次以减少噪声
- [ ] **统计**: 计算均值、中位数、标准差
- [ ] **日志**: 记录所有原始数据供事后分析
- [ ] **可重现**: 使用固定种子确保结果可复现
- [ ] **准确性**: 验证两个系统返回等效结果
- [ ] **资源**: 监控 CPU、内存、网络使用

---

## 🎯 预期结果

### 基于当前架构的预期性能提升：

```
场景 1: 简单查询 (代码查找)
  基线:   ~12s (1x Retrieval + 1x LLM)
  并行:   ~12s (无改进，因为只有1个并行任务)
  加速:   1.0x ❌

场景 2: 复杂查询 (代码分析 + 分析)
  基线:   ~35s (Orch + Retr + Ana + Synt)
  并行:   ~28s (Orch + max(Retr, Ana) + Synt)
  加速:   1.25x ✅

场景 3: 完整查询 (所有智能体)
  基线:   ~45s (Orch + Retr + Ana + Code + Synt)
  并行:   ~30s (Orch + max(Retr, Ana, Code) + Synt)
  加速:   1.50x ✅ ⭐

场景 4: 高并发 (10 并发查询)
  基线:   无法处理 (顺序执行)
  并行:   可处理，吞吐量 3-5 QPS
  加速:   显著 ✅✅✅
```

---

## 🚀 优化建议

| 优化 | 潜在收益 | 实现难度 | 优先级 |
|------|---------|---------|--------|
| 并行化智能体执行 | 30-40% | 中 | 🔴 高 |
| 缓存 MultiQuery 结果 | 20-30% | 低 | 🟡 中 |
| 轻量级 LLM 用于 Orch | 15-20% | 中 | 🟡 中 |
| 批量处理查询 | 40-50% | 高 | 🟢 低 |
| 智能提前停止 | 25-35% | 高 | 🟢 低 |

---

## 📝 运行命令

```bash
# 1. 基线系统基准
uv run python -m evaluation.benchmark --skip-llm-eval

# 2. 并行系统基准
uv run python -m evaluation.benchmark_parallel

# 3. 并发负载测试
uv run python -m evaluation.concurrency_benchmark

# 4. 生成对比报告
uv run python scripts/generate_benchmark_report.py
```

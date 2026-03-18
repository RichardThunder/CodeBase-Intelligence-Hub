#!/usr/bin/env python
"""
Test multi-threaded ingestion performance.

Usage:
  uv run python scripts/test_ingest_multithread.py
"""

import time
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import Settings
from retrieval.ingestion import ingest_repo


def main():
    """Test ingestion with different thread counts."""
    settings = Settings()
    test_repo = "."  # Ingest current directory

    print("=" * 60)
    print("🧵 Multi-Threaded Ingestion Performance Test")
    print("=" * 60)

    # Test with different thread counts
    thread_counts = [1, 2, 4, 8]

    for num_threads in thread_counts:
        print(f"\n🔄 Testing with {num_threads} thread(s)...")
        start_time = time.time()

        try:
            chunks_created = ingest_repo(
                test_repo,
                settings,
                use_parser=True,
                num_threads=num_threads,
                batch_size=100,
            )
            elapsed = time.time() - start_time

            print(f"\n  ⏱️  Time: {elapsed:.2f}s")
            print(f"  📊 Throughput: {chunks_created / elapsed:.1f} chunks/sec")

        except Exception as e:
            print(f"  ❌ Error: {e}")

    print("\n" + "=" * 60)
    print("✅ Performance test complete")
    print("=" * 60)


if __name__ == "__main__":
    main()

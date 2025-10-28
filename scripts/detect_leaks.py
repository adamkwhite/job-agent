#!/usr/bin/env python3
"""
Memory leak detection using tracemalloc
Shows you EXACTLY where memory is allocated
"""

import sys
import tracemalloc
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


def run_with_memory_profiling():
    """Run processor with memory profiling"""

    # Start tracing
    tracemalloc.start()

    # Take snapshot before
    snapshot1 = tracemalloc.take_snapshot()

    # Import and run your processor
    from processor_v2 import JobProcessorV2

    processor = JobProcessorV2()

    # Simulate processing (without actual IMAP fetch)
    print("Processing jobs (test mode)...")
    stats = processor.run(fetch_emails=False)
    print(f"Stats: {stats}")

    # Take snapshot after
    snapshot2 = tracemalloc.take_snapshot()

    # Compare snapshots
    top_stats = snapshot2.compare_to(snapshot1, "lineno")

    print("\n" + "=" * 70)
    print("TOP 10 MEMORY ALLOCATIONS:")
    print("=" * 70)

    for stat in top_stats[:10]:
        print(f"{stat.size_diff / 1024:.1f} KB - {stat.traceback.format()[0]}")

    # Get current memory usage
    current, peak = tracemalloc.get_traced_memory()
    print(f"\nCurrent memory: {current / 1024 / 1024:.1f} MB")
    print(f"Peak memory: {peak / 1024 / 1024:.1f} MB")

    tracemalloc.stop()


def demonstrate_leak():
    """Demonstrate what a memory leak looks like"""
    print("\n" + "=" * 70)
    print("DEMONSTRATING A MEMORY LEAK:")
    print("=" * 70)

    tracemalloc.start()

    # Simulate a leaky cache
    leak_cache = []

    for _i in range(1000):
        # Simulate storing large email content
        large_object = "X" * 10000  # 10KB string
        leak_cache.append(large_object)  # ❌ Never cleared!

    current, peak = tracemalloc.get_traced_memory()
    print("\nAfter 1000 iterations:")
    print(f"Memory used: {current / 1024 / 1024:.1f} MB")
    print("Expected: ~10 MB (1000 × 10KB)")

    # This is a leak - leak_cache holds all objects in memory

    tracemalloc.stop()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--demo-leak", action="store_true", help="Demonstrate a memory leak")
    args = parser.parse_args()

    if args.demo_leak:
        demonstrate_leak()
    else:
        run_with_memory_profiling()

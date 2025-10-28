#!/usr/bin/env python3
"""
Memory monitoring script - Run your processor and watch for leaks
Usage: python scripts/monitor_memory.py
"""

import os
import time

import psutil


def monitor_process(pid=None):
    """Monitor memory usage of a process"""
    if pid is None:
        pid = os.getpid()

    process = psutil.Process(pid)

    print("Monitoring memory usage (Ctrl+C to stop)...")
    print(f"{'Time (s)':<10} {'RSS (MB)':<12} {'VMS (MB)':<12} {'% Memory':<10}")
    print("-" * 50)

    start_time = time.time()
    baseline_rss = None

    try:
        while True:
            mem_info = process.memory_info()
            rss_mb = mem_info.rss / 1024 / 1024  # Resident Set Size
            vms_mb = mem_info.vms / 1024 / 1024  # Virtual Memory Size
            mem_percent = process.memory_percent()

            if baseline_rss is None:
                baseline_rss = rss_mb

            elapsed = time.time() - start_time
            growth = rss_mb - baseline_rss

            print(
                f"{elapsed:<10.1f} {rss_mb:<12.1f} {vms_mb:<12.1f} {mem_percent:<10.2f} (+{growth:.1f} MB)"
            )

            # Alert if memory grows >100MB from baseline
            if growth > 100:
                print(f"⚠️  WARNING: Memory grew by {growth:.1f} MB!")

            time.sleep(5)  # Check every 5 seconds

    except KeyboardInterrupt:
        print("\nMonitoring stopped")
        print(f"Total memory growth: {rss_mb - baseline_rss:.1f} MB")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Monitor process memory")
    parser.add_argument("--pid", type=int, help="Process ID to monitor (default: self)")
    args = parser.parse_args()

    monitor_process(args.pid)

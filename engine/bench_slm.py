"""Latency benchmark for the SLM classifier. Run from engine/: python bench_slm.py"""
import statistics
import time

from pipeline import get_classifier

PROMPTS = {
    "short": "What is the capital of France?",
    "medium": "Summarize the following article about renewable energy policy. " * 8,
    "long": "Explain the history of the Roman Empire in detail. " * 80,
}
WARMUP, RUNS = 5, 50


def main():
    t0 = time.perf_counter()
    stage = get_classifier()
    print(f"model load: {time.perf_counter() - t0:.2f}s (one-time, at server start)\n")
    print(f"{'prompt':8} {'p50 ms':>8} {'p95 ms':>8} {'max ms':>8}")
    for name, prompt in PROMPTS.items():
        for _ in range(WARMUP):
            stage.process(prompt)
        times = []
        for _ in range(RUNS):
            t = time.perf_counter()
            stage.process(prompt)
            times.append((time.perf_counter() - t) * 1000)
        times.sort()
        print(f"{name:8} {statistics.median(times):8.1f} {times[int(RUNS * 0.95) - 1]:8.1f} {times[-1]:8.1f}")


if __name__ == "__main__":
    main()

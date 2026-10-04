"""Measure full script runtime and enforce an optional median-time budget."""

import argparse
import hashlib
import json
import math
import os
import platform
import shutil
import statistics
import subprocess
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log", type=Path, default=ROOT / "space_missions.log")
    parser.add_argument("--expected-code", default="XRT-421-ZQP")
    parser.add_argument("--warmups", type=int, default=5)
    parser.add_argument("--runs", type=int, default=50)
    parser.add_argument("--max-median-ms", type=float, default=200)
    parser.add_argument("--output", type=Path, default=Path("benchmark-results.json"))
    args = parser.parse_args()
    if args.runs < 1 or args.warmups < 0:
        parser.error("runs must be positive and warmups must be nonnegative")
    if not math.isfinite(args.max_median_ms) or args.max_median_ms <= 0:
        parser.error("max-median-ms must be finite and positive")

    script = ROOT / "lcm_mars.sh"
    command = ["sh", str(script), str(args.log.resolve())]
    expected = (args.expected_code + "\n").encode()
    samples = []
    for iteration in range(args.warmups + args.runs):
        start = time.perf_counter_ns()
        result = subprocess.run(command, capture_output=True, timeout=10, check=False)
        elapsed_ms = (time.perf_counter_ns() - start) / 1_000_000
        if result.returncode != 0 or result.stdout != expected or result.stderr:
            raise SystemExit(
                f"Run {iteration + 1} failed: exit={result.returncode}, "
                f"stdout={result.stdout!r}, stderr={result.stderr!r}"
            )
        if iteration >= args.warmups:
            samples.append(elapsed_ms)

    median = statistics.median(samples)
    version = subprocess.run(
        ["awk", "-W", "version"], capture_output=True, text=True, check=True, timeout=10
    )
    raw = args.log.read_bytes()
    report = {
        "commit": os.environ.get("GITHUB_SHA"),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "awk_path": str(Path(shutil.which("awk")).resolve()),
        "awk_version": (version.stdout + version.stderr).splitlines()[0],
        "shell_path": str(Path(shutil.which("sh")).resolve()),
        "input_bytes": len(raw),
        "input_lines": len(raw.splitlines()),
        "input_sha256": hashlib.sha256(raw).hexdigest(),
        "script_sha256": hashlib.sha256(script.read_bytes()).hexdigest(),
        "warmups": args.warmups,
        "runs": args.runs,
        "expected_code": args.expected_code,
        "median_ms": median,
        "mean_ms": statistics.mean(samples),
        "p95_ms": sorted(samples)[math.ceil(0.95 * len(samples)) - 1],
        "min_ms": min(samples),
        "max_ms": max(samples),
        "max_median_ms": args.max_median_ms,
        "passed": median <= args.max_median_ms,
        "samples_ms": samples,
    }
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    summary = (
        "## Mission performance\n\n"
        f"Interpreter: `{report['awk_version']}`. "
        f"{args.runs} measured runs after {args.warmups} warmups.\n\n"
        "| Metric | Milliseconds |\n| --- | ---: |\n"
        f"| Median | {median:.2f} |\n"
        f"| Mean | {report['mean_ms']:.2f} |\n"
        f"| P95 | {report['p95_ms']:.2f} |\n"
        f"| Fastest | {report['min_ms']:.2f} |\n"
        f"| Slowest | {report['max_ms']:.2f} |\n"
        f"| Median limit | {args.max_median_ms:.2f} |\n\n"
        "Includes shell and awk startup and output capture. Warm-cache elapsed times; "
        "shared-runner load can affect results. Every run checks the full output and exit status.\n"
    )
    print(summary)
    if summary_path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary_path, "a", encoding="utf-8") as target:
            target.write(summary)
    if not report["passed"]:
        raise SystemExit(f"Median {median:.2f} ms exceeds {args.max_median_ms:.2f} ms")


if __name__ == "__main__":
    main()

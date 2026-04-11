#!/usr/bin/env bash
# Measure warm startup latency for the installed phil binary.
#
# Usage:
#   scripts/bench.sh              # uses 'phil' on PATH
#   scripts/bench.sh /path/to/phil
#
# Outputs p50 and p95 over 12 warm runs for three representative invocations.
# Run before and after any startup optimization to capture before/after.
set -euo pipefail

PHIL="${1:-phil}"

if ! command -v "$PHIL" &>/dev/null && [ ! -x "$PHIL" ]; then
    echo "error: '$PHIL' not found — install with: uv tool install philcalc" >&2
    exit 1
fi

python3 - "$PHIL" <<'EOF'
import subprocess, sys, time

def bench(label, cmd, n=12):
    subprocess.run(cmd, capture_output=True)  # warm-up
    results = []
    for _ in range(n):
        t0 = time.perf_counter()
        subprocess.run(cmd, capture_output=True)
        results.append(time.perf_counter() - t0)
    results.sort()
    p50 = results[n // 2] * 1000
    p95 = results[min(int(n * 0.95), n - 1)] * 1000
    print(f"  {label:<28}  p50={p50:5.0f}ms  p95={p95:5.0f}ms")

phil = sys.argv[1]
print(f"[bench] {phil}")
bench(":version",    [phil, ":version"])
bench("2+2",         [phil, "2+2"])
bench("d(x^2, x)",  [phil, "d(x^2, x)"])
bench("solve(x^2-4, x)", [phil, "solve(x^2-4, x)"])
EOF

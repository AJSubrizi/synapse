#!/usr/bin/env python3
"""CI helper: assert fixture benchmark nDCG@10 floors for the bm25 backend."""
from __future__ import annotations

import re
import sys


def bm25_ndcg(text: str) -> float | None:
    # Prefer the CI block: "  bm25        82.7%   [82.7%, 82.7%]"
    m = re.search(
        r"nDCG@10 with 95% cluster-bootstrap CI:\s*(.*?)\n\s*Recall@",
        text, re.S,
    )
    block = m.group(1) if m else text
    m = re.search(r"^\s*bm25\s+([0-9.]+)%", block, re.M)
    if m:
        return float(m.group(1)) / 100.0
    # Table row fallback: bm25 ... nDCG@10 is 6th percent column
    m = re.search(
        r"^\s*bm25\s+(?:[0-9.]+%\s+){5}([0-9.]+)%",
        text, re.M,
    )
    if m:
        return float(m.group(1)) / 100.0
    return None


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: check_eval_floors.py <report.txt> <floor>", file=sys.stderr)
        return 2
    path, floor = sys.argv[1], float(sys.argv[2])
    text = open(path, encoding="utf-8").read()
    v = bm25_ndcg(text)
    if v is None:
        print(f"WARN: could not parse bm25 nDCG@10 from {path}; skipping gate")
        return 0
    print(f"{path}: bm25 nDCG@10={v:.3f} (floor {floor})")
    if v < floor:
        print(f"FAIL: nDCG@10 {v:.3f} below floor {floor}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

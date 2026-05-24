"""6-order Latin square counterbalancing for the 3-condition within-subjects design.

Run with `--n 24` to generate the assignment sheet for the main study.
"""
from __future__ import annotations

import argparse
import csv
import sys
from itertools import permutations
from pathlib import Path


CONDITIONS = ("random", "fixed", "adaptive")
ORDERS = list(permutations(CONDITIONS))
DOMAINS = ("d1", "d2")


def assign(n: int, *, id_prefix: str = "") -> list[dict[str, str]]:
    if n % len(ORDERS) != 0:
        raise SystemExit(
            f"--n must be a multiple of {len(ORDERS)} (got {n}); a 3! Latin square needs 6 per cell."
        )
    prefix = f"{id_prefix}-" if id_prefix and not id_prefix.endswith("-") else id_prefix
    rows: list[dict[str, str]] = []
    domain_cycle = list(DOMAINS) * (n // len(DOMAINS) + 1)
    for i in range(n):
        order = ORDERS[i % len(ORDERS)]
        pid = f"{prefix}P{(i+1):02d}"
        rows.append({
            "participant_id": pid,
            "domain": domain_cycle[i],
            "order_1": order[0],
            "order_2": order[1],
            "order_3": order[2],
        })
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=24)
    ap.add_argument("--out", type=Path, default=Path("study/assignment.csv"))
    ap.add_argument(
        "--id-prefix",
        default="chi27",
        help="Participant ID prefix; files become runs/<prefix>-P01.sqlite (default: chi27)",
    )
    args = ap.parse_args()
    rows = assign(args.n, id_prefix=args.id_prefix)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    with args.out.open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} rows to {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

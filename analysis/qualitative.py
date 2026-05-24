"""Tabulate qualitative coder annotations and compute Cohen's kappa.

Input: `analysis/qualitative_codes/<participant>_<coder>.csv` with columns
  segment_id, codes (comma-separated)

This script:
  - aggregates code counts per participant,
  - computes per-code Cohen's kappa between Coder A and Coder B,
  - writes `analysis/output/qualitative_counts.csv` and `..._kappa.csv`.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parent.parent
CODES_DIR = REPO_ROOT / "analysis" / "qualitative_codes"


def load_codes() -> pd.DataFrame:
    rows = []
    if not CODES_DIR.exists():
        return pd.DataFrame(columns=["participant", "coder", "segment_id", "code"])
    for p in CODES_DIR.glob("*.csv"):
        parts = p.stem.split("_")
        if len(parts) < 2:
            continue
        participant = "_".join(parts[:-1])
        coder = parts[-1]
        df = pd.read_csv(p)
        for _, r in df.iterrows():
            codes = str(r["codes"]).split(",") if pd.notna(r["codes"]) else []
            for c in codes:
                c = c.strip()
                if not c:
                    continue
                rows.append({"participant": participant, "coder": coder, "segment_id": r["segment_id"], "code": c})
    return pd.DataFrame(rows)


def cohens_kappa(a: list[bool], b: list[bool]) -> float:
    n = len(a)
    if n == 0:
        return float("nan")
    po = sum(1 for x, y in zip(a, b) if x == y) / n
    pa1 = sum(a) / n
    pb1 = sum(b) / n
    pe = pa1 * pb1 + (1 - pa1) * (1 - pb1)
    return (po - pe) / (1 - pe) if pe < 1 else float("nan")


def kappa_table(df: pd.DataFrame) -> pd.DataFrame:
    coders = sorted(df["coder"].unique())
    if len(coders) < 2:
        return pd.DataFrame()
    a, b = coders[0], coders[1]
    out = []
    segs = sorted(df["segment_id"].unique())
    codes = sorted(df["code"].unique())
    for code in codes:
        ay = [(s in set(df[(df.coder == a) & (df.code == code)]["segment_id"])) for s in segs]
        by = [(s in set(df[(df.coder == b) & (df.code == code)]["segment_id"])) for s in segs]
        out.append({"code": code, "n_segments": len(segs), "kappa": cohens_kappa(ay, by)})
    return pd.DataFrame(out)


def counts_table(df: pd.DataFrame) -> pd.DataFrame:
    return (
        df.groupby(["participant", "coder", "code"]).size()
          .reset_index(name="count")
          .pivot_table(index=["participant", "code"], columns="coder", values="count", fill_value=0)
          .reset_index()
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="analysis/output")
    args = ap.parse_args()
    df = load_codes()
    out_dir = REPO_ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    if df.empty:
        print(f"No qualitative codes in {CODES_DIR}. Add CSVs once interviews are coded.")
        return 0
    counts_table(df).to_csv(out_dir / "qualitative_counts.csv", index=False)
    kappa_table(df).to_csv(out_dir / "qualitative_kappa.csv", index=False)
    print(f"wrote qualitative outputs to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

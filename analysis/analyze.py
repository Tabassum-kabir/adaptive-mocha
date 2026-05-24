"""Pre-registered analysis pipeline.

For each pre-registered outcome (accuracy, macro-F1, NASA-TLX mean, quiz score,
median dwell time) we fit a linear mixed-effects model:

    outcome ~ condition + (1 | participant)

with `condition` as a 3-level factor (random/fixed/adaptive). We report:

  - Fixed-effect estimates and 95% CIs.
  - Pairwise contrasts (Fixed vs Random; Adaptive vs Fixed; Adaptive vs Random)
    with Holm-Bonferroni adjusted p-values.
  - Within-subject Cohen's d_z for each contrast.

The script is intentionally deterministic and can be re-run as new data is
added. Outputs land in `analysis/output/`.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis.load import load_study, primary_outcome_table  # noqa: E402


OUTCOMES = [
    ("accuracy", "Post-block classifier accuracy on held-out probe set"),
    ("macro_f1", "Macro F1 on held-out probe set"),
    ("mean_raw", "Raw NASA-TLX mean (0-20)"),
    ("quiz_score", "Concept-understanding quiz (0-12)"),
    ("median_dwell_ms", "Median dwell time per label, ms"),
]


def holm_bonferroni(pvals: list[float]) -> list[float]:
    order = sorted(range(len(pvals)), key=lambda i: pvals[i])
    adj = [None] * len(pvals)
    n = len(pvals)
    for rank, i in enumerate(order):
        adj_val = min(1.0, pvals[i] * (n - rank))
        adj[i] = adj_val
    return adj


def cohen_dz(a: np.ndarray, b: np.ndarray) -> float:
    diff = a - b
    sd = np.std(diff, ddof=1)
    return float(np.mean(diff) / sd) if sd > 0 else 0.0


def fit_mixed(df: pd.DataFrame, outcome: str) -> dict:
    df = df.dropna(subset=[outcome, "condition", "participant_id"]).copy()
    df["condition"] = df["condition"].astype(pd.CategoricalDtype(categories=["random", "fixed", "adaptive"], ordered=False))
    md = smf.mixedlm(
        formula=f"{outcome} ~ C(condition, Treatment(reference='random'))",
        data=df,
        groups=df["participant_id"],
    )
    res = md.fit(method="lbfgs", reml=True, disp=False)
    coefs = res.fe_params.to_dict()
    ci = res.conf_int().to_dict("index")
    pvals = res.pvalues.to_dict()
    return {
        "n": int(df.shape[0]),
        "coefs": {k: float(v) for k, v in coefs.items()},
        "ci": {k: [float(v[0]), float(v[1])] for k, v in ci.items()},
        "pvals": {k: float(v) for k, v in pvals.items()},
        "converged": bool(res.converged),
    }


def pairwise_contrasts(df: pd.DataFrame, outcome: str) -> list[dict]:
    df = df.dropna(subset=[outcome, "condition", "participant_id"]).copy()
    wide = df.pivot_table(index="participant_id", columns="condition", values=outcome, aggfunc="mean")
    contrasts = [
        ("fixed", "random"),
        ("adaptive", "fixed"),
        ("adaptive", "random"),
    ]
    rows: list[dict] = []
    raw_p: list[float] = []
    for a, b in contrasts:
        x = wide[a].dropna()
        y = wide[b].dropna()
        common = x.index.intersection(y.index)
        x = x.loc[common].to_numpy()
        y = y.loc[common].to_numpy()
        if len(common) < 3:
            t = np.nan
            p = np.nan
            d = np.nan
        else:
            t_stat, p = stats.ttest_rel(x, y)
            t = float(t_stat)
            d = cohen_dz(x, y)
        rows.append({"contrast": f"{a}-{b}", "n_pairs": int(len(common)),
                     "mean_diff": float(np.mean(x - y)) if len(common) else float("nan"),
                     "t": t, "p_raw": float(p) if not np.isnan(p) else float("nan"),
                     "cohen_dz": d})
        raw_p.append(p if not np.isnan(p) else 1.0)
    adj = holm_bonferroni(raw_p)
    for r, q in zip(rows, adj):
        r["p_holm"] = float(q)
    return rows


def descriptives(df: pd.DataFrame, outcome: str) -> pd.DataFrame:
    g = df.dropna(subset=[outcome]).groupby("condition")[outcome]
    return pd.DataFrame({
        "n": g.count(),
        "mean": g.mean(),
        "sd": g.std(),
        "median": g.median(),
        "q25": g.quantile(0.25),
        "q75": g.quantile(0.75),
    }).reset_index()


def run(tag: str) -> dict:
    data = load_study(tag)
    pot = primary_outcome_table(data)
    out: dict = {"tag": tag, "n_sessions": int(pot.shape[0]),
                 "n_participants": int(pot["participant_id"].nunique())}
    out["primary_outcome_table"] = pot.to_dict(orient="records")
    out["per_outcome"] = {}
    for outcome, label in OUTCOMES:
        if outcome not in pot.columns:
            continue
        desc = descriptives(pot, outcome)
        try:
            model = fit_mixed(pot, outcome)
        except Exception as e:
            model = {"error": str(e)}
        contrasts = pairwise_contrasts(pot, outcome)
        out["per_outcome"][outcome] = {
            "label": label,
            "descriptives": desc.to_dict(orient="records"),
            "mixed_model": model,
            "contrasts": contrasts,
        }
    return out


def pretty_print(report: dict) -> None:
    print(f"\nStudy tag: {report['tag']}")
    print(f"  participants: {report['n_participants']}")
    print(f"  sessions:     {report['n_sessions']}")
    for outcome, block in report["per_outcome"].items():
        print(f"\n  {outcome}  ({block['label']})")
        for row in block["descriptives"]:
            print(f"    {row['condition']:>9s}  n={row['n']:>2d}  M={row['mean']:.3f}  SD={row['sd']:.3f}  Med={row['median']:.3f}")
        for c in block["contrasts"]:
            print(
                f"    contrast {c['contrast']:<18s}  d_z={c['cohen_dz']:+.2f}  "
                f"t={c['t']:+.2f}  p_holm={c['p_holm']:.3f}"
            )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="mainstudy")
    ap.add_argument("--out", default="analysis/output/report.json")
    args = ap.parse_args()
    report = run(args.tag)
    out_path = REPO_ROOT / args.out
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(report, indent=2, default=str), encoding="utf-8")
    pretty_print(report)
    print(f"\nWrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Publication-ready figures for the paper.

Produces, into `analysis/output/figures/`:

  fig1_outcomes.pdf      per-condition strips + means for each primary outcome
  fig2_controller.pdf    cognitive-load trajectory and controller decisions
                          for a representative Adaptive participant
  fig3_tlx_profile.pdf   six-item TLX profile per condition
  fig4_learning_curve.pdf trial-level dwell time across the block by condition
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis.load import load_study, primary_outcome_table  # noqa: E402

CONDITION_ORDER = ["random", "fixed", "adaptive"]
CONDITION_LABELS = {"random": "Random", "fixed": "MOCHA-Fixed", "adaptive": "MOCHA-Adaptive"}
CONDITION_COLORS = {"random": "#9a9a9a", "fixed": "#5277ff", "adaptive": "#ff7a3f"}


def style() -> None:
    sns.set_style("whitegrid")
    plt.rcParams.update({
        "figure.dpi": 160,
        "savefig.dpi": 300,
        "font.size": 10,
        "axes.titlesize": 11,
        "axes.labelsize": 10,
        "legend.fontsize": 9,
        "axes.spines.top": False,
        "axes.spines.right": False,
    })


def fig_outcomes(pot: pd.DataFrame, out_path: Path) -> None:
    outcomes = [
        ("accuracy", "Classifier accuracy", (0, 1)),
        ("mean_raw", "NASA-TLX (raw)", (0, 20)),
        ("quiz_score", "Concept quiz (0-12)", (0, 12)),
        ("median_dwell_ms", "Median dwell (ms)", None),
    ]
    fig, axes = plt.subplots(1, len(outcomes), figsize=(11, 3.2))
    for ax, (col, label, ylim) in zip(axes, outcomes):
        if col not in pot.columns:
            ax.set_visible(False)
            continue
        df = pot.dropna(subset=[col]).copy()
        df["condition"] = pd.Categorical(df["condition"], categories=CONDITION_ORDER, ordered=True)
        sns.stripplot(
            data=df, x="condition", y=col, hue="condition", legend=False, ax=ax,
            palette=CONDITION_COLORS, alpha=0.6, jitter=0.15, size=4,
            order=CONDITION_ORDER,
        )
        means = df.groupby("condition", observed=True)[col].mean().reindex(CONDITION_ORDER)
        stds = df.groupby("condition", observed=True)[col].std().reindex(CONDITION_ORDER)
        for i, cond in enumerate(CONDITION_ORDER):
            ax.errorbar(i, means[cond], yerr=stds[cond] if not np.isnan(stds[cond]) else 0,
                        fmt="_", color="black", markersize=18, capsize=4, capthick=1.2, linewidth=2)
        ax.set_title(label)
        ax.set_xlabel("")
        ax.set_ylabel("")
        ax.set_xticks(range(len(CONDITION_ORDER)))
        ax.set_xticklabels([CONDITION_LABELS[c] for c in CONDITION_ORDER], rotation=15)
        if ylim:
            ax.set_ylim(*ylim)
    fig.suptitle("Adaptive MOCHA primary outcomes (SYNTHETIC pipeline run)", y=1.02)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def fig_controller_trace(events: pd.DataFrame, out_path: Path) -> None:
    if events.empty or "kind" not in events.columns:
        _empty(out_path, "No controller events")
        return
    decisions = events[events["kind"] == "controller.decision"].copy()
    if decisions.empty:
        _empty(out_path, "No controller decisions logged")
        return
    decisions["payload"] = decisions["payload_json"].apply(json.loads)
    decisions["load"] = decisions["payload"].apply(lambda p: p.get("load_state", {}).get("load"))
    decisions["band"] = decisions["payload"].apply(lambda p: p.get("decision", {}).get("difficulty_band"))
    decisions = decisions[decisions["condition"] == "adaptive"].dropna(subset=["load", "band"])
    if decisions.empty:
        _empty(out_path, "No Adaptive condition data")
        return
    representative_pid = decisions["participant_id"].value_counts().index[0]
    d = decisions[decisions["participant_id"] == representative_pid].copy()
    d = d.sort_values("ts").reset_index(drop=True)
    d["trial_idx"] = range(1, len(d) + 1)
    band_to_y = {"easy": 0.2, "medium": 0.5, "hard": 0.8}
    d["band_y"] = d["band"].map(band_to_y)
    fig, ax1 = plt.subplots(figsize=(8, 3.2))
    ax1.plot(d["trial_idx"], d["load"], "o-", color=CONDITION_COLORS["adaptive"], label="Estimated load")
    ax1.axhline(0.65, color="black", linestyle=":", linewidth=0.8, alpha=0.6)
    ax1.axhline(0.35, color="black", linestyle=":", linewidth=0.8, alpha=0.6)
    ax1.set_ylim(0, 1.0)
    ax1.set_ylabel("Cognitive-load estimate (0-1)")
    ax1.set_xlabel("Trial index within block")
    ax2 = ax1.twinx()
    ax2.scatter(d["trial_idx"], d["band_y"], marker="s", s=50, color=CONDITION_COLORS["fixed"], alpha=0.7, label="Controller band")
    ax2.set_ylim(0, 1.0)
    ax2.set_yticks([0.2, 0.5, 0.8])
    ax2.set_yticklabels(["easy", "medium", "hard"])
    ax2.set_ylabel("Controller decision")
    ax1.set_title(f"Controller trace for representative Adaptive participant ({representative_pid})")
    ax1.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def fig_tlx_profile(tlx: pd.DataFrame, out_path: Path) -> None:
    if tlx.empty:
        _empty(out_path, "No TLX data")
        return
    items = ["mental", "physical", "temporal", "performance", "effort", "frustration"]
    df = tlx.melt(id_vars=["condition"], value_vars=items, var_name="dimension", value_name="rating")
    df["condition"] = pd.Categorical(df["condition"], categories=CONDITION_ORDER, ordered=True)
    fig, ax = plt.subplots(figsize=(8, 3.4))
    sns.barplot(
        data=df, x="dimension", y="rating", hue="condition",
        palette=CONDITION_COLORS, hue_order=CONDITION_ORDER, ax=ax, errorbar="sd",
    )
    ax.set_ylim(0, 20)
    ax.set_xlabel("")
    ax.set_ylabel("Rating (0-20)")
    ax.set_title("NASA-TLX per dimension")
    handles, labels = ax.get_legend_handles_labels()
    ax.legend(handles, [CONDITION_LABELS[l] for l in labels], title="Condition")
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def fig_dwell_curve(labels: pd.DataFrame, out_path: Path) -> None:
    if labels.empty:
        _empty(out_path, "No labels data")
        return
    df = labels.copy()
    if "condition" not in df.columns:
        _empty(out_path, "labels has no condition column")
        return
    df = df.sort_values(["participant_id", "session_id", "submitted_at"]).copy()
    df["trial_index"] = df.groupby("session_id").cumcount() + 1
    df = df[df["trial_index"] <= 80]
    df["condition"] = pd.Categorical(df["condition"], categories=CONDITION_ORDER, ordered=True)
    fig, ax = plt.subplots(figsize=(7.5, 3.2))
    sns.lineplot(
        data=df, x="trial_index", y="dwell_ms", hue="condition",
        palette=CONDITION_COLORS, hue_order=CONDITION_ORDER, errorbar="se", ax=ax,
    )
    ax.set_xlabel("Trial index within block")
    ax.set_ylabel("Dwell time per label (ms)")
    ax.set_title("Per-trial dwell time across the block")
    handles, labels_ = ax.get_legend_handles_labels()
    ax.legend(handles, [CONDITION_LABELS[l] for l in labels_], title="Condition")
    fig.tight_layout()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def _empty(out_path: Path, text: str) -> None:
    fig, ax = plt.subplots(figsize=(6, 2))
    ax.text(0.5, 0.5, text, ha="center", va="center", fontsize=11, color="#888")
    ax.set_axis_off()
    fig.savefig(out_path, bbox_inches="tight")
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="mainstudy")
    ap.add_argument("--out", default="analysis/output/figures")
    args = ap.parse_args()
    out_dir = REPO_ROOT / args.out
    out_dir.mkdir(parents=True, exist_ok=True)
    data = load_study(args.tag)
    pot = primary_outcome_table(data)
    style()
    for ext in ("pdf", "png"):
        fig_outcomes(pot, out_dir / f"fig1_outcomes.{ext}")
        fig_controller_trace(data["events"], out_dir / f"fig2_controller.{ext}")
        fig_tlx_profile(data["tlx"], out_dir / f"fig3_tlx_profile.{ext}")
        fig_dwell_curve(data["labels"], out_dir / f"fig4_learning_curve.{ext}")
    print(f"wrote 8 figures (pdf+png) to {out_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

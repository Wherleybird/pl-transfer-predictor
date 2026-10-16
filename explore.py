from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

DATA_DIR = Path(__file__).parent / "data"
CHART_DIR = Path(__file__).parent / "charts"
CHART_DIR.mkdir(exist_ok=True)

df = pd.read_csv(DATA_DIR / "merged.csv")
df = df[df["market_value_in_eur"] > 0].copy()
df["value_m"] = df["market_value_in_eur"] / 1e6
df["log_value"] = np.log10(df["market_value_in_eur"])

# ---------- Numbers ----------
print("Rows:", len(df))
print(df["value_m"].describe().round(1))
print(f"\nSkew of raw value: {df['value_m'].skew():.2f}")
print(f"Skew of log value: {df['log_value'].skew():.2f}")
print("\nRows per position:")
print(df["position"].value_counts())
print("\nCorrelation with log value:")
cols = ["goals_scored", "assists", "minutes", "age", "total_points"]
print(df[cols + ["log_value"]].corr()["log_value"].drop("log_value").round(2))

# ---------- Chart 1: why we log-transform ----------
fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
axes[0].hist(df["value_m"], bins=30, color="#4C72B0", edgecolor="white")
axes[0].set_title("Raw market value")
axes[0].set_xlabel("Value (€ millions)")
axes[0].set_ylabel("Player-seasons")

axes[1].hist(df["log_value"], bins=30, color="#55A868", edgecolor="white")
axes[1].set_title("Log of market value")
axes[1].set_xlabel("Value (log scale)")
axes[1].set_xticks([5, 6, 7, 8])
axes[1].set_xticklabels(["€100k", "€1M", "€10M", "€100M"])
fig.tight_layout()
fig.savefig(CHART_DIR / "1_value_distribution.png", dpi=150)

# ---------- Chart 2: goals vs value, by position ----------
colors = {"GK": "#8172B3", "DF": "#4C72B0", "MD": "#55A868", "FW": "#C44E52"}
fig, ax = plt.subplots(figsize=(8, 5.5))
for pos, color in colors.items():
    sub = df[df["position"] == pos]
    ax.scatter(sub["goals_scored"], sub["value_m"], alpha=0.6, s=28, color=color, label=pos)
ax.set_yscale("log")
ax.set_xlabel("Goals in season")
ax.set_ylabel("Market value (€ millions, log scale)")
ax.set_title("Goals vs market value")
ax.legend(title="Position")
fig.tight_layout()
fig.savefig(CHART_DIR / "2_goals_vs_value.png", dpi=150)

# ---------- Chart 3: value by position ----------
order = ["GKP", "DEF", "MID", "FWD"]
fig, ax = plt.subplots(figsize=(7, 5))
ax.boxplot([df[df["position"] == p]["value_m"] for p in order])
ax.set_xticks(range(1, len(order) + 1))
ax.set_xticklabels(order)
ax.set_yscale("log")
ax.set_ylabel("Market value (€ millions, log scale)")
ax.set_title("Market value by position")
fig.tight_layout()
fig.savefig(CHART_DIR / "3_value_by_position.png", dpi=150)

print(f"\nCharts saved to {CHART_DIR}")
plt.show()
from pathlib import Path
import warnings
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

warnings.filterwarnings("ignore", message="Found unknown categories")

ROOT = Path(__file__).parent
DATA_DIR = ROOT / "data"
CHART_DIR = ROOT / "charts"
CHART_DIR.mkdir(exist_ok=True)

# ---------- Load and build features (final model: F2) ----------
df = pd.read_csv(DATA_DIR / "merged.csv")
df = df[df["market_value_in_eur"] > 0].copy()
df["club"] = df["club"].fillna("Unknown")
df["log_value"] = np.log(df["market_value_in_eur"])
df["goals_per90"] = df["goals_scored"] / df["minutes"] * 90
df["assists_per90"] = df["assists"] / df["minutes"] * 90
df["clean_sheets_per90"] = df["clean_sheets"] / df["minutes"] * 90
df["saves_per90"] = df["saves"] / df["minutes"] * 90
df["bonus_per90"] = df["bonus"] / df["minutes"] * 90
df["age_sq"] = (df["age"] - 25) ** 2
df["age_over29"] = (df["age"] - 29).clip(lower=0)
df["age_under21"] = (21 - df["age"]).clip(lower=0)
df["minutes_k"] = df["minutes"] / 1000
df = df.dropna(subset=["age", "goals_per90", "assists_per90"]).reset_index(drop=True)

club_counts = df["club"].value_counts()
rare = club_counts[club_counts < 10].index
df["club_group"] = df["club"].where(~df["club"].isin(rare), "Other")

# Cleaner display names from Transfermarkt
tm_names = pd.read_csv(DATA_DIR / "players.csv.gz").set_index("player_id")["name"]
df["player"] = df["tm_player_id"].map(tm_names).fillna(df["first_name"] + " " + df["second_name"])

# ---------- Out-of-fold predictions ----------
num_cols = ["goals_per90", "assists_per90", "clean_sheets_per90", "saves_per90",
            "bonus_per90", "minutes_k", "age", "age_sq", "age_over29", "age_under21"]
cat_cols = ["position", "season_name", "club_group"]

pre = ColumnTransformer(
    [("cat", OneHotEncoder(drop="first", handle_unknown="ignore"), cat_cols)],
    remainder="passthrough",
)
model = Pipeline([("pre", pre), ("lr", LinearRegression())])

pred_log = cross_val_predict(
    model, df[num_cols + cat_cols], df["log_value"],
    groups=df["player_id"], cv=GroupKFold(n_splits=5),
)

df["predicted_m"] = np.exp(pred_log) / 1e6
df["market_m"] = df["market_value_in_eur"] / 1e6
df["gap_m"] = df["market_m"] - df["predicted_m"]            # + = market values him MORE than the model
df["gap_pct"] = (df["market_m"] / df["predicted_m"] - 1) * 100
df["resid_log"] = df["log_value"] - pred_log

print(f"Out-of-fold R2 (log): {r2_score(df['log_value'], pred_log):.3f}")
print(f"Out-of-fold MAE: €{mean_absolute_error(df['market_m'], df['predicted_m']):.1f}M")

df.to_csv(DATA_DIR / "predictions.csv", index=False)

# ---------- Residuals by age band: should all be near zero ----------
bands = pd.cut(df["age"], [0, 21, 25, 29, 33, 100], right=False,
               labels=["<21", "21-24", "25-28", "29-32", "33+"])
print("\nAverage residual by age band (log scale; 0 = unbiased):")
print(df.groupby(bands, observed=True)["resid_log"].agg(["mean", "count"]).round(3))

# ---------- Tables: latest season, ranked by euro gap ----------
latest = df[df["season_name"] == "2025/26"]
cols = ["player", "club", "position", "age", "market_m", "predicted_m", "gap_m", "gap_pct"]

print("\nMARKET VALUES HIM MORE than the model, 2025/26 (by € gap):")
print(latest.nlargest(10, "gap_m")[cols].round(1).to_string(index=False))

print("\nMARKET VALUES HIM LESS than the model, 2025/26 (by € gap):")
print(latest.nsmallest(10, "gap_m")[cols].round(1).to_string(index=False))

# ---------- Chart 4: predicted vs actual ----------
fig, ax = plt.subplots(figsize=(7, 6.5))
ax.scatter(df["predicted_m"], df["market_m"], alpha=0.45, s=22, color="#4C72B0")
lims = [df[["predicted_m", "market_m"]].min().min() * 0.8,
        df[["predicted_m", "market_m"]].max().max() * 1.2]
ax.plot(lims, lims, color="black", lw=1, ls="--", label="Perfect prediction")
ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlabel("Model estimate (€M, log scale)")
ax.set_ylabel("Transfermarkt value (€M, log scale)")
ax.set_title("Predicted vs actual market value (out-of-fold)")
ax.legend()
fig.tight_layout()
fig.savefig(CHART_DIR / "4_predicted_vs_actual.png", dpi=150)

# ---------- Chart 5: biggest € gaps, 2025/26 ----------
show = pd.concat([latest.nsmallest(10, "gap_m"), latest.nlargest(10, "gap_m")]).sort_values("gap_m")
labels = show["player"] + " (" + show["club"].str.replace(" FC", "", regex=False) + ")"
colors = ["#55A868" if g < 0 else "#C44E52" for g in show["gap_m"]]

fig, ax = plt.subplots(figsize=(9, 7.5))
ax.barh(labels, show["gap_m"], color=colors)
ax.axvline(0, color="black", lw=0.8)
ax.set_xlabel("Transfermarkt value minus model estimate (€M)")
ax.set_title("2025/26: valued below (green) and above (red) the model")
fig.tight_layout()
fig.savefig(CHART_DIR / "5_biggest_gaps.png", dpi=150)

# ---------- Chart 6: residual check ----------
fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))
axes[0].scatter(df["age"], df["resid_log"], alpha=0.35, s=18, color="#4C72B0")
means = df.groupby(bands, observed=True).agg(age=("age", "mean"), resid=("resid_log", "mean"))
axes[0].plot(means["age"], means["resid"], color="#C44E52", marker="o", lw=2, label="Average per age band")
axes[0].axhline(0, color="black", lw=0.8)
axes[0].set_xlabel("Age")
axes[0].set_ylabel("Residual (log value: actual - predicted)")
axes[0].set_title("Residuals by age")
axes[0].legend()

axes[1].hist(df["resid_log"], bins=30, color="#55A868", edgecolor="white")
axes[1].axvline(0, color="black", lw=0.8)
axes[1].set_xlabel("Residual (log value: actual - predicted)")
axes[1].set_ylabel("Player-seasons")
axes[1].set_title("Distribution of residuals")
fig.tight_layout()
fig.savefig(CHART_DIR / "6_residuals.png", dpi=150)

print(f"\nSaved predictions to {DATA_DIR / 'predictions.csv'} and charts to {CHART_DIR}")
plt.show()
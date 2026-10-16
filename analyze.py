# Need this file because we need a prediction for every player-season from a model that never saw
# that player. cross_val_predict() does exactly that, and we can save the predictions 
# to disk for later analysis.

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

# ---------- Load and build features (same as Model D) ----------
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
df["minutes_k"] = df["minutes"] / 1000
df = df.dropna(subset=["age", "goals_per90", "assists_per90"]).reset_index(drop=True)

# Cleaner display names from Transfermarkt
tm_names = pd.read_csv(DATA_DIR / "players.csv.gz").set_index("player_id")["name"]
df["player"] = df["tm_player_id"].map(tm_names).fillna(df["first_name"] + " " + df["second_name"])

print("Rows per club (smallest 12):")
print(df["club"].value_counts().tail(12))

# ---------- Out-of-fold predictions ----------
num_cols = ["goals_per90", "assists_per90", "clean_sheets_per90", "saves_per90",
            "bonus_per90", "minutes_k", "age", "age_sq"]
cat_cols = ["position", "season_name", "club"]

pre = ColumnTransformer(
    [("cat", OneHotEncoder(drop="first", handle_unknown="ignore"), cat_cols)],
    remainder="passthrough",
)
model = Pipeline([("pre", pre), ("lr", LinearRegression())])

pred_log = cross_val_predict(
    model, df[num_cols + cat_cols], df["log_value"],
    groups=df["player_id"], cv=GroupKFold(n_splits=5),
)

df["predicted_eur"] = np.exp(pred_log)
df["market_m"] = df["market_value_in_eur"] / 1e6
df["predicted_m"] = df["predicted_eur"] / 1e6
df["gap_pct"] = (df["market_m"] / df["predicted_m"] - 1) * 100  # + = market values him MORE than the model

print(f"\nOut-of-fold R2 (log): {r2_score(df['log_value'], pred_log):.3f}")
print(f"Out-of-fold MAE: €{mean_absolute_error(df['market_m'], df['predicted_m']):.1f}M")

df.to_csv(DATA_DIR / "predictions.csv", index=False)

# ---------- Tables: latest season ----------
latest = df[df["season_name"] == "2025/26"]
cols = ["player", "club", "position", "age", "market_m", "predicted_m", "gap_pct"]

print("\nMOST OVERVALUED by the market, 2025/26 (market > model):")
print(latest.nlargest(10, "gap_pct")[cols].round(1).to_string(index=False))

print("\nMOST UNDERVALUED by the market, 2025/26 (market < model):")
print(latest.nsmallest(10, "gap_pct")[cols].round(1).to_string(index=False))

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

# ---------- Chart 5: over/undervalued, 2025/26 ----------
show = pd.concat([latest.nsmallest(10, "gap_pct"), latest.nlargest(10, "gap_pct")])
show = show.sort_values("gap_pct")
labels = show["player"] + " (" + show["club"].str.replace(" FC", "", regex=False) + ")"
colors = ["#55A868" if g < 0 else "#C44E52" for g in show["gap_pct"]]

fig, ax = plt.subplots(figsize=(9, 7.5))
ax.barh(labels, show["gap_pct"], color=colors)
ax.axvline(0, color="black", lw=0.8)
ax.set_xlabel("Market value vs model estimate (%)")
ax.set_title("2025/26: most undervalued (green) and overvalued (red) players")
fig.tight_layout()
fig.savefig(CHART_DIR / "5_over_under_valued.png", dpi=150)

print(f"\nSaved predictions to {DATA_DIR / 'predictions.csv'} and charts to {CHART_DIR}")
plt.show()


from pathlib import Path
import numpy as np
import pandas as pd
import warnings
warnings.filterwarnings("ignore", message="Found unknown categories")
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold, GroupShuffleSplit, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

DATA_DIR = Path(__file__).parent / "data"

df = pd.read_csv(DATA_DIR / "merged.csv")
df["club"] = df["club"].fillna("Unknown")
df = df[df["market_value_in_eur"] > 0].copy()
df["log_value"] = np.log(df["market_value_in_eur"])
df["goals_per90"] = df["goals_scored"] / df["minutes"] * 90
df["assists_per90"] = df["assists"] / df["minutes"] * 90

df["clean_sheets_per90"] = df["clean_sheets"] / df["minutes"] * 90
df["saves_per90"] = df["saves"] / df["minutes"] * 90
df["bonus_per90"] = df["bonus"] / df["minutes"] * 90
df["age_sq"] = (df["age"] - 25) ** 2     # lets the age curve bend
df["minutes_k"] = df["minutes"] / 1000   # minutes in thousands, readable coefficient

# Sanity check: are these stats recorded in every season?
print(df.groupby("season_name")[["clean_sheets", "saves", "bonus"]]
        .apply(lambda g: (g > 0).mean()).round(2))

before = len(df)
df = df.dropna(subset=["age", "goals_per90", "assists_per90"]).reset_index(drop=True)
print(f"Rows: {len(df)} (dropped {before - len(df)} with missing values)")

# Group clubs with fewer than 10 player-seasons into "Other"
club_counts = df["club"].value_counts()
rare = club_counts[club_counts < 10].index
df["club_group"] = df["club"].where(~df["club"].isin(rare), "Other")

# Age bands (the numbers in the labels keep them sorted correctly)
df["age_band"] = pd.cut(
    df["age"],
    bins=[0, 21, 25, 29, 33, 100],
    labels=["1: under 21", "2: 21-24", "3: 25-28", "4: 29-32", "5: 33+"],
    right=False,
).astype(str)

print("\nClub groups:", df["club_group"].nunique())
print(df["age_band"].value_counts().sort_index())

y = df["log_value"]
groups = df["player_id"]  # keeps each player entirely in train OR test

# One 80/20 split by player
gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
train_idx, test_idx = next(gss.split(df, y, groups))


def evaluate(name, num_cols, cat_cols):
    pre = ColumnTransformer(
           [("cat", OneHotEncoder(drop="first", handle_unknown="ignore"), cat_cols)], remainder="passthrough"
    )
    model = Pipeline([("pre", pre), ("lr", LinearRegression())])
    X = df[num_cols + cat_cols]

    # 5-fold cross-validation, grouped by player
    cv_r2 = cross_val_score(model, X, y, groups=groups, cv=GroupKFold(n_splits=5), scoring="r2")

    # Single held-out test set
    model.fit(X.iloc[train_idx], y.iloc[train_idx])
    pred = model.predict(X.iloc[test_idx])
    test_r2 = r2_score(y.iloc[test_idx], pred)
    mae_m = mean_absolute_error(np.exp(y.iloc[test_idx]), np.exp(pred)) / 1e6

    print(f"\n=== {name} ===")
    print(f"Grouped 5-fold R2: {cv_r2.mean():.3f} (+/- {cv_r2.std():.3f})")
    print(f"Test R2 (log value): {test_r2:.3f}")
    print(f"Test MAE: €{mae_m:.1f}M")

    # Refit on everything to inspect coefficients
    model.fit(X, y)
    coefs = pd.Series(
        model.named_steps["lr"].coef_,
        index=model.named_steps["pre"].get_feature_names_out(),
    )
    print("Coefficients (change in log value per unit):")
    print(coefs.round(3).to_string())


evaluate("Model A: goals, assists, position", ["goals_scored", "assists"], ["position"])
evaluate(
    "Model B: + age, minutes, per-90 stats",
    ["goals_per90", "assists_per90", "minutes", "age"],
    ["position"],
)

evaluate(
    "Model C: + age curve, season, defensive/GK stats",
    ["goals_per90", "assists_per90", "clean_sheets_per90", "saves_per90",
     "bonus_per90", "minutes_k", "age", "age_sq"],
    ["position", "season_name"],
)

evaluate(
       "Model D: Model C + club",
       ["goals_per90", "assists_per90", "clean_sheets_per90", "saves_per90",
        "bonus_per90", "minutes_k", "age", "age_sq"],
       ["position", "season_name", "club"],
   )

evaluate(
    "Model E: Model C + grouped club + age bands",
    ["goals_per90", "assists_per90", "clean_sheets_per90", "saves_per90",
     "bonus_per90", "minutes_k"],
    ["position", "season_name", "club_group", "age_band"],
)
"""Fit the final linear model on every season and export its coefficients.

Run once after analyze.py:   python export_model.py

It writes assets/model.json. The app reads plain numbers from that file, so
there is no pickle and no scikit-learn version to keep in sync when deploying.
"""
import json
import warnings
from pathlib import Path

import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import GroupKFold, cross_val_predict, cross_val_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder

from features import CAT_COLS, NUM_COLS, load_features

warnings.filterwarnings("ignore", message="Found unknown categories")

OUT = Path(__file__).parent / "assets" / "model.json"

df = load_features()
X = df[NUM_COLS + CAT_COLS]
y = df["log_value"]


def make_pipeline():
    pre = ColumnTransformer(
        [("cat", OneHotEncoder(drop="first", handle_unknown="ignore"), CAT_COLS)],
        remainder="passthrough",
    )
    return Pipeline([("pre", pre), ("lr", LinearRegression())])


# Honest accuracy numbers: every row is predicted by a model that never saw that player.
cv = GroupKFold(n_splits=5)
oof = cross_val_predict(make_pipeline(), X, y, groups=df["player_id"], cv=cv)
cv_scores = cross_val_score(make_pipeline(), X, y, groups=df["player_id"], cv=cv, scoring="r2")
resid = y - oof

# Final model on all rows
pipe = make_pipeline().fit(X, y)
pre = pipe.named_steps["pre"]
lr = pipe.named_steps["lr"]
encoder = pre.named_transformers_["cat"]

coef = lr.coef_
pos = 0
categorical, cat_mean_coef = {}, {}
for i, col in enumerate(CAT_COLS):
    levels = list(encoder.categories_[i])
    dropped = encoder.drop_idx_[i]
    table = {}
    for j, level in enumerate(levels):
        if j == dropped:
            table[str(level)] = 0.0
        else:
            table[str(level)] = float(coef[pos])
            pos += 1
    categorical[col] = table
    share = df[col].value_counts(normalize=True)
    cat_mean_coef[col] = float(sum(table[str(k)] * v for k, v in share.items()))

numeric = {c: float(coef[pos + i]) for i, c in enumerate(NUM_COLS)}
assert pos + len(NUM_COLS) == len(coef), "coefficient bookkeeping is off"

# Sanity check: rebuilding the prediction by hand must match scikit-learn exactly.
manual = lr.intercept_ + sum(numeric[c] * df[c] for c in NUM_COLS)
for col in CAT_COLS:
    manual = manual + df[col].map(categorical[col])
assert np.allclose(manual, pipe.predict(X)), "exported coefficients do not reproduce the model"

# Typical season totals per position: starting points for the estimator sliders
defaults = {}
for position, g in df.groupby("position"):
    defaults[position] = {
        "minutes": float(g["minutes"].median()),
        "goals": float(g["goals_scored"].median()),
        "assists": float(g["assists"].median()),
        "clean_sheets": float(g["clean_sheets"].median()),
        "saves": float(g["saves"].median()),
        "bonus": float(g["bonus"].median()),
        "age": float(g["age"].median()),
    }

params = {
    "version": 1,
    "trained_on_rows": int(len(df)),
    "intercept": float(lr.intercept_),
    "numeric": numeric,
    "numeric_means": {c: float(df[c].mean()) for c in NUM_COLS},
    "categorical": categorical,
    "categorical_mean_coef": cat_mean_coef,
    "baseline_log_value": float(y.mean()),
    "residual_sigma": float(resid.std()),
    "metrics": {
        "oof_r2": float(r2_score(y, oof)),
        "oof_mae_m": float(mean_absolute_error(np.exp(y) / 1e6, np.exp(oof) / 1e6)),
        "cv_r2_mean": float(cv_scores.mean()),
        "cv_r2_std": float(cv_scores.std()),
    },
    "defaults": defaults,
}

OUT.parent.mkdir(exist_ok=True)
OUT.write_text(json.dumps(params, indent=2), encoding="utf-8")
print(f"Saved {OUT}")
print(f"Rows: {len(df)} | out-of-fold R2 {params['metrics']['oof_r2']:.3f} | "
      f"MAE EUR {params['metrics']['oof_mae_m']:.1f}M | typical error x/÷ {np.exp(params['residual_sigma']):.2f}")
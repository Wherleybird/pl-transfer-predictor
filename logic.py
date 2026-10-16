"""Data and model logic for the EPL's Value Gap app.

Nothing in here imports Streamlit, so every function can be tested on its own.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from clubs import club_info

ROOT = Path(__file__).parent
DATA_PATH = ROOT / "data" / "predictions.csv"
MODEL_PATH = ROOT / "assets" / "model.json"

POSITION_NAMES = {"GKP": "Goalkeeper", "DEF": "Defender", "MID": "Midfielder", "FWD": "Forward"}
POSITIONS = list(POSITION_NAMES)

REQUIRED_COLUMNS = [
    "season_name", "player_id", "player", "club", "position", "age",
    "market_m", "predicted_m", "gap_m", "gap_pct",
]

# Results from the modelling notebook-style runs (experiments.py / compare_models.py).
MODEL_HISTORY = [
    # id, name, what changed, CV R2, test R2, MAE (EUR M)
    ("A", "Baseline", "Goals, assists, position", 0.183, 0.156, 18.2),
    ("B", "Age and playing time", "+ age, minutes, per-90 rates", 0.430, 0.394, 16.1),
    ("C", "Season and defending", "+ age curve, season, clean sheets, saves, bonus", 0.589, 0.585, 14.0),
    ("D", "Club", "+ club", 0.728, 0.742, 10.7),
    ("E", "Age bands (dropped)", "Age bands and grouped clubs scored lower", 0.691, 0.689, 11.1),
    ("F2", "Final model", "Model D + grouped rare clubs + age hinges", 0.739, 0.747, 10.4),
]
FINAL_MODEL_ID = "F2"

MODEL_COMPARISON = [
    ("Linear regression", 0.752, 8.8),
    ("Gradient boosting", 0.694, 9.8),
    ("Random forest", 0.627, 11.1),
]

AGE_BANDS = [0, 21, 25, 29, 33, 100]
AGE_BAND_LABELS = ["Under 21", "21 to 24", "25 to 28", "29 to 32", "33 and over"]


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------
def load_predictions(path: Path = DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"{Path(path).name} is missing columns {missing}. "
            "Re-run analyze.py to rebuild it."
        )
    df = df.copy()
    df["club"] = df["club"].fillna("Unknown").astype(str)
    for col in ["age", "market_m", "predicted_m", "gap_m", "gap_pct"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["market_m", "predicted_m", "age"]).reset_index(drop=True)
    info = df["club"].map(club_info)
    df["club_short"] = info.map(lambda d: d["short"])
    df["club_abbr"] = info.map(lambda d: d["abbr"])
    if "element_code" in df.columns:
        df["element_code"] = pd.to_numeric(df["element_code"], errors="coerce").astype("Int64")
    else:
        df["element_code"] = pd.array([pd.NA] * len(df), dtype="Int64")
    return df.sort_values(["season_name", "market_m"], ascending=[True, False]).reset_index(drop=True)


def season_list(df: pd.DataFrame) -> list[str]:
    return sorted(df["season_name"].unique())


def player_labels(df: pd.DataFrame) -> dict[int, str]:
    """player_id -> 'Name  (Club)' using the player's most recent season."""
    latest = df.sort_values("season_name").drop_duplicates("player_id", keep="last")
    return {int(r.player_id): f"{r.player}  ({r.club_short})" for r in latest.itertuples()}


# --------------------------------------------------------------------------
# Tables and summaries
# --------------------------------------------------------------------------
def split_gaps(view: pd.DataFrame, n: int = 10, by: str = "gap_m"):
    """Return (market pays more, market pays less), each at most n rows.

    The two lists are split on the SIGN of the gap, so a player can only ever
    appear in one of them. (Using nlargest and nsmallest on the same small
    selection returned the same players in both lists.)
    """
    over = view[view["gap_m"] > 0].nlargest(n, by)
    under = view[view["gap_m"] < 0].nsmallest(n, by)
    return over, under


def club_table(season_df: pd.DataFrame) -> pd.DataFrame:
    g = (
        season_df.groupby("club")
        .agg(players=("player_id", "nunique"), market=("market_m", "sum"), model=("predicted_m", "sum"))
        .reset_index()
    )
    g["gap"] = g["market"] - g["model"]
    info = g["club"].map(club_info)
    g["short"] = info.map(lambda d: d["short"])
    return g.sort_values("market", ascending=False).reset_index(drop=True)


def age_curve(df: pd.DataFrame, min_n: int = 8) -> pd.DataFrame:
    d = df.assign(age_r=df["age"].round().astype(int))
    d = d[d["age_r"].between(17, 38)]
    g = d.groupby("age_r").agg(n=("market_m", "size"), Market=("market_m", "median"), Model=("predicted_m", "median"))
    g = g[g["n"] >= min_n].reset_index().rename(columns={"age_r": "Age"})
    return g


def band_residuals(df: pd.DataFrame) -> pd.DataFrame:
    """Average out-of-fold error by age band, in percent of value."""
    if "resid_log" not in df.columns:
        d = df.assign(resid_log=np.log(df["market_m"]) - np.log(df["predicted_m"]))
    else:
        d = df
    bands = pd.cut(d["age"], AGE_BANDS, labels=AGE_BAND_LABELS, right=False)
    g = d.groupby(bands, observed=True)["resid_log"].agg(["mean", "size"]).reset_index()
    g.columns = ["Age band", "mean_log", "n"]
    g["Average miss (%)"] = (np.exp(g["mean_log"]) - 1) * 100
    return g


def headline_numbers(df: pd.DataFrame) -> dict:
    y = np.log(df["market_m"].to_numpy())
    p = np.log(df["predicted_m"].to_numpy())
    sst = float(((y - y.mean()) ** 2).sum())
    sse = float(((y - p) ** 2).sum())
    return {
        "rows": int(len(df)),
        "players": int(df["player_id"].nunique()),
        "r2": 1 - sse / sst if sst else float("nan"),
        "mae": float(df["gap_m"].abs().mean()),
        "clubs": int(df["club"].nunique()),
    }


# --------------------------------------------------------------------------
# Formatting
# --------------------------------------------------------------------------
def fmt_m(x: float, signed: bool = False) -> str:
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "n/a"
    sign = ("+" if x > 0 else "-" if x < 0 else "") if signed else ("-" if x < 0 else "")
    v = abs(x)
    body = f"{v:.0f}" if v >= 100 else f"{v:.1f}"
    return f"{sign}€{body}M"


def fmt_pct(x: float, signed: bool = True) -> str:
    sign = ("+" if x > 0 else "-" if x < 0 else "") if signed else ""
    return f"{sign}{abs(x):.0f}%"


# --------------------------------------------------------------------------
# The exported linear model (coefficients only, no pickle)
# --------------------------------------------------------------------------
NUMERIC_GROUPS = {
    "Age": ["age", "age_sq", "age_over29", "age_under21"],
    "Goals and assists": ["goals_per90", "assists_per90"],
    "Clean sheets and saves": ["clean_sheets_per90", "saves_per90"],
    "Bonus points": ["bonus_per90"],
    "Playing time": ["minutes_k"],
}
CATEGORICAL_LABELS = {"club_group": "Club", "position": "Position", "season_name": "Season (market inflation)"}


def build_features(age, minutes, goals, assists, clean_sheets, saves, bonus) -> dict:
    """Same feature maths as features.py, for one player-season of season totals."""
    minutes = max(float(minutes), 1.0)
    per90 = 90.0 / minutes
    age = float(age)
    return {
        "goals_per90": goals * per90,
        "assists_per90": assists * per90,
        "clean_sheets_per90": clean_sheets * per90,
        "saves_per90": saves * per90,
        "bonus_per90": bonus * per90,
        "minutes_k": minutes / 1000.0,
        "age": age,
        "age_sq": (age - 25.0) ** 2,
        "age_over29": max(age - 29.0, 0.0),
        "age_under21": max(21.0 - age, 0.0),
    }


class ValueModel:
    """Evaluates the final linear regression from the coefficients in model.json."""

    def __init__(self, params: dict):
        self.p = params
        self.numeric = params["numeric"]
        self.categorical = params["categorical"]

    @classmethod
    def load(cls, path: Path = MODEL_PATH) -> "ValueModel":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    # -- helpers -----------------------------------------------------------
    def club_group_for(self, club: str) -> str:
        return club if club in self.categorical["club_group"] else "Other"

    def _cat_coef(self, col: str, level: str) -> float:
        table = self.categorical[col]
        if level in table:
            return table[level]
        return table.get("Other", 0.0) if col == "club_group" else 0.0

    # -- prediction --------------------------------------------------------
    def predict_log(self, feats: dict, position: str, season: str, club_group: str) -> float:
        total = self.p["intercept"]
        total += sum(self.numeric[k] * feats[k] for k in self.numeric)
        total += self._cat_coef("position", position)
        total += self._cat_coef("season_name", season)
        total += self._cat_coef("club_group", club_group)
        return float(total)

    def predict_m(self, feats, position, season, club_group) -> float:
        return float(np.exp(self.predict_log(feats, position, season, club_group)) / 1e6)

    def interval_m(self, value_m: float) -> tuple[float, float]:
        s = self.p["residual_sigma"]
        return value_m * float(np.exp(-s)), value_m * float(np.exp(s))

    # -- explanation -------------------------------------------------------
    def breakdown(self, feats: dict, position: str, season: str, club_group: str) -> list[dict]:
        """Effect of each factor versus the average player, as % of value.

        Because the model is linear in log-value, the effects multiply:
        estimate = average player x (1 + effect_1) x (1 + effect_2) x ...
        """
        out = []
        means = self.p["numeric_means"]
        for label, cols in NUMERIC_GROUPS.items():
            eff = sum(self.numeric[c] * (feats[c] - means[c]) for c in cols)
            out.append({"factor": label, "log_effect": float(eff)})
        for col, label in CATEGORICAL_LABELS.items():
            level = {"club_group": club_group, "position": position, "season_name": season}[col]
            eff = self._cat_coef(col, level) - self.p["categorical_mean_coef"][col]
            out.append({"factor": label, "log_effect": float(eff)})
        for row in out:
            row["effect_pct"] = (float(np.exp(row["log_effect"])) - 1.0) * 100.0
        return sorted(out, key=lambda r: abs(r["log_effect"]), reverse=True)

    def average_player_m(self) -> float:
        return float(np.exp(self.p["baseline_log_value"]) / 1e6)

    # -- what the model learned (for the Model page) ------------------------
    def club_premiums(self) -> pd.DataFrame:
        base = self.p["categorical_mean_coef"]["club_group"]
        rows = [
            {"club": club, "premium_pct": (float(np.exp(c - base)) - 1.0) * 100.0}
            for club, c in self.categorical["club_group"].items()
        ]
        return pd.DataFrame(rows).sort_values("premium_pct", ascending=False).reset_index(drop=True)

    def season_effects(self) -> pd.DataFrame:
        table = self.categorical["season_name"]
        first = sorted(table)[0]
        return pd.DataFrame(
            [{"season": s, "vs_first_pct": (float(np.exp(table[s] - table[first])) - 1.0) * 100.0} for s in sorted(table)]
        )

    def age_curve_effect(self, ages=None) -> pd.DataFrame:
        ages = np.arange(17, 38.5, 0.5) if ages is None else np.asarray(ages, dtype=float)
        n = self.numeric

        def f(a):
            return (n["age"] * a + n["age_sq"] * (a - 25.0) ** 2
                    + n["age_over29"] * max(a - 29.0, 0.0) + n["age_under21"] * max(21.0 - a, 0.0))

        ref = f(25.0)
        return pd.DataFrame({"Age": ages, "Value vs age 25 (%)": [(np.exp(f(a) - ref) - 1.0) * 100.0 for a in ages]})


def feats_from_row(row, model: ValueModel) -> dict:
    """Pull the model features out of a predictions.csv row."""
    return {k: float(row[k]) for k in model.numeric}
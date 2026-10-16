from pathlib import Path
import numpy as np
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"

NUM_COLS = ["goals_per90", "assists_per90", "clean_sheets_per90", "saves_per90",
            "bonus_per90", "minutes_k", "age", "age_sq", "age_over29", "age_under21"]
CAT_COLS = ["position", "season_name", "club_group"]


def load_features():
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
    return df
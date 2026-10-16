from pathlib import Path
import unicodedata
import pandas as pd
import requests

DATA_DIR = Path(__file__).parent / "data"

REVIEW_IDS = [1, 4, 10, 57, 64, 67, 79, 102, 142, 157, 165, 233, 248, 263,
              319, 571, 350, 364, 402, 458, 470, 472, 403, 508, 527, 578, 532]

POS = {"GKP": "Goalkeeper", "DEF": "Defender", "MID": "Midfield", "FWD": "Attack"}


def normalize(s):
    s = str(s).lower()
    for a, b in {"ø": "o", "ł": "l", "đ": "d", "ß": "ss", "æ": "ae", "œ": "oe"}.items():
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("-", " ").replace("'", "")
    return " ".join(s.split())


stats = pd.read_csv(DATA_DIR / "player_history.csv")
players = pd.read_csv(DATA_DIR / "players.csv.gz")
vals = pd.read_csv(DATA_DIR / "player_valuations.csv.gz", parse_dates=["date"])

# FPL team names, so duplicates like the two Reece Jameses are easy to tell apart
boot = requests.get("https://fantasy.premierleague.com/api/bootstrap-static/", timeout=30).json()
teams = {t["id"]: t["name"] for t in boot["teams"]}
fpl_team = {e["id"]: teams[e["team"]] for e in boot["elements"]}

# Only consider Transfermarkt players valued at a Premier League club since 2021
pl = vals[(vals["player_club_domestic_competition_id"] == "GB1") & (vals["date"] >= "2021-01-01")]
pl_counts = pl.groupby("player_id").size()

pool = players[players["player_id"].isin(pl_counts.index)].copy()
pool["tokens"] = (
    (pool["name"].fillna("") + " " + pool["last_name"].fillna(""))
    .map(normalize).str.split().map(set)
)

suggested = {}
for fid in REVIEW_IDS:
    rows = stats[stats["player_id"] == fid]
    if rows.empty:
        continue
    r0 = rows.iloc[0]
    full = f"{r0['first_name']} {r0['second_name']}"
    toks = {t for t in normalize(full).split() if len(t) >= 4}
    pos = POS[r0["position"]]

    pool["score"] = pool["tokens"].map(lambda s: len(s & toks))
    hits = pool[(pool["score"] > 0) & (pool["position"] == pos)]
    hits = hits.sort_values("score", ascending=False).head(5)

    print(f"\n[{fid}] {full} | FPL: {r0['position']}, {fpl_team.get(fid, '?')}, "
          f"seasons {rows['season_name'].min()} to {rows['season_name'].max()}")
    if hits.empty:
        print("    no candidates found")
    for h in hits.itertuples():
        print(f"    {h.player_id:>7}  {h.name} | {str(h.date_of_birth)[:10]} | "
              f"{h.current_club_name} | last_season {h.last_season} | "
              f"PL valuations: {pl_counts[h.player_id]}")
    if len(hits) == 1:
        suggested[fid] = int(hits.iloc[0]["player_id"])

print("\nSINGLE-CANDIDATE SUGGESTIONS (check the names above before pasting):")
print("MANUAL = {")
for k, v in suggested.items():
    print(f"    {k}: {v},")
print("}")
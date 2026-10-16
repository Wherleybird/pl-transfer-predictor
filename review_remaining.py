# file used to explore the 7 missing players from the review_matches.py output

from pathlib import Path
import unicodedata
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"

# fpl_id: (who we're looking for, name prefixes to search)
SEARCHES = {
    102: ("Yehor Yarmoliuk, Brentford midfielder", ["yarmol"]),
    157: ("Estevao, Chelsea winger", ["estevao"]),
    248: ("Norberto Bercique Gomes Betuncal (Beto), Everton", ["beto"]),
    263: ("Kevin Santos Lopes de Macedo, Fulham", ["kevin"]),
    578: ("Mykhailo Mudryk", ["mudryk"]),
    67: ("Rayan Vitor, Bournemouth (NOT Cherki)", ["rayan"]),
    403: ("Savio Moreira de Oliveira (Savinho)", ["savi"]),
}


def normalize(s):
    s = unicodedata.normalize("NFKD", str(s).lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    return s.replace("-", " ").replace("'", "")


players = pd.read_csv(DATA_DIR / "players.csv.gz")
vals = pd.read_csv(DATA_DIR / "player_valuations.csv.gz", parse_dates=["date"])
pl = vals[(vals["player_club_domestic_competition_id"] == "GB1") & (vals["date"] >= "2021-01-01")]
pl_counts = pl.groupby("player_id").size()

pool = players[players["player_id"].isin(pl_counts.index)].copy()
pool["toks"] = pool["name"].fillna("").map(normalize).str.split()

for fid, (label, prefixes) in SEARCHES.items():
    hits = pool[pool["toks"].map(lambda ts: any(t.startswith(p) for t in ts for p in prefixes))]
    hits = hits.sort_values("last_season", ascending=False).head(12)
    print(f"\n[{fid}] {label}")
    if hits.empty:
        print("    no candidates found")
    for h in hits.itertuples():
        print(f"    {h.player_id:>7}  {h.name} | {str(h.date_of_birth)[:10]} | "
              f"{h.current_club_name} | {h.position} | last_season {h.last_season} | "
              f"PL valuations: {pl_counts[h.player_id]}")
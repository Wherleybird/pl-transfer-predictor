from pathlib import Path
import unicodedata
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"

# Fill this in later for players the matcher can't resolve: {fpl_player_id: transfermarkt_player_id}
MANUAL = {
    1: 262749,     # David Raya (Arsenal)
    4: 435338,     # Gabriel (Arsenal)
    10: 335721,    # Ben White
    57: 465555,    # Djordje Petrovic
    64: 61841,     # Adam Smith (Bournemouth)
    67: 1012564,   # Rayan (Bournemouth)
    79: 711337,    # Evanilson
    102: 717411,   # Yegor Yarmolyuk
    142: 472423,   # Reece James (Chelsea, b. 1999)
    157: 1056993,  # Estevao
    165: 626724,   # Joao Pedro (Chelsea, b. 2001)
    233: 404842,   # Mykolenko
    248: 595809,   # Beto
    263: 900195,   # Kevin
    319: 292139,   # Sammie Szmodics
    350: 105470,   # Alisson
    364: 338070,   # Tsimikas
    402: 357565,   # Rodri
    403: 743591,   # Savinho
    458: 333241,   # Joelinton
    470: 156501,   # Felipe (Forest, b. 1989)
    472: 1005649,  # Murillo
    508: 192765,   # Ben Davies (Spurs)
    527: 378710,   # Richarlison
    532: 503686,   # Dan Ballard (Sunderland)
    571: 357162,   # Florentino (Burnley in 2025/26)
    578: 537860,   # Mykhaylo Mudryk
}


def normalize(s):
    s = str(s).lower()
    for a, b in {"ø": "o", "ł": "l", "đ": "d", "ß": "ss", "æ": "ae", "œ": "oe"}.items():
        s = s.replace(a, b)
    s = unicodedata.normalize("NFKD", s)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("-", " ").replace("'", "")
    return " ".join(s.split())


def tokens_match(a, b):
    small, big = (a, b) if len(a) <= len(b) else (b, a)
    return len(small) >= 2 and small <= big


# ---------- Load ----------
stats = pd.read_csv(DATA_DIR / "player_history.csv")
players = pd.read_csv(DATA_DIR / "players.csv.gz", parse_dates=["date_of_birth"])
vals = pd.read_csv(DATA_DIR / "player_valuations.csv.gz", parse_dates=["date"])

stats = stats[(stats["season_name"] >= "2021/22") & (stats["minutes"] >= 450)].copy()
print("Stat rows after filtering:", len(stats))

# ---------- One valuation per player-season (Premier League clubs only) ----------
pl_vals = vals[
    (vals["player_club_domestic_competition_id"] == "GB1") & (vals["date"] >= "2021-01-01")
]
season_rows = []
for end_year in range(2022, 2027):
    window = pl_vals[
        (pl_vals["date"] >= f"{end_year}-01-01") & (pl_vals["date"] <= f"{end_year}-06-30")
    ]
    latest = window.sort_values("date").groupby("player_id").tail(1).copy()
    latest["season_name"] = f"{end_year - 1}/{str(end_year)[2:]}"
    season_rows.append(latest)

season_vals = pd.concat(season_rows)[
    ["player_id", "season_name", "date", "market_value_in_eur"]
].rename(columns={"player_id": "tm_player_id", "date": "value_date"})
print("Player-season valuations:", len(season_vals))

# ---------- Match FPL players to Transfermarkt players ----------
cand = players[players["player_id"].isin(season_vals["tm_player_id"])].copy()
cand["norm"] = cand["name"].map(normalize)
cand["tokens"] = cand["norm"].str.split().map(set)
exact = cand.groupby("norm")["player_id"].apply(list).to_dict()

fpl = stats[["player_id", "first_name", "second_name"]].drop_duplicates("player_id").copy()
fpl["norm"] = (fpl["first_name"] + " " + fpl["second_name"]).map(normalize)
fpl["tokens"] = fpl["norm"].str.split().map(set)

results = []
for r in fpl.itertuples():
    if r.player_id in MANUAL:
        ids, method = [MANUAL[r.player_id]], "manual"
    else:
        ids, method = exact.get(r.norm, []), "exact"
        if not ids:
            ids = [c.player_id for c in cand.itertuples() if tokens_match(c.tokens, r.tokens)]
            method = "tokens"
    status = "ok" if len(ids) == 1 else ("none" if len(ids) == 0 else "ambiguous")
    results.append({
        "fpl_id": r.player_id,
        "name": f"{r.first_name} {r.second_name}",
        "tm_player_id": ids[0] if len(ids) == 1 else None,
        "candidates": ids if len(ids) > 1 else None,
        "method": method,
        "status": status,
    })

res = pd.DataFrame(results)
print("\nMATCH REPORT")
print(res["status"].value_counts())
print(res.loc[res["status"] == "ok", "method"].value_counts())
print("\nNeeds review:")
print(res.loc[res["status"] != "ok", ["fpl_id", "name", "status", "candidates"]].to_string())

# ---------- Merge everything ----------
ok = res[res["status"] == "ok"][["fpl_id", "tm_player_id"]]
tm_info = players[["player_id", "date_of_birth", "position", "sub_position"]].rename(
    columns={"player_id": "tm_player_id", "position": "tm_position"}
)

merged = (
    stats.merge(ok, left_on="player_id", right_on="fpl_id")
    .merge(season_vals, on=["tm_player_id", "season_name"], how="inner")
    .merge(tm_info, on="tm_player_id", how="left")
)
merged["age"] = (merged["value_date"] - merged["date_of_birth"]).dt.days / 365.25

merged.to_csv(DATA_DIR / "merged.csv", index=False)

print(f"\nMerged rows: {len(merged)} (from {len(stats)} stat rows)")
print(merged.sort_values("market_value_in_eur", ascending=False).head(10)[
    ["season_name", "first_name", "second_name", "position", "goals_scored",
     "assists", "age", "market_value_in_eur"]
].to_string())

print("\nSPOT CHECK (manual matches):")
check_ids = [263, 470, 571, 157, 67, 403]
print(merged[merged["player_id"].isin(check_ids)][
    ["season_name", "first_name", "second_name", "age", "market_value_in_eur"]
].to_string())


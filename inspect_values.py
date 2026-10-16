from pathlib import Path
import pandas as pd

DATA_DIR = Path(__file__).parent / "data"

players = pd.read_csv(DATA_DIR / "players.csv.gz")
vals = pd.read_csv(DATA_DIR / "player_valuations.csv.gz")

print("PLAYERS", players.shape)
print(players.columns.tolist())
print(players.head(3).T)

print("\nVALUATIONS", vals.shape)
print(vals.columns.tolist())
print(vals.head(5))
print("\nDate range:", vals["date"].min(), "to", vals["date"].max())
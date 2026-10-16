from pathlib import Path
import pandas as pd

df = pd.read_csv(Path(__file__).parent / "data" / "player_history.csv")
print(df.shape)
print("Unique players:", df["player_id"].nunique())
print(df["season_name"].value_counts().sort_index())
print(df.sample(8, random_state=1)[
    ["season_name", "first_name", "second_name", "position",
     "minutes", "goals_scored", "assists"]
])
import requests
import pandas as pd

# API For Prem Stats

URL = "https://fantasy.premierleague.com/api/bootstrap-static/"

response = requests.get(URL, timeout=30)
response.raise_for_status()
data = response.json()

# Specify players and positions

players = pd.DataFrame(data["elements"])
positions = pd.DataFrame(data["element_types"])[["id", "singular_name_short"]]

players = players.merge(
    positions, left_on="element_type", right_on="id", suffixes=("", "_pos")
)

# Formatting

cols = ["first_name", "second_name", "singular_name_short", 
        "goals_scored", "assists", "minutes"]

print(players[cols].sort_values("goals_scored", ascending=False).head(10)) # Just 10 players for now
print(f"\nTotal Players: {len(players)}")
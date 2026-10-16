import os
import time
import requests
import pandas as pd

BASE = "https://fantasy.premierleague.com/api"

session = requests.Session()

# Fetch it normally, find player name, position, etc

bootstrap = session.get(f"{BASE}/bootstrap-static/",  timeout=30).json()
players = pd.DataFrame(bootstrap["elements"])
positions = pd.DataFrame(bootstrap["element_types"])
pos_map = dict(zip(positions["id"], positions["singular_name_short"]))
players["position"] = players["element_type"].map(pos_map)

# Now we need to loop over every player and grab their past seasons

rows = []
total = len(players)

for i, p in enumerate(players.itertuples(), start=1):
    try:
        r = session.get(f"{BASE}/element-summary/{p.id}/", timeout=30)
        r.raise_for_status()
        history = r.json().get("history_past", []) # Notes down history of past seasons
    except requests.RequestException as e:
        print(f"Skipping {p.first_name} {p.second_name} due to error: {e}") # Error Case
        continue
    
    for season in history:
        season["player_id"] = p.id
        season["first_name"] = p.first_name
        season["second_name"] = p.second_name
        season["position"] = p.position
        rows.append(season)
        
    if i % 50 == 0: # Prints out every 50 players to make sure the program runs properly
        print(f"{i}/{total} players done")
    time.sleep(0.3) # Sleep to avoid hitting the API too hard
    
    # Now we need to save to disk so we only download it once
    
history_df = pd.DataFrame(rows)
os.makedirs("data", exist_ok=True)
history_df.to_csv("data/player_history.csv", index=False)
    
print(f"\nSaved {len(history_df)} player season rows")
print(history_df.columns.tolist())
print(history_df.head())

        
# File used for retreiving .gz files for players and their valuations
# These come from the David Caribou Repo, Last Updated in July 2026

from pathlib import Path
import requests

DATA_DIR = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)

BASE = "https://pub-e682421888d945d684bcae8890b0ec20.r2.dev/data"
FILES = ["players.csv.gz", "player_valuations.csv.gz"]

for name in FILES:
    url = f"{BASE}/{name}"
    out = DATA_DIR / name
    r = requests.get(url, timeout=120)
    if r.status_code != 200:
        print(f"FAILED {name}: HTTP {r.status_code}")
        continue
    out.write_bytes(r.content)
    print(f"Saved {name} ({len(r.content) / 1e6:.1f} MB)")
    
    
"""Download club badges and player photos into assets/ (run once, locally).

    python fetch_assets.py

Badges  -> assets/badges/{ABBR}.png        (one per club)
Photos  -> assets/players/{element_code}.png (one per player in predictions.csv)

Existing files are skipped, so it is safe to re-run. Anything that fails keeps
the app's built-in fallback (a coloured shield or a silhouette), so the app
never breaks if a download does. Images belong to their owners; this is for
non-commercial portfolio use only.
"""
import time
from pathlib import Path

import pandas as pd
import requests

from clubs import CLUBS

ROOT = Path(__file__).parent
BADGES = ROOT / "assets" / "badges"
PLAYERS = ROOT / "assets" / "players"
FPL = "https://fantasy.premierleague.com/api/bootstrap-static/"
HEADERS = {"User-Agent": "Mozilla/5.0 (portfolio project)"}

BADGE_URLS = [
    "https://resources.premierleague.com/premierleague/badges/100/t{code}@x2.png",
    "https://resources.premierleague.com/premierleague/badges/70/t{code}.png",
    "https://resources.premierleague.com/premierleague25/badges/100/t{code}.png",
]
PHOTO_URLS = [
    "https://resources.premierleague.com/premierleague25/photos/players/110x140/{code}.png",
    "https://resources.premierleague.com/premierleague/photos/players/250x250/p{code}.png",
]


def download(urls, code, dest):
    for pattern in urls:
        try:
            r = requests.get(pattern.format(code=code), headers=HEADERS, timeout=15)
        except requests.RequestException:
            continue
        if r.status_code == 200 and r.content[:4] == b"\x89PNG":
            dest.write_bytes(r.content)
            return True
    return False


def live_badge_codes():
    """FPL team code by 3-letter short name (keeps badge ids current)."""
    try:
        teams = requests.get(FPL, headers=HEADERS, timeout=20).json()["teams"]
        return {t["short_name"]: t["code"] for t in teams}
    except Exception as exc:  # network or schema change: use the table in clubs.py
        print(f"Could not read live club codes ({exc}); using clubs.py")
        return {}


def main():
    BADGES.mkdir(parents=True, exist_ok=True)
    PLAYERS.mkdir(parents=True, exist_ok=True)

    live = live_badge_codes()
    failed_badges = []
    for name, (_short, abbr, code, _colour) in CLUBS.items():
        dest = BADGES / f"{abbr}.png"
        if dest.exists():
            continue
        if not download(BADGE_URLS, live.get(abbr, code), dest) and not download(BADGE_URLS, code, dest):
            failed_badges.append(name)
    print(f"Badges: {len(list(BADGES.glob('*.png')))} on disk, {len(failed_badges)} failed {failed_badges}")

    df = pd.read_csv(ROOT / "data" / "predictions.csv")
    codes = sorted(int(c) for c in df["element_code"].dropna().unique())
    todo = [c for c in codes if not (PLAYERS / f"{c}.png").exists()]
    print(f"Photos: {len(codes)} players, {len(todo)} to download")
    failed = []
    for i, code in enumerate(todo, 1):
        if not download(PHOTO_URLS, code, PLAYERS / f"{code}.png"):
            failed.append(code)
        if i % 50 == 0:
            print(f"  {i}/{len(todo)}")
        time.sleep(0.05)
    print(f"Photos done: {len(codes) - len(failed)} available, {len(failed)} will use the silhouette")


if __name__ == "__main__":
    main()
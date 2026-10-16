"""Club metadata: display names, badge ids and colours.

Keys are the club names exactly as Transfermarkt writes them (that is what
`club` holds in predictions.csv). `code` is the id the Premier League uses for
its badge images; fetch_assets.py also refreshes it from the live FPL API.
Clubs that are not in this table (Hull, Middlesbrough...) still work: they get
a grey fallback badge built from their name.
"""

CLUBS = {
    #  Transfermarkt name          short name       abbr   badge code  colour
    "Arsenal FC":                  ("Arsenal",       "ARS", 3,   "#EF0107"),
    "Aston Villa":                 ("Aston Villa",   "AVL", 7,   "#670E36"),
    "AFC Bournemouth":             ("Bournemouth",   "BOU", 91,  "#DA291C"),
    "Brentford FC":                ("Brentford",     "BRE", 94,  "#E30613"),
    "Brighton & Hove Albion":      ("Brighton",      "BHA", 36,  "#0057B8"),
    "Burnley FC":                  ("Burnley",       "BUR", 90,  "#6C1D45"),
    "Chelsea FC":                  ("Chelsea",       "CHE", 8,   "#034694"),
    "Crystal Palace":              ("Crystal Palace", "CRY", 31, "#1B458F"),
    "Everton FC":                  ("Everton",       "EVE", 11,  "#003399"),
    "Fulham FC":                   ("Fulham",        "FUL", 54,  "#1A1A1A"),
    "Leeds United":                ("Leeds",         "LEE", 2,   "#1D428A"),
    "Leicester City":              ("Leicester",     "LEI", 13,  "#003090"),
    "Liverpool FC":                ("Liverpool",     "LIV", 14,  "#C8102E"),
    "Manchester City":             ("Man City",      "MCI", 43,  "#6CABDD"),
    "Manchester United":           ("Man United",    "MUN", 1,   "#DA291C"),
    "Newcastle United":            ("Newcastle",     "NEW", 4,   "#241F20"),
    "Nottingham Forest":           ("Nott'm Forest", "NFO", 17,  "#DD0000"),
    "Southampton FC":              ("Southampton",   "SOU", 20,  "#D71920"),
    "Sunderland AFC":              ("Sunderland",    "SUN", 56,  "#EB172B"),
    "Tottenham Hotspur":           ("Spurs",         "TOT", 6,   "#132257"),
    "West Ham United":             ("West Ham",      "WHU", 21,  "#7A263A"),
    "Wolverhampton Wanderers":     ("Wolves",        "WOL", 39,  "#FDB913"),
    "Ipswich Town":                ("Ipswich",       "IPS", 40,  "#3A64A3"),
    "Luton Town":                  ("Luton",         "LUT", 102, "#F78F1E"),
    "Watford FC":                  ("Watford",       "WAT", 57,  "#FBEE23"),
    "Norwich City":                ("Norwich",       "NOR", 45,  "#00A650"),
    "Sheffield United":            ("Sheff Utd",     "SHU", 49,  "#EE2737"),
}

_FALLBACK_COLOUR = "#5B6B63"


def club_info(name):
    """Return {'short', 'abbr', 'code', 'color'} for a Transfermarkt club name."""
    name = "Unknown" if name is None else str(name)
    if name in CLUBS:
        short, abbr, code, color = CLUBS[name]
        return {"short": short, "abbr": abbr, "code": code, "color": color}
    short = name.replace(" FC", "").replace("AFC ", "").strip() or "Unknown"
    abbr = "".join(ch for ch in short.upper() if ch.isalnum())[:3] or "UNK"
    return {"short": short, "abbr": abbr, "code": None, "color": _FALLBACK_COLOUR}
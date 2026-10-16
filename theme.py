"""Look and feel for EPL's Value Gap: CSS, badges, photos and small HTML components.

Design idea: the market and the model are two teams, and every player is a fixture.
Values are shown as a scoreboard, clubs as a league table, the page as a pitch.
"""
from __future__ import annotations

import base64
import html
from functools import lru_cache
from pathlib import Path
from urllib.parse import quote

import altair as alt
import pandas as pd
import streamlit as st

from clubs import club_info
from logic import fmt_m, fmt_pct

ASSETS = Path(__file__).parent / "assets"

# Colour tokens (validated pairs: market-vs-model = ink/green, gap = red/blue)
PITCH = "#17803A"
PITCH_LIGHT = "#1B8A3F"
PITCH_DEEP = "#0B4A22"
GOLD = "#FFD21F"
NAVY = "#0C1F3A"
INK = "#16231C"
MUTED = "#5B6B63"
LINE = "#DCE4DF"
HOT = "#E34948"
COOL = "#2A78D6"
MARKET_INK = "#1F2D26"
MODEL_GREEN = "#168A3E"
NEUTRAL_BAR = "#BFCBC4"


# --------------------------------------------------------------------------
# Images: local files first, generated fallbacks second
# --------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def _data_uri(path: str, mtime: float) -> str:
    suffix = Path(path).suffix.lower().lstrip(".")
    mime = "image/svg+xml" if suffix == "svg" else f"image/{'jpeg' if suffix in ('jpg', 'jpeg') else suffix}"
    return f"data:{mime};base64," + base64.b64encode(Path(path).read_bytes()).decode()


def _svg_uri(svg: str) -> str:
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


def _text_on(hex_colour: str) -> str:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#111111" if (0.299 * r + 0.587 * g + 0.114 * b) > 150 else "#FFFFFF"


@lru_cache(maxsize=None)
def _fallback_badge(abbr: str, colour: str) -> str:
    fg = _text_on(colour)
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 72">'
        f'<path d="M32 3 L58 11 V36 C58 52 46 63 32 69 C18 63 6 52 6 36 V11 Z" fill="{colour}" '
        'stroke="rgba(0,0,0,0.28)" stroke-width="2"/>'
        f'<text x="32" y="43" text-anchor="middle" font-family="Arial, Helvetica, sans-serif" '
        f'font-weight="700" font-size="19" fill="{fg}">{html.escape(abbr)}</text></svg>'
    )
    return _svg_uri(svg)


def badge_src(club: str) -> str:
    info = club_info(club)
    path = ASSETS / "badges" / f"{info['abbr']}.png"
    if path.exists():
        return _data_uri(str(path), path.stat().st_mtime)
    return _fallback_badge(info["abbr"], info["color"])


@lru_cache(maxsize=None)
def _fallback_photo(initials: str, colour: str) -> str:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100">'
        f'<rect width="100" height="100" fill="{colour}" fill-opacity="0.16"/>'
        f'<circle cx="50" cy="40" r="17" fill="{colour}" fill-opacity="0.55"/>'
        f'<path d="M14 100 C14 70 32 60 50 60 C68 60 86 70 86 100 Z" fill="{colour}" fill-opacity="0.55"/>'
        '</svg>'
    )
    return _svg_uri(svg)


def photo_src(element_code, name: str, club: str) -> str:
    info = club_info(club)
    if element_code is not None and not pd.isna(element_code):
        path = ASSETS / "players" / f"{int(element_code)}.png"
        if path.exists():
            return _data_uri(str(path), path.stat().st_mtime)
    initials = "".join(w[0] for w in str(name).split()[:2]).upper()
    return _fallback_photo(initials, info["color"])


def badge_img(club: str, size: int = 22) -> str:
    return f'<img class="vg-badge" src="{badge_src(club)}" width="{size}" height="{size}" alt="">'


def photo_img(row, size: int = 44) -> str:
    src = photo_src(row.get("element_code"), row["player"], row["club"])
    colour = club_info(row["club"])["color"]
    return (f'<img class="vg-photo" src="{src}" width="{size}" height="{size}" alt="" '
            f'style="--club:{colour};width:{size}px;height:{size}px">')


# --------------------------------------------------------------------------
# CSS
# --------------------------------------------------------------------------
def _pitch_svg() -> str:
    line = 'fill="none" stroke="white" stroke-opacity="0.28" stroke-width="3"'
    parts = [
        f'<rect x="24" y="24" width="1152" height="472" {line}/>',
        f'<line x1="600" y1="24" x2="600" y2="496" {line}/>',
        f'<circle cx="600" cy="260" r="84" {line}/>',
        '<circle cx="600" cy="260" r="5" fill="white" fill-opacity="0.35"/>',
        f'<rect x="24" y="130" width="190" height="260" {line}/>',
        f'<rect x="24" y="195" width="70" height="130" {line}/>',
        f'<path d="M214 214 A84 84 0 0 1 214 306" {line}/>',
        '<circle cx="150" cy="260" r="4" fill="white" fill-opacity="0.35"/>',
        f'<rect x="986" y="130" width="190" height="260" {line}/>',
        f'<rect x="1106" y="195" width="70" height="130" {line}/>',
        f'<path d="M986 214 A84 84 0 0 0 986 306" {line}/>',
        '<circle cx="1050" cy="260" r="4" fill="white" fill-opacity="0.35"/>',
    ]
    svg = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 520" '
           'preserveAspectRatio="xMidYMid slice">' + "".join(parts) + "</svg>")
    return "data:image/svg+xml;utf8," + quote(svg)


CSS = """
@import url('https://fonts.googleapis.com/css2?family=Barlow+Condensed:ital,wght@0,600;0,700;1,700;1,800&display=swap');

:root{
  --vg-pitch:__PITCH__; --vg-pitch-light:__PITCH_LIGHT__; --vg-pitch-deep:__PITCH_DEEP__;
  --vg-gold:__GOLD__; --vg-navy:__NAVY__; --vg-ink:__INK__; --vg-muted:__MUTED__; --vg-line:__LINE__;
  --vg-hot:__HOT__; --vg-hot-ink:#B42525; --vg-hot-bg:#FDECEC;
  --vg-cool:__COOL__; --vg-cool-ink:#1B5BAA; --vg-cool-bg:#E8F0FB;
  --vg-display:"Barlow Condensed","Arial Narrow","Liberation Sans Narrow",sans-serif;
}

/* ---------- page frame ---------- */
[data-testid="stMainBlockContainer"], .block-container{
  max-width:1240px; padding-top:1.4rem; padding-bottom:4rem;
}
[data-testid="stHeader"]{ background:rgba(255,255,255,.92); border-bottom:1px solid var(--vg-line); }
[data-testid="stVerticalBlockBorderWrapper"]{ background:#fff; }

/* ---------- headings and small type ---------- */
.vg-h2{ font-family:var(--vg-display); font-weight:700; font-size:32px; line-height:1.05; margin:0 0 4px; color:var(--vg-ink); }
.vg-sub{ color:var(--vg-muted); font-size:15px; margin:0 0 14px; max-width:62ch; line-height:1.45; }
.vg-section{ margin:34px 0 10px; }
.vg-muted{ color:var(--vg-muted); }
.vg-sr{ position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); white-space:nowrap; }

/* ---------- hero ---------- */
.vg-hero > *{ min-width:0; }
.vg-hero{
  position:relative; overflow:hidden; border-radius:18px; color:#fff;
  padding:40px 44px 44px; display:grid; grid-template-columns:minmax(0,1.05fr) minmax(0,.95fr); gap:36px; align-items:center;
  background:
    url("__PITCH_SVG__") center/cover no-repeat,
    repeating-linear-gradient(90deg, var(--vg-pitch) 0 84px, var(--vg-pitch-light) 84px 168px);
}
.vg-hero h1{
  font-family:var(--vg-display); font-style:italic; font-weight:800; text-transform:uppercase;
  font-size:clamp(44px,6.2vw,92px); line-height:.88; overflow-wrap:anywhere; letter-spacing:-.005em; margin:0 0 18px; color:#fff;
  text-shadow:0 2px 0 rgba(0,0,0,.18); padding:0;
}
.vg-hero p{ font-size:18px; line-height:1.45; max-width:44ch; margin:0; color:rgba(255,255,255,.94); }
.vg-hero .vg-hero-note{ margin-top:14px; font-size:14px; color:rgba(255,255,255,.82); }

/* ---------- scoreboard ---------- */
.vg-board{
  background:var(--vg-navy); color:#fff; padding:16px 22px 22px; border-top:5px solid var(--vg-gold);
  clip-path:polygon(0 0,100% 0,100% calc(100% - 20px),calc(100% - 20px) 100%,0 100%);
  box-shadow:0 18px 40px rgba(0,0,0,.28);
}
.vg-board-title{ font-size:13px; color:rgba(255,255,255,.72); margin-bottom:6px; }
.vg-board-score{ display:grid; grid-template-columns:minmax(0,1fr) auto minmax(0,1fr); align-items:end; gap:8px; }
.vg-board-side{ text-align:center; }
.vg-board-label{ font-size:14px; font-weight:600; color:rgba(255,255,255,.8); margin-top:2px; }
.vg-digit{
  font-family:var(--vg-display); font-weight:800; font-style:italic; line-height:.92;
  font-size:clamp(34px,3.7vw,58px); font-variant-numeric:tabular-nums; white-space:nowrap;
}
.vg-board .market .vg-digit{ color:#fff; }
.vg-board .model .vg-digit{ color:var(--vg-gold); }
.vg-dash{ font-family:var(--vg-display); font-size:44px; line-height:1; opacity:.45; padding-bottom:18px; }
.vg-board-who{ display:flex; align-items:center; gap:12px; margin-top:16px; padding-top:14px; border-top:1px solid rgba(255,255,255,.14); }
.vg-board-who .name{ font-family:var(--vg-display); font-weight:700; font-size:26px; line-height:1; }
.vg-board-who .meta{ font-size:13px; color:rgba(255,255,255,.75); display:flex; align-items:center; gap:6px; margin-top:4px; }
.vg-board-gap{ margin-left:auto; }
.vg-board .vg-pill{ box-shadow:none; }

/* ---------- badges, photos, pills ---------- */
.vg-badge{ display:inline-block; object-fit:contain; vertical-align:middle; flex:none; }
.vg-photo{
  border-radius:50%; object-fit:cover; object-position:center top; flex:none;
  background:color-mix(in srgb, var(--club,#5B6B63) 14%, #fff); box-shadow:0 0 0 2px color-mix(in srgb, var(--club,#5B6B63) 55%, #fff);
}
.vg-pill{
  display:inline-flex; align-items:center; gap:5px; padding:3px 9px; border-radius:6px; white-space:nowrap;
  font-weight:700; font-size:14px; font-variant-numeric:tabular-nums;
}
.vg-pill.hot{ background:var(--vg-hot-bg); color:var(--vg-hot-ink); }
.vg-pill.cool{ background:var(--vg-cool-bg); color:var(--vg-cool-ink); }
.vg-pill.flat{ background:#EDF1EE; color:var(--vg-muted); }
.vg-board .vg-pill.hot{ background:var(--vg-hot); color:#fff; }
.vg-board .vg-pill.cool{ background:#5AA0F0; color:#08254A; }
.vg-pill small{ font-weight:600; opacity:.8; font-size:12px; }

/* ---------- KPI strip ---------- */
.vg-kpis{ display:grid; grid-template-columns:repeat(4,1fr); margin:22px 0 4px; border-top:1px solid var(--vg-line); border-bottom:1px solid var(--vg-line); }
.vg-kpi{ padding:16px 20px; border-left:1px solid var(--vg-line); }
.vg-kpi:first-child{ border-left:0; padding-left:2px; }
.vg-kpi b{ display:block; font-family:var(--vg-display); font-size:clamp(28px,3vw,42px); line-height:1; font-weight:700; color:var(--vg-ink); font-variant-numeric:tabular-nums; white-space:nowrap; }
.vg-kpi span{ font-size:14px; color:var(--vg-muted); }

/* ---------- fixtures ---------- */
.vg-fxhead{ display:grid; grid-template-columns:1fr auto auto; gap:14px; padding:0 4px 6px 4px; font-size:13px; color:var(--vg-muted); }
.vg-fxhead .sc{ width:150px; text-align:center; } .vg-fxhead .gp{ width:104px; text-align:right; }
.vg-fx{
  display:grid; grid-template-columns:auto 1fr auto auto; align-items:center; gap:14px;
  padding:10px 4px 10px 12px; border-top:1px solid var(--vg-line); position:relative;
}
.vg-fx::before{ content:""; position:absolute; left:0; top:10px; bottom:10px; width:4px; border-radius:2px; background:var(--club); }
.vg-fx:hover{ background:#F6F9F7; }
.vg-fx .name{ font-weight:700; font-size:16px; line-height:1.15; color:var(--vg-ink); }
.vg-fx .meta{ font-size:13px; color:var(--vg-muted); display:flex; align-items:center; gap:6px; margin-top:3px; }
.vg-sc{ width:150px; display:flex; justify-content:center; align-items:baseline; gap:8px; font-family:var(--vg-display); font-weight:700; font-size:26px; font-variant-numeric:tabular-nums; }
.vg-sc .mk{ color:var(--vg-ink); } .vg-sc .md{ color:__MODEL_GREEN__; } .vg-sc .dash{ color:#9AA8A0; font-size:20px; }
.vg-fx .gp{ width:104px; text-align:right; }
.vg-empty{ padding:22px 6px; color:var(--vg-muted); border-top:1px solid var(--vg-line); font-size:15px; }

/* ---------- league table ---------- */
.vg-table{ width:100%; border-collapse:collapse; font-size:15px; }
.vg-table th{ text-align:right; font-weight:600; font-size:13px; color:var(--vg-muted); padding:0 8px 8px; border-bottom:2px solid var(--vg-ink); }
.vg-table th:nth-child(1),.vg-table th:nth-child(2){ text-align:left; }
.vg-table td{ padding:7px 8px; border-bottom:1px solid var(--vg-line); text-align:right; font-variant-numeric:tabular-nums; }
.vg-table td:nth-child(1){ text-align:left; color:var(--vg-muted); width:28px; }
.vg-table td:nth-child(2){ text-align:left; }
.vg-table tr:hover td{ background:#F6F9F7; }
.vg-club{ display:flex; align-items:center; gap:10px; font-weight:600; }
.vg-gapcell{ display:flex; align-items:center; justify-content:flex-end; gap:8px; font-weight:700; }
.vg-gapbar{ display:inline-block; width:70px; height:6px; background:#EDF1EE; border-radius:3px; position:relative; }
.vg-gapbar i{ position:absolute; top:0; bottom:0; border-radius:3px; }
.vg-gapbar.hot i{ left:50%; background:var(--vg-hot); } .vg-gapbar.cool i{ right:50%; background:var(--vg-cool); }
.vg-gapbar::after{ content:""; position:absolute; left:50%; top:-2px; bottom:-2px; width:1px; background:#9AA8A0; }
.vg-pos-hot{ color:var(--vg-hot-ink); } .vg-pos-cool{ color:var(--vg-cool-ink); }

/* ---------- player header ---------- */
.vg-player{ display:flex; align-items:center; gap:22px; padding:6px 0 10px; }
.vg-player h2{ font-family:var(--vg-display); font-style:italic; font-weight:800; text-transform:uppercase; font-size:clamp(38px,5vw,60px); line-height:.95; margin:0; color:var(--vg-ink); padding:0; }
.vg-player .meta{ display:flex; align-items:center; gap:8px; margin-top:8px; font-size:16px; color:var(--vg-muted); flex-wrap:wrap; }

/* ---------- process steps ---------- */
.vg-steps{ display:grid; grid-template-columns:repeat(4,1fr); gap:0; margin:6px 0 4px; }
.vg-step{ padding:4px 22px 4px 0; position:relative; }
.vg-step .n{ display:inline-flex; width:30px; height:30px; border-radius:50%; background:var(--vg-pitch); color:#fff; font-family:var(--vg-display); font-weight:700; font-size:18px; align-items:center; justify-content:center; }
.vg-step h3{ font-family:var(--vg-display); font-size:23px; font-weight:700; margin:8px 0 4px; padding:0; color:var(--vg-ink); }
.vg-step p{ font-size:14.5px; line-height:1.45; color:var(--vg-muted); margin:0; }

/* ---------- misc ---------- */
.vg-note{ font-size:13.5px; color:var(--vg-muted); line-height:1.5; }
.vg-footer{ margin-top:48px; padding-top:18px; border-top:1px solid var(--vg-line); font-size:13px; color:var(--vg-muted); line-height:1.55; max-width:90ch; }
.vg-list{ margin:6px 0 0; padding-left:18px; color:var(--vg-ink); font-size:15px; line-height:1.55; }
.vg-list li{ margin-bottom:6px; }
.vg-callout{ border-left:4px solid var(--vg-gold); background:#FFFBE6; padding:12px 16px; border-radius:0 8px 8px 0; font-size:15px; line-height:1.5; color:var(--vg-ink); }


/* ---------- about ---------- */
.vg-about{ display:grid; grid-template-columns:minmax(0,340px) minmax(0,1fr); gap:44px; align-items:start; margin-top:28px; }
.vg-id{ background:var(--vg-navy); color:#fff; border-top:5px solid var(--vg-gold);
  clip-path:polygon(0 0,100% 0,100% calc(100% - 24px),calc(100% - 24px) 100%,0 100%); box-shadow:0 18px 40px rgba(0,0,0,.2); }
.vg-id .ph{ position:relative; aspect-ratio:4/5; background:var(--vg-pitch); overflow:hidden; }
.vg-id .ph img{ width:100%; height:100%; object-fit:cover; display:block; }
.vg-id .num{ position:absolute; right:14px; bottom:6px; font-family:var(--vg-display); font-style:italic; font-weight:800;
  font-size:92px; line-height:1; color:#fff; opacity:.92; text-shadow:0 2px 12px rgba(0,0,0,.45); }
.vg-id .cap{ padding:14px 18px 22px; }
.vg-id .cap b{ display:block; font-family:var(--vg-display); font-style:italic; text-transform:uppercase; font-weight:800; font-size:30px; line-height:1; }
.vg-id .cap span{ display:block; margin-top:4px; font-size:14px; color:rgba(255,255,255,.78); }
.vg-about h1{ font-family:var(--vg-display); font-style:italic; text-transform:uppercase; font-weight:800; padding:0;
  font-size:clamp(44px,5.6vw,84px); line-height:.9; margin:0 0 12px; color:var(--vg-ink); overflow-wrap:anywhere; }
.vg-about .lede{ font-size:21px; line-height:1.4; color:var(--vg-ink); margin:0 0 20px; max-width:34ch; font-weight:500; }
.vg-facts{ display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); border-top:1px solid var(--vg-line); border-bottom:1px solid var(--vg-line); margin:0 0 22px; }
.vg-facts div{ padding:12px 16px; border-left:1px solid var(--vg-line); }
.vg-facts div:first-child{ border-left:0; padding-left:2px; }
.vg-facts b{ display:block; font-family:var(--vg-display); font-size:23px; font-weight:700; line-height:1.1; color:var(--vg-ink); }
.vg-facts span{ font-size:13px; color:var(--vg-muted); }
.vg-about p.body{ font-size:16.5px; line-height:1.6; color:var(--vg-ink); max-width:62ch; margin:0 0 12px; }
.vg-links{ display:flex; flex-wrap:wrap; gap:10px; margin-top:20px; }
.vg-links a{ display:inline-block; padding:9px 18px; border-radius:999px; background:var(--vg-pitch); color:#fff !important; font-weight:600;
  font-size:15px; text-decoration:none !important; transition:background .15s; }
.vg-links a:hover{ background:var(--vg-pitch-deep); }
.vg-links a.alt{ background:#fff; color:var(--vg-pitch-deep) !important; box-shadow:inset 0 0 0 1.5px var(--vg-pitch); }
.vg-links a:focus-visible{ outline:3px solid var(--vg-gold); outline-offset:2px; }
.vg-two{ display:grid; grid-template-columns:minmax(0,1.1fr) minmax(0,.9fr); gap:28px; }
.vg-card{ background:#fff; border:1px solid var(--vg-line); border-radius:14px; padding:22px 24px; }
.vg-card h3{ font-family:var(--vg-display); font-size:28px; font-weight:700; margin:0 0 10px; padding:0; color:var(--vg-ink); }
.vg-card p{ font-size:15.5px; line-height:1.55; color:var(--vg-ink); margin:0; }
.vg-tl{ list-style:none; margin:0; padding:0 0 0 22px; border-left:3px solid var(--vg-pitch); }
.vg-tl li{ position:relative; padding:0 0 18px 14px; }
.vg-tl li:last-child{ padding-bottom:0; }
.vg-tl li::before{ content:""; position:absolute; left:-31px; top:5px; width:14px; height:14px; border-radius:50%; background:#fff; border:3px solid var(--vg-pitch); }
.vg-tl .yr{ font-size:13px; font-weight:600; color:var(--vg-pitch); }
.vg-tl .wh{ font-family:var(--vg-display); font-size:23px; font-weight:700; line-height:1.15; color:var(--vg-ink); }
.vg-tl .tx{ font-size:14.5px; color:var(--vg-muted); line-height:1.4; }
.vg-chips{ display:flex; flex-wrap:wrap; gap:8px; }
.vg-chips span{ padding:6px 12px; border-radius:8px; background:#EAF3EC; color:var(--vg-pitch-deep); font-size:14px; font-weight:600; }

/* ---------- responsive ---------- */
@media (max-width:900px){
  .vg-about,.vg-two{ grid-template-columns:1fr; gap:26px; } .vg-id{ max-width:320px; }
  .vg-table th:nth-child(3),.vg-table td:nth-child(3){ display:none; }
  .vg-table{ font-size:14px; } .vg-table td,.vg-table th{ padding-left:5px; padding-right:5px; }
  .vg-hero{ grid-template-columns:1fr; padding:28px 22px 30px; gap:22px; }
  .vg-kpis{ grid-template-columns:repeat(2,1fr); } .vg-kpi:nth-child(3){ border-left:0; padding-left:2px; }
  .vg-steps{ grid-template-columns:1fr 1fr; row-gap:18px; }
  .vg-fxhead{ display:none; }
  .vg-fx{ grid-template-columns:auto 1fr auto; } .vg-sc{ display:none; }
  .vg-player{ flex-direction:column; align-items:flex-start; }
}
@media (prefers-reduced-motion:no-preference){
  .vg-board{ animation:vg-rise .6s cubic-bezier(.2,.7,.2,1) both; }
  @keyframes vg-rise{ from{ transform:translateY(14px); opacity:0; } to{ transform:none; opacity:1; } }
}
"""


def inject_css() -> None:
    css = (CSS.replace("__PITCH_SVG__", _pitch_svg())
           .replace("__PITCH_LIGHT__", PITCH_LIGHT).replace("__PITCH_DEEP__", PITCH_DEEP)
           .replace("__PITCH__", PITCH).replace("__GOLD__", GOLD).replace("__NAVY__", NAVY)
           .replace("__INK__", INK).replace("__MUTED__", MUTED).replace("__LINE__", LINE)
           .replace("__HOT__", HOT).replace("__COOL__", COOL).replace("__MODEL_GREEN__", MODEL_GREEN))
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# --------------------------------------------------------------------------
# Altair theme
# --------------------------------------------------------------------------
def register_altair_theme() -> None:
    @alt.theme.register("value_gap", enable=True)
    def _theme() -> alt.theme.ThemeConfig:
        return {
            "config": {
                "background": "transparent",
                "view": {"stroke": None},
                "font": "Barlow, system-ui, sans-serif",
                "axis": {
                    "labelColor": MUTED, "titleColor": MUTED, "labelFontSize": 12, "titleFontSize": 12,
                    "titleFontWeight": 500, "gridColor": "#E8EEEA", "domainColor": "#C9D4CD",
                    "tickColor": "#C9D4CD", "titlePadding": 10,
                },
                "legend": {"labelColor": INK, "titleColor": MUTED, "labelFontSize": 13, "titleFontSize": 12, "symbolType": "circle"},
                "title": {"color": INK, "font": "Barlow Condensed, sans-serif", "fontSize": 18, "fontWeight": 700, "anchor": "start"},
            }
        }


# --------------------------------------------------------------------------
# HTML components
# --------------------------------------------------------------------------
def esc(x) -> str:
    return html.escape(str(x), quote=True)


def gap_pill(gap_m: float, gap_pct: float | None = None, with_pct: bool = False) -> str:
    if gap_m is None or abs(gap_m) < 0.05:
        return '<span class="vg-pill flat">level</span>'
    cls, arrow = ("hot", "▲") if gap_m > 0 else ("cool", "▼")
    words = "above" if gap_m > 0 else "below"
    pct = f' <small>{fmt_pct(gap_pct)}</small>' if with_pct and gap_pct is not None else ""
    return (f'<span class="vg-pill {cls}" title="Market value is {fmt_m(abs(gap_m))} {words} the model estimate">'
            f'<span aria-hidden="true">{arrow}</span>{fmt_m(abs(gap_m))}{pct}'
            f'<span class="vg-sr"> market {words} model</span></span>')


def kpi_strip(items: list[tuple[str, str]]) -> str:
    cells = "".join(f'<div class="vg-kpi"><b>{esc(v)}</b><span>{esc(label)}</span></div>' for v, label in items)
    return f'<div class="vg-kpis">{cells}</div>'


def section(title: str, sub: str = "") -> str:
    sub_html = f'<p class="vg-sub">{sub}</p>' if sub else ""
    return f'<div class="vg-section"><h2 class="vg-h2">{esc(title)}</h2>{sub_html}</div>'


def scoreboard(market: float, model: float, title: str, row=None, with_pct_gap: bool = True) -> str:
    who = ""
    if row is not None:
        gap = row["market_m"] - row["predicted_m"]
        who = (
            '<div class="vg-board-who">'
            f'{photo_img(row, 54)}'
            f'<div><div class="name">{esc(row["player"])}</div>'
            f'<div class="meta">{badge_img(row["club"], 16)} {esc(row["club_short"])} · {esc(row["position"])} · age {row["age"]:.0f}</div></div>'
            f'<div class="vg-board-gap">{gap_pill(gap, row["gap_pct"], with_pct_gap)}</div></div>'
        )
    return (
        '<div class="vg-board">'
        f'<div class="vg-board-title">{esc(title)}</div>'
        '<div class="vg-board-score">'
        f'<div class="vg-board-side market"><div class="vg-digit">{market:.1f}</div><div class="vg-board-label">Market, €M</div></div>'
        '<div class="vg-dash">–</div>'
        f'<div class="vg-board-side model"><div class="vg-digit">{model:.1f}</div><div class="vg-board-label">Model, €M</div></div>'
        '</div>' + who + '</div>'
    )


def estimate_board(model_m: float, low_m: float, high_m: float, market_m: float | None = None, name: str = "") -> str:
    """Scoreboard for the estimator page. With a reference player it shows market against model."""
    if market_m is not None:
        gap = market_m - model_m
        pct = (market_m / model_m - 1) * 100 if model_m else 0.0
        title = f"{name}: market value against your model setup" if name else "Market value against your setup"
        return (
            '<div class="vg-board">'
            f'<div class="vg-board-title">{esc(title)}</div>'
            '<div class="vg-board-score">'
            f'<div class="vg-board-side market"><div class="vg-digit">{market_m:.1f}</div><div class="vg-board-label">Market, €M</div></div>'
            '<div class="vg-dash">–</div>'
            f'<div class="vg-board-side model"><div class="vg-digit">{model_m:.1f}</div><div class="vg-board-label">Model, €M</div></div>'
            '</div>'
            f'<div class="vg-board-who"><div class="meta">Typical range for the model: {fmt_m(low_m)} to {fmt_m(high_m)}</div>'
            f'<div class="vg-board-gap">{gap_pill(gap, pct, True)}</div></div></div>'
        )
    return (
        '<div class="vg-board">'
        '<div class="vg-board-title">Model estimate for this setup</div>'
        '<div class="vg-board-score" style="grid-template-columns:1fr">'
        f'<div class="vg-board-side model"><div class="vg-digit">{model_m:.1f}</div><div class="vg-board-label">€ millions</div></div></div>'
        f'<div class="vg-board-who"><div class="meta">Typical range: {fmt_m(low_m)} to {fmt_m(high_m)}</div></div></div>'
    )


def fixtures(frame: pd.DataFrame, empty_message: str) -> str:
    if frame.empty:
        return f'<div class="vg-empty">{esc(empty_message)}</div>'
    rows = []
    for _, r in frame.iterrows():
        colour = club_info(r["club"])["color"]
        rows.append(
            f'<div class="vg-fx" style="--club:{colour}">'
            f'{photo_img(r, 46)}'
            f'<div><div class="name">{esc(r["player"])}</div>'
            f'<div class="meta">{badge_img(r["club"], 15)} {esc(r["club_short"])} · {esc(r["position"])} · age {r["age"]:.0f}</div></div>'
            f'<div class="vg-sc" title="Market value, then model estimate, in € millions">'
            f'<span class="mk">{r["market_m"]:.1f}</span><span class="dash">–</span><span class="md">{r["predicted_m"]:.1f}</span></div>'
            f'<div class="gp">{gap_pill(r["gap_m"], r["gap_pct"], True)}</div></div>'
        )
    head = ('<div class="vg-fxhead"><span>Player</span><span class="sc">Market – Model, €M</span>'
            '<span class="gp">Gap</span></div>')
    return head + "".join(rows)


def league_table(table: pd.DataFrame, top: int = 20) -> str:
    t = table.head(top)
    span = max(float(t["gap"].abs().max()), 1e-9)
    rows = []
    for i, r in enumerate(t.itertuples(), start=1):
        cls = "hot" if r.gap > 0 else "cool"
        width = min(abs(r.gap) / span, 1.0) * 50
        sign = "+" if r.gap > 0 else "-" if r.gap < 0 else ""
        rows.append(
            f'<tr><td>{i}</td><td><div class="vg-club">{badge_img(r.club, 24)}{esc(r.short)}</div></td>'
            f'<td>{r.players}</td><td>{r.market:,.0f}</td><td>{r.model:,.0f}</td>'
            f'<td><div class="vg-gapcell vg-pos-{cls}"><span class="vg-gapbar {cls}"><i style="width:{width:.0f}%"></i></span>'
            f'{sign}{abs(r.gap):,.0f}</div></td></tr>'
        )
    head = ('<table class="vg-table"><thead><tr><th>#</th><th>Club</th><th>Players</th>'
            '<th>Market €M</th><th>Model €M</th><th>Gap €M</th></tr></thead><tbody>')
    return head + "".join(rows) + "</tbody></table>"


def player_header(row) -> str:
    return (
        '<div class="vg-player">'
        f'{photo_img(row, 112)}'
        f'<div><h2>{esc(row["player"])}</h2>'
        f'<div class="meta">{badge_img(row["club"], 22)}<span>{esc(row["club"])}</span>'
        f'<span>·</span><span>{esc(row["position"])}</span><span>·</span><span>age {row["age"]:.0f}</span>'
        f'<span>·</span><span>{esc(row["season_name"])}</span></div></div></div>'
    )


def steps(items: list[tuple[str, str]]) -> str:
    cells = "".join(
        f'<div class="vg-step"><span class="n">{i}</span><h3>{esc(t)}</h3><p>{esc(d)}</p></div>'
        for i, (t, d) in enumerate(items, start=1)
    )
    return f'<div class="vg-steps">{cells}</div>'


@lru_cache(maxsize=4)
def _me_photo(mtime: float, path: str) -> str:
    """Your photo, shrunk to a web-friendly size so a 6 MB phone picture stays fast."""
    import io
    try:
        from PIL import Image, ImageOps
        im = ImageOps.exif_transpose(Image.open(path)).convert("RGB")
        im.thumbnail((900, 1125))
        buf = io.BytesIO()
        im.save(buf, "JPEG", quality=86)
        return "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()
    except Exception:
        return _data_uri(path, mtime)


def about_page(p: dict) -> str:
    """The About page as one block of HTML, built from profile.PROFILE."""
    photo = next((f for ext in ("jpg", "jpeg", "png", "webp") if (f := ASSETS / f"me.{ext}").exists()), None)
    if photo:
        src = _me_photo(photo.stat().st_mtime, str(photo))
    else:
        initials = "".join(w[0] for w in p.get("name", "").split()[:2]).upper() or "?"
        src = _fallback_photo(initials, PITCH)
    num = f'<div class="num">{esc(p["number"])}</div>' if p.get("number") else ""
    pos = p.get("position_played") or p.get("role", "")
    card = (f'<div class="vg-id"><div class="ph"><img src="{src}" alt="Portrait of {esc(p.get("name", ""))}">{num}</div>'
            f'<div class="cap"><b>{esc(p.get("name", ""))}</b><span>{esc(pos)}</span></div></div>')

    facts = "".join(f'<div><b>{esc(v)}</b><span>{esc(k)}</span></div>' for k, v in p.get("facts", []) if v)
    facts = f'<div class="vg-facts">{facts}</div>' if facts else ""
    bio = "".join(f'<p class="body">{esc(t)}</p>' for t in p.get("bio", []) if t)
    links = "".join(
        f'<a class="{"" if i == 0 else "alt"}" href="{esc(u)}" target="_blank" rel="noopener">{esc(l)}</a>'
        for i, (l, u) in enumerate(p.get("links", [])) if u
    )
    links = f'<div class="vg-links">{links}</div>' if links else ""
    lede = f'<p class="lede">{esc(p["tagline"])}</p>' if p.get("tagline") else ""
    right = f'<div><h1>{esc(p.get("name", ""))}</h1>{lede}{facts}{bio}{links}</div>'

    cards = ""
    if p.get("soccer"):
        items = "".join(
            f'<li><div class="yr">{esc(y)}</div><div class="wh">{esc(w)}</div><div class="tx">{esc(t)}</div></li>'
            for y, w, t in p["soccer"]
        )
        cards += f'<div class="vg-card"><h3>Soccer background</h3><ul class="vg-tl">{items}</ul></div>'
    side = ""
    if p.get("why"):
        side += f'<div class="vg-card"><h3>Why I built EPL&rsquo;s Value Gap</h3><p>{esc(p["why"])}</p></div>'
    if p.get("skills"):
        chips = "".join(f"<span>{esc(s)}</span>" for s in p["skills"])
        side += f'<div class="vg-card" style="margin-top:20px"><h3>Built with</h3><div class="vg-chips">{chips}</div></div>'
    lower = f'<div class="vg-two" style="margin-top:40px"><div>{cards}</div><div>{side}</div></div>' if (cards or side) else ""
    return f'<div class="vg-about">{card}{right}</div>{lower}'


def footer() -> str:
    return (
        '<div class="vg-footer"><b>About this project.</b> An independent portfolio project, not affiliated with '
        'the Premier League or any club. Player statistics come from the public Fantasy Premier League API; market '
        'values come from the open transfermarkt-datasets project (CC0). Club badges and player photos belong to '
        'their owners and are shown for non-commercial, illustrative use. "Over" and "under" valued means '
        'valued above or below what this simple model predicts, not a verdict on any player.</div>'
    )
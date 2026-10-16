"""EPL's Value Gap: what a linear regression model thinks Premier League players are worth,
versus what the transfer market says.

Run with:   streamlit run app.py
"""
from __future__ import annotations

import altair as alt
import numpy as np
import pandas as pd
import streamlit as st

import logic as L
import theme as T
from clubs import club_info

st.set_page_config(
    page_title="EPL's Value Gap",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="collapsed",
)
T.register_altair_theme()
T.inject_css()
_LOGO = T.ASSETS / "logo.svg"
if _LOGO.exists():
    st.logo(str(_LOGO), size="large")

PAGES: dict[str, st.Page] = {}


# ---------------------------------------------------------------------------
# Data access
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner="Loading data")
def get_data() -> pd.DataFrame:
    return L.load_predictions()


@st.cache_resource
def get_model() -> L.ValueModel | None:
    return L.ValueModel.load() if L.MODEL_PATH.exists() else None


def require_data() -> pd.DataFrame:
    if not L.DATA_PATH.exists():
        st.error("data/predictions.csv was not found. Run `python analyze.py` first, then reload this page.")
        st.stop()
    return get_data()


def require_model() -> L.ValueModel:
    model = get_model()
    if model is None:
        st.error("assets/model.json was not found. Run `python export_model.py` once, then reload this page.")
        st.stop()
    return model


# ---------------------------------------------------------------------------
# Shared widgets and charts
# ---------------------------------------------------------------------------
def season_picker(page: str) -> str:
    seasons = L.season_list(require_data())
    current = st.session_state.get("season", seasons[-1])
    if current not in seasons:
        current = seasons[-1]
    choice = st.segmented_control(
        "Season", seasons, default=current, required=True, key=f"season_{page}", label_visibility="collapsed"
    )
    st.session_state["season"] = choice
    return choice


def chart(c: alt.Chart | alt.LayerChart) -> None:
    st.altair_chart(c, width="stretch", theme=None)


def panel_title(title: str, sub: str = "") -> None:
    sub_html = f'<p class="vg-sub">{sub}</p>' if sub else ""
    st.html(f'<h2 class="vg-h2">{T.esc(title)}</h2>{sub_html}')


def log_ticks(lo: float, hi: float) -> list[float]:
    ticks = [0.2, 0.5, 1, 2, 5, 10, 20, 50, 100, 200]
    return [t for t in ticks if lo * 0.9 <= t <= hi * 1.1]


def diverging_bars(frame: pd.DataFrame, cat: str, val: str, axis_title: str, height: int | None = None,
                   sort: list[str] | None = None) -> alt.LayerChart:
    d = frame.copy()
    d["label"] = d[val].map(lambda v: f"{v:+.0f}%")
    d["dir"] = np.where(d[val] >= 0, "Adds value", "Reduces value")
    order = sort if sort is not None else list(d[cat])
    lo, hi = min(float(d[val].min()), 0.0), max(float(d[val].max()), 0.0)
    pad = (hi - lo) * 0.16 + 4
    x = alt.X(f"{val}:Q", title=axis_title, scale=alt.Scale(domain=[lo - pad, hi + pad], nice=False))
    base = alt.Chart(d).encode(y=alt.Y(f"{cat}:N", sort=order, title=None,
                                       axis=alt.Axis(labelLimit=240, ticks=False, domain=False, labelFontSize=13, labelColor=T.INK)))
    bars = base.mark_bar(size=16, cornerRadiusEnd=3).encode(
        x=x,
        color=alt.Color("dir:N", legend=None, scale=alt.Scale(domain=["Adds value", "Reduces value"],
                                                               range=[T.MODEL_GREEN, "#7A8A82"])),
        tooltip=[alt.Tooltip(f"{cat}:N", title=cat.title()), alt.Tooltip(f"{val}:Q", title=axis_title, format="+.1f")],
    )
    pos = base.mark_text(align="left", dx=5, fontWeight=600, color=T.INK).encode(x=alt.X(f"{val}:Q"), text="label:N") \
        .transform_filter(alt.datum[val] >= 0)
    neg = base.mark_text(align="right", dx=-5, fontWeight=600, color=T.INK).encode(x=alt.X(f"{val}:Q"), text="label:N") \
        .transform_filter(alt.datum[val] < 0)
    zero = alt.Chart(pd.DataFrame({"z": [0]})).mark_rule(color="#8A9A92").encode(x="z:Q")
    h = height if height else max(120, 34 * len(d) + 40)
    return (bars + pos + neg + zero).properties(height=h)


def factor_chart(breakdown: list[dict]) -> alt.LayerChart:
    d = pd.DataFrame(breakdown).rename(columns={"factor": "Factor", "effect_pct": "Effect (%)"})
    return diverging_bars(d, "Factor", "Effect (%)", "Effect on value versus an average player (%)")


def journey_chart() -> alt.LayerChart:
    rows = [{"id": i, "label": f"{i}  {name}", "cv": cv, "what": what} for i, name, what, cv, _, _ in L.MODEL_HISTORY]
    d = pd.DataFrame(rows)
    order = list(d["label"])
    d["final"] = np.where(d["id"] == L.FINAL_MODEL_ID, "Final model", "Earlier step")
    base = alt.Chart(d).encode(y=alt.Y("label:N", sort=order, title=None,
                                       axis=alt.Axis(ticks=False, domain=False, labelFontSize=13, labelColor=T.INK, labelLimit=260)))
    bars = base.mark_bar(size=18, cornerRadiusEnd=3).encode(
        x=alt.X("cv:Q", title="R², tested on players the model had not seen", scale=alt.Scale(domain=[0, 0.9])),
        color=alt.Color("final:N", legend=None, scale=alt.Scale(domain=["Final model", "Earlier step"],
                                                                 range=[T.MODEL_GREEN, T.NEUTRAL_BAR])),
        tooltip=[alt.Tooltip("label:N", title="Model"), alt.Tooltip("what:N", title="Change"), alt.Tooltip("cv:Q", title="R²", format=".3f")],
    )
    text = base.mark_text(align="left", dx=5, fontWeight=600, color=T.INK).encode(x="cv:Q", text=alt.Text("cv:Q", format=".2f"))
    return (bars + text).properties(height=250)


def to_table(view: pd.DataFrame):
    """Return (dataframe, column_config, styler) for the player table."""
    t = view.copy()
    t["Club"] = t["club"].map(T.badge_src)
    cols = {
        "Club": "Club", "player": "Player", "club_short": "Team", "position": "Pos", "age": "Age",
        "season_name": "Season", "minutes": "Minutes", "goals_scored": "Goals", "assists": "Assists",
        "market_m": "Market €M", "predicted_m": "Model €M", "gap_m": "Gap €M", "gap_pct": "Gap %",
    }
    keep = [c for c in cols if c in t.columns]
    t = t[keep].rename(columns=cols)
    cfg = {
        "Club": st.column_config.ImageColumn("", width="small"),
        "Age": st.column_config.NumberColumn(format="%.0f", width="small"),
        "Market €M": st.column_config.NumberColumn(format="%.1f"),
        "Model €M": st.column_config.NumberColumn(format="%.1f"),
        "Gap €M": st.column_config.NumberColumn(format="%+.1f"),
        "Gap %": st.column_config.NumberColumn(format="%+.0f%%"),
    }

    def colour(v):
        if pd.isna(v) or abs(v) < 0.05:
            return ""
        return f"color:{T.HOT if v > 0 else T.COOL};font-weight:600"

    styler = t.style.map(colour, subset=[c for c in ["Gap €M", "Gap %"] if c in t.columns])
    return styler, cfg


# ---------------------------------------------------------------------------
# Page: Home
# ---------------------------------------------------------------------------
def page_home() -> None:
    df = require_data()
    hn = L.headline_numbers(df)
    seasons = L.season_list(df)

    hero_slot = st.container()
    with st.container():
        left, right = st.columns([3, 2], vertical_alignment="bottom", gap="large")
        with left:
            season = season_picker("home")
        with right:
            labels = L.player_labels(df)
            ids = sorted(labels, key=lambda i: labels[i].lower())
            pick = st.selectbox(
                "Find a player", ids, index=None, format_func=lambda i: labels[i],
                placeholder="Search for any player", label_visibility="collapsed", key="home_search",
            )
    if pick is not None:
        st.session_state["focus_player"] = int(pick)
        st.switch_page(PAGES["players"])

    sdf = df[df["season_name"] == season]
    feature_row = sdf.loc[sdf["gap_m"].abs().idxmax()]
    with hero_slot:
        st.html(
            '<div class="vg-hero"><div>'
            '<h1>EPL&rsquo;s Value Gap</h1>'
            '<p>A model prices every Premier League player from what he does on the pitch, his age and his club. '
            'Then it shows where the transfer market disagrees.</p>'
            f'<p class="vg-hero-note">Built on {hn["rows"]:,} player-seasons from {seasons[0]} to {seasons[-1]}.</p></div>'
            + T.scoreboard(feature_row["market_m"], feature_row["predicted_m"],
                           f"Biggest disagreement in {season}", feature_row)
            + "</div>"
        )

    st.html(T.kpi_strip([
        (f"{hn['players']:,}", "players priced"),
        (f"{hn['r2']:.2f}", "R², tested on players the model had not seen"),
        (f"€{hn['mae']:.1f}M", "average miss"),
        (f"{hn['clubs']}", "clubs"),
    ]))

    # --- fixtures -------------------------------------------------------
    st.html(T.section(
        f"Biggest gaps in {season}",
        "Each player is a fixture: the market's value against the model's estimate, in € millions."))
    rank = st.segmented_control("Rank by", ["€ gap", "% gap"], default="€ gap", required=True, key="home_rank")
    by = "gap_m" if rank == "€ gap" else "gap_pct"
    over, under = L.split_gaps(sdf, 5, by)
    c1, c2 = st.columns(2, gap="large")
    with c1:
        with st.container(border=True):
            panel_title("Market pays more", "Valued above what stats, age and club predict.")
            st.html(T.fixtures(over, "No players in this season are valued above the model."))
    with c2:
        with st.container(border=True):
            panel_title("Market pays less", "Valued below what stats, age and club predict.")
            st.html(T.fixtures(under, "No players in this season are valued below the model."))

    # --- league table + charts -----------------------------------------
    st.html(T.section("Clubs and the model",
                      "Squad totals for the players in the data (450+ minutes in the season)."))
    t1, t2 = st.columns([7, 5], gap="large")
    with t1:
        with st.container(border=True):
            panel_title(f"Club table, {season}", "Ranked by total market value. Gap is market minus model.")
            st.html(T.league_table(L.club_table(sdf), top=20))
    with t2:
        with st.container(border=True):
            curve = L.age_curve(df)
            peak = int(curve.loc[curve["Market"].idxmax(), "Age"]) if not curve.empty else None
            panel_title("Value by age", f"Median market value peaks around {peak}, and the model follows it."
                        if peak else "Median value by age.")
            long = curve.melt("Age", ["Market", "Model"], var_name="Series", value_name="Median value (€M)")
            base = alt.Chart(long).encode(
                x=alt.X("Age:Q", scale=alt.Scale(zero=False), axis=alt.Axis(tickMinStep=1, format="d")),
                y=alt.Y("Median value (€M):Q"),
                color=alt.Color("Series:N", scale=alt.Scale(domain=["Market", "Model"], range=[T.MARKET_INK, T.MODEL_GREEN]),
                                legend=alt.Legend(orient="top", title=None)),
                tooltip=["Series:N", alt.Tooltip("Age:Q", format="d"), alt.Tooltip("Median value (€M):Q", format=".1f")],
            )
            chart(base.mark_line(strokeWidth=2.5, interpolate="monotone") + base.mark_circle(size=46, opacity=1).properties(height=230))
        with st.container(border=True):
            panel_title("How the model improved", "Each step added information. Step E was tried and dropped.")
            chart(journey_chart())
    st.html(T.footer())


# ---------------------------------------------------------------------------
# Page: Players
# ---------------------------------------------------------------------------
def page_players() -> None:
    df = require_data()
    model = get_model()
    labels = L.player_labels(df)
    ids = sorted(labels, key=lambda i: labels[i].lower())
    latest = L.season_list(df)[-1]
    default = st.session_state.get("focus_player")
    if default not in labels:
        default = int(df[df["season_name"] == latest].nlargest(1, "market_m")["player_id"].iloc[0])

    pid = st.selectbox("Player", ids, index=ids.index(default), format_func=lambda i: labels[i], key="players_pick",
                       label_visibility="collapsed", placeholder="Search for a player")
    st.session_state["focus_player"] = int(pid)

    rows = df[df["player_id"] == pid].sort_values("season_name").reset_index(drop=True)
    seasons = list(rows["season_name"])
    global_season = st.session_state.get("season", seasons[-1])
    start = global_season if global_season in seasons else seasons[-1]
    season = seasons[0]
    if len(seasons) > 1:
        season = st.segmented_control("Season", seasons, default=start, required=True, key="players_season",
                                      label_visibility="collapsed")
    else:
        season = seasons[0]
    row = rows[rows["season_name"] == season].iloc[0]

    st.html(T.player_header(row))
    gap = row["gap_m"]
    gap_text = "level with the model" if abs(gap) < 0.05 else f"{L.fmt_m(gap, signed=True)} ({L.fmt_pct(row['gap_pct'])})"
    minutes = f"{int(row['minutes']):,}" if "minutes" in row and pd.notna(row.get("minutes")) else "n/a"
    st.html(T.kpi_strip([
        (L.fmt_m(row["market_m"]), "Market value"),
        (L.fmt_m(row["predicted_m"]), "Model estimate"),
        (gap_text, "Market minus model"),
        (minutes, "Minutes played"),
    ]))

    c1, c2 = st.columns(2, gap="large")
    with c1:
        with st.container(border=True):
            panel_title("Market versus model", "One value per season. The model never saw this player when it made its estimate.")
            long = rows.melt("season_name", ["market_m", "predicted_m"], var_name="Series", value_name="Value (€M)")
            long["Series"] = long["Series"].map({"market_m": "Market", "predicted_m": "Model"})
            base = alt.Chart(long).encode(
                x=alt.X("season_name:N", title=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("Value (€M):Q", scale=alt.Scale(zero=True)),
                color=alt.Color("Series:N", scale=alt.Scale(domain=["Market", "Model"], range=[T.MARKET_INK, T.MODEL_GREEN]),
                                legend=alt.Legend(orient="top", title=None)),
                tooltip=[alt.Tooltip("season_name:N", title="Season"), "Series:N", alt.Tooltip("Value (€M):Q", format=".1f")],
            )
            chart(base.mark_line(strokeWidth=2.5) + base.mark_circle(size=80, opacity=1).properties(height=300))
    with c2:
        with st.container(border=True):
            panel_title(f"What drives the estimate, {season}",
                        "How much each factor moves the value compared with an average player in the data.")
            if model is None:
                st.info("Run `python export_model.py` to see the factor breakdown.")
            else:
                feats = L.feats_from_row(row, model)
                cg = row["club_group"] if "club_group" in row.index and pd.notna(row["club_group"]) else model.club_group_for(row["club"])
                bd = model.breakdown(feats, row["position"], row["season_name"], cg)
                chart(factor_chart(bd))
                st.html(f'<p class="vg-note">An average player in the data is worth about {L.fmt_m(model.average_player_m())}. '
                        'The factors multiply together to reach the model\'s estimate.</p>')

    with st.container(border=True):
        panel_title("Season by season")
        styler, cfg = to_table(rows.sort_values("season_name", ascending=False))
        st.dataframe(styler, column_config=cfg, hide_index=True, width="stretch")
    st.html(T.footer())


# ---------------------------------------------------------------------------
# Page: Explorer
# ---------------------------------------------------------------------------
def page_explorer() -> None:
    df = require_data()
    st.html('<h1 class="vg-h2" style="font-size:44px;margin:0 0 4px">Market explorer</h1>'
            '<p class="vg-sub">Filter by season, position, club, age and value, then see where the market and the model disagree.</p>')
    with st.container(border=True):
        a, b = st.columns([3, 2], vertical_alignment="bottom", gap="large")
        with a:
            season = season_picker("explorer")
        with b:
            query = st.text_input("Search by name", placeholder="Search by name", label_visibility="collapsed")
        sdf = df[df["season_name"] == season]
        p1, p2 = st.columns([2, 3], gap="large")
        with p1:
            positions = st.pills("Position", L.POSITIONS, selection_mode="multi", key="ex_pos",
                                 format_func=lambda p: L.POSITION_NAMES[p], default=None)
        with p2:
            club_names = sorted(sdf["club"].unique(), key=lambda c: club_info(c)["short"])
            clubs = st.multiselect("Club", club_names, key="ex_clubs", placeholder="All clubs",
                                   format_func=lambda c: club_info(c)["short"])
        s1, s2, s3 = st.columns([2, 2, 1.4], gap="large")
        with s1:
            amin, amax = float(np.floor(sdf["age"].min())), float(np.ceil(sdf["age"].max()))
            age_range = st.slider("Age", amin, amax, (amin, amax), step=1.0, key="ex_age")
        with s2:
            vmax = float(np.ceil(sdf["market_m"].max() / 5) * 5)
            value_range = st.slider("Market value (€M)", 0.0, vmax, (0.0, vmax), step=1.0, key="ex_value")
        with s3:
            rank = st.segmented_control("Rank by", ["€ gap", "% gap"], default="€ gap", required=True, key="ex_rank")

    view = sdf
    if positions:
        view = view[view["position"].isin(positions)]
    if clubs:
        view = view[view["club"].isin(clubs)]
    if query.strip():
        view = view[view["player"].str.contains(query.strip(), case=False, na=False, regex=False)]
    view = view[view["age"].between(*age_range) & view["market_m"].between(*value_range)]

    if view.empty:
        st.html('<div class="vg-callout">No players match these filters. Widen the age or value range, or clear the club filter.</div>')
        return

    st.html(T.kpi_strip([
        (f"{len(view)}", "players in view"),
        (L.fmt_m(float(view["market_m"].median())), "median market value"),
        (L.fmt_m(float(view["predicted_m"].median())), "median model estimate"),
        (L.fmt_m(float(view["gap_m"].abs().mean())), "average miss"),
    ]))

    by = "gap_m" if rank == "€ gap" else "gap_pct"
    over, under = L.split_gaps(view, 10, by)
    c1, c2 = st.columns(2, gap="large")
    with c1:
        with st.container(border=True):
            panel_title("Market pays more", "Valued above the model's estimate.")
            st.html(T.fixtures(over, "Nobody in this selection is valued above the model."))
    with c2:
        with st.container(border=True):
            panel_title("Market pays less", "Valued below the model's estimate.")
            st.html(T.fixtures(under, "Nobody in this selection is valued below the model."))

    with st.container(border=True):
        panel_title("Market against model", "Each dot is a player. Dots above the line are valued higher by the market than by the model.")
        d = view[["player", "club_short", "position", "age", "market_m", "predicted_m", "gap_m"]].copy()
        d["Direction"] = np.where(d["gap_m"] >= 0, "Market above model", "Market below model")
        lo = float(min(d["market_m"].min(), d["predicted_m"].min()))
        hi = float(max(d["market_m"].max(), d["predicted_m"].max()))
        dom = [max(lo * 0.7, 0.1), hi * 1.3]
        ticks = log_ticks(*dom)
        scale = alt.Scale(type="log", domain=dom, nice=False)
        axis = alt.Axis(values=ticks, labelExpr="'€' + datum.label + 'M'", format="~g")
        pts = alt.Chart(d).mark_circle(size=70, opacity=0.8, stroke="#fff", strokeWidth=1.2).encode(
            x=alt.X("predicted_m:Q", scale=scale, axis=axis, title="Model estimate"),
            y=alt.Y("market_m:Q", scale=scale, axis=axis, title="Market value"),
            color=alt.Color("Direction:N", scale=alt.Scale(domain=["Market above model", "Market below model"],
                                                            range=[T.HOT, T.COOL]),
                            legend=alt.Legend(orient="top", title=None)),
            tooltip=[alt.Tooltip("player:N", title="Player"), alt.Tooltip("club_short:N", title="Club"),
                     alt.Tooltip("position:N", title="Position"), alt.Tooltip("age:Q", title="Age", format=".0f"),
                     alt.Tooltip("market_m:Q", title="Market €M", format=".1f"),
                     alt.Tooltip("predicted_m:Q", title="Model €M", format=".1f"),
                     alt.Tooltip("gap_m:Q", title="Gap €M", format="+.1f")],
        )
        diag = alt.Chart(pd.DataFrame({"x": dom, "y": dom})).mark_line(color="#8A9A92", strokeWidth=1.5) \
            .encode(x=alt.X("x:Q", scale=scale), y=alt.Y("y:Q", scale=scale))
        chart((diag + pts).properties(height=420))

    with st.container(border=True):
        panel_title("All players in view", "Click a column header to sort.")
        styler, cfg = to_table(view.sort_values("market_m", ascending=False).head(500))
        st.dataframe(styler, column_config=cfg, hide_index=True, width="stretch", height=420)
    st.html(T.footer())


# ---------------------------------------------------------------------------
# Page: Estimator
# ---------------------------------------------------------------------------
EST_KEYS = ["est_pos", "est_club", "est_season", "est_age", "est_min", "est_goals", "est_assists",
            "est_cs", "est_saves", "est_bonus"]


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _typical_for_position() -> None:
    model = get_model()
    d = model.p["defaults"].get(st.session_state["est_pos"]) if model else None
    if d:
        st.session_state.update(
            est_age=_clamp(round(d["age"] * 2) / 2, 16.0, 40.0),
            est_min=int(_clamp(round(d["minutes"] / 30) * 30, 450, 3420)),
            est_goals=int(_clamp(round(d["goals"]), 0, 40)),
            est_assists=int(_clamp(round(d["assists"]), 0, 25)),
            est_cs=int(_clamp(round(d["clean_sheets"]), 0, 25)),
            est_saves=int(_clamp(round(d["saves"]), 0, 150)),
            est_bonus=int(_clamp(round(d["bonus"]), 0, 40)),
        )
    st.session_state["est_preset"] = None
    st.session_state["est_ref"] = None


def _load_preset() -> None:
    idx = st.session_state.get("est_preset")
    if idx is None:
        st.session_state["est_ref"] = None
        return
    df, model = get_data(), get_model()
    r = df.loc[idx]
    club_group = r["club_group"] if "club_group" in df.columns and pd.notna(r.get("club_group")) else model.club_group_for(r["club"])
    seasons = sorted(model.categorical["season_name"])

    def val(col):
        return float(r[col]) if col in df.columns and pd.notna(r[col]) else 0.0

    st.session_state.update(
        est_pos=r["position"],
        est_club=club_group if club_group in model.categorical["club_group"] else "Other",
        est_season=r["season_name"] if r["season_name"] in seasons else seasons[-1],
        est_age=_clamp(round(float(r["age"]) * 2) / 2, 16.0, 40.0),
        est_min=int(_clamp(round(val("minutes") / 30) * 30, 450, 3420)),
        est_goals=int(_clamp(val("goals_scored"), 0, 40)),
        est_assists=int(_clamp(val("assists"), 0, 25)),
        est_cs=int(_clamp(val("clean_sheets"), 0, 25)),
        est_saves=int(_clamp(val("saves"), 0, 150)),
        est_bonus=int(_clamp(val("bonus"), 0, 40)),
        est_ref=float(r["market_m"]),
        est_ref_name=f"{r['player']} ({r['season_name']})",
    )


def page_estimator() -> None:
    df = require_data()
    model = require_model()
    seasons = sorted(model.categorical["season_name"])
    club_levels = sorted(model.categorical["club_group"], key=lambda c: ("zzz" if c == "Other" else club_info(c)["short"]))
    defaults = dict(est_pos="MID", est_club=club_levels[0], est_season=seasons[-1], est_age=24.0, est_min=2400,
                    est_goals=6, est_assists=5, est_cs=0, est_saves=0, est_bonus=8)
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

    st.html('<h1 class="vg-h2" style="font-size:44px;margin:0 0 4px">Value estimator</h1>'
            '<p class="vg-sub">Set up a player-season and see what the model thinks he is worth. '
            'This uses the final model trained on every season.</p>')

    left, right = st.columns([5, 7], gap="large")
    with left:
        with st.container(border=True):
            order = df.sort_values("market_m", ascending=False).index.tolist()
            st.selectbox(
                "Start from a real player", order, index=None, key="est_preset", on_change=_load_preset,
                format_func=lambda i: f"{df.at[i, 'player']}  ·  {df.at[i, 'club_short']}  ·  {df.at[i, 'season_name']}",
                placeholder="Search for a player to load their numbers",
            )
            st.segmented_control("Position", L.POSITIONS, required=True, key="est_pos", on_change=_typical_for_position,
                                 format_func=lambda p: L.POSITION_NAMES[p])
            st.selectbox("Club", club_levels, key="est_club",
                         format_func=lambda c: "Other or smaller clubs" if c == "Other" else club_info(c)["short"])
            st.segmented_control("Season", seasons, required=True, key="est_season")
            st.slider("Age", 16.0, 40.0, step=0.5, key="est_age")
            st.slider("Minutes played", 450, 3420, step=30, key="est_min")
            g1, g2 = st.columns(2)
            with g1:
                st.slider("Goals", 0, 40, key="est_goals")
            with g2:
                st.slider("Assists", 0, 25, key="est_assists")
            with st.expander("Defending and goalkeeping"):
                st.slider("Clean sheets", 0, 25, key="est_cs")
                st.slider("Saves", 0, 150, key="est_saves")
                st.slider("Bonus points", 0, 40, key="est_bonus")

    s = st.session_state
    feats = L.build_features(s["est_age"], s["est_min"], s["est_goals"], s["est_assists"],
                             s["est_cs"], s["est_saves"], s["est_bonus"])
    value = model.predict_m(feats, s["est_pos"], s["est_season"], s["est_club"])
    low, high = model.interval_m(value)
    ref = s.get("est_ref")

    with right:
        st.html(T.estimate_board(value, low, high, ref, s.get("est_ref_name", "")))
        with st.container(border=True):
            panel_title("What drives this estimate", "Compared with an average player in the data.")
            chart(factor_chart(model.breakdown(feats, s["est_pos"], s["est_season"], s["est_club"])))
        sigma = float(np.exp(model.p["residual_sigma"]) - 1) * 100
        st.html(f'<p class="vg-note">The range shows where about two thirds of players land relative to the model: '
                f'the model is typically off by around {sigma:.0f}%. It cannot see injuries, contract length or hype.</p>')
    st.html(T.footer())


# ---------------------------------------------------------------------------
# Page: How it works
# ---------------------------------------------------------------------------
def page_method() -> None:
    df = require_data()
    model = get_model()
    hn = L.headline_numbers(df)
    st.html('<h1 class="vg-h2" style="font-size:44px;margin:0 0 4px">How it works</h1>'
            '<p class="vg-sub">A plain linear regression, built step by step, tested honestly and explained in full.</p>')
    st.html(T.steps([
        ("Collect", "Season stats for every current Premier League player come from the Fantasy Premier League API."),
        ("Match", "Players are matched by name to Transfermarkt values, with a manual list for the awkward ones."),
        ("Model", "A linear regression predicts the log of market value from output, age, position, club and season."),
        ("Compare", "Predictions come from folds where the player was held out, so the gap is a fair comparison."),
    ]))

    st.html(T.section("How the model improved",
                      "The first idea, goals and assists, explained under a fifth of the variation. Adding age, then the "
                      "club, did most of the work."))
    a, b = st.columns([6, 5], gap="large")
    with a:
        with st.container(border=True):
            chart(journey_chart())
    with b:
        with st.container(border=True):
            hist = pd.DataFrame(L.MODEL_HISTORY, columns=["Step", "Name", "What changed", "CV R²", "Test R²", "MAE €M"])
            st.dataframe(hist[["Step", "What changed", "CV R²", "MAE €M"]], hide_index=True, width="stretch",
                         column_config={"CV R²": st.column_config.NumberColumn(format="%.3f"),
                                        "MAE €M": st.column_config.NumberColumn(format="%.1f")})
            comp = pd.DataFrame(L.MODEL_COMPARISON, columns=["Model", "R²", "MAE €M"])
            st.html('<p class="vg-note" style="margin-top:12px"><b>Why linear regression?</b> With about a thousand rows, '
                    'flexible models overfit. The simple model scored best and its coefficients can be explained.</p>')
            st.dataframe(comp, hide_index=True, width="stretch",
                         column_config={"R²": st.column_config.NumberColumn(format="%.3f"),
                                        "MAE €M": st.column_config.NumberColumn(format="%.1f")})

    if model is not None:
        st.html(T.section("What the model learned", "Read straight from the fitted coefficients."))
        c1, c2 = st.columns(2, gap="large")
        with c1:
            with st.container(border=True):
                panel_title("The age curve", "Value compared with a 25-year-old, all else equal.")
                ac = model.age_curve_effect()
                peak = ac.loc[ac["Value vs age 25 (%)"].idxmax()]
                line = alt.Chart(ac).mark_line(strokeWidth=2.5, color=T.MODEL_GREEN).encode(
                    x=alt.X("Age:Q", scale=alt.Scale(zero=False), axis=alt.Axis(tickMinStep=1, format="d")),
                    y=alt.Y("Value vs age 25 (%):Q", axis=alt.Axis(format="+.0f")),
                    tooltip=[alt.Tooltip("Age:Q", format=".1f"), alt.Tooltip("Value vs age 25 (%):Q", format="+.0f")],
                )
                mark = alt.Chart(pd.DataFrame([peak])).mark_circle(size=90, color=T.MODEL_GREEN).encode(x="Age:Q", y="Value vs age 25 (%):Q")
                label = alt.Chart(pd.DataFrame([peak])).mark_text(dy=-14, fontWeight=600, color=T.INK).encode(
                    x="Age:Q", y="Value vs age 25 (%):Q", text=alt.value(f"Peak at {peak['Age']:.0f}"))
                zero = alt.Chart(pd.DataFrame({"z": [0]})).mark_rule(color="#8A9A92").encode(y="z:Q")
                chart((zero + line + mark + label).properties(height=280))
        with c2:
            with st.container(border=True):
                panel_title("Club premium", "Value compared with the average club, same player.")
                cp = model.club_premiums()
                cp["Club"] = cp["club"].map(lambda c: "Other or smaller clubs" if c == "Other" else club_info(c)["short"])
                chart(diverging_bars(cp[["Club", "premium_pct"]].rename(columns={"premium_pct": "Premium (%)"}),
                                     "Club", "Premium (%)", "Premium compared with the average club (%)",
                                     height=max(280, 22 * len(cp) + 40)))
        se = model.season_effects()
        st.html(T.kpi_strip([(f"{r.vs_first_pct:+.0f}%", f"{r.season} versus {se['season'].iloc[0]}")
                             for r in se.iloc[1:5].itertuples()] if len(se) >= 5 else
                            [(f"{r.vs_first_pct:+.0f}%", r.season) for r in se.itertuples()][:4]))
        st.html('<p class="vg-note">The same stats are worth more in later seasons because market values drift upward. '
                'The model has a season term so it does not mistake inflation for quality.</p>')

    st.html(T.section("Where the model is wrong", "Knowing the limits is part of the result."))
    d1, d2 = st.columns([5, 6], gap="large")
    with d1:
        with st.container(border=True):
            panel_title("Average miss by age", "Close to zero everywhere means no age group is systematically mispriced.")
            br = L.band_residuals(df)
            bars = alt.Chart(br).mark_bar(size=34, cornerRadiusEnd=3, color=T.MODEL_GREEN).encode(
                x=alt.X("Age band:N", sort=L.AGE_BAND_LABELS, title=None, axis=alt.Axis(labelAngle=0)),
                y=alt.Y("Average miss (%):Q", axis=alt.Axis(format="+.0f"), scale=alt.Scale(domain=[-30, 30])),
                tooltip=["Age band:N", alt.Tooltip("Average miss (%):Q", format="+.1f"), alt.Tooltip("n:Q", title="Players")],
            )
            chart((bars + alt.Chart(pd.DataFrame({"z": [0]})).mark_rule(color="#8A9A92").encode(y="z:Q")).properties(height=250))
    with d2:
        with st.container(border=True):
            panel_title("Limits you should know about")
            st.html(
                '<ul class="vg-list">'
                '<li><b>Potential and hype are invisible.</b> Teenagers the market loves can look overvalued, because the model only sees output, age and club.</li>'
                '<li><b>Timing.</b> Stats cover the whole season, but the club is the one at valuation time (January to June), so mid-season movers carry their new club\'s premium.</li>'
                '<li><b>Survivorship.</b> Only players in the current Fantasy pool appear, so players who left the league are missing from older seasons.</li>'
                '<li><b>Values are opinions.</b> Transfermarkt values are crowd-sourced and rounded. They are not fees paid.</li>'
                '<li><b>Small data.</b> About a thousand player-seasons. Clubs with fewer than ten rows are grouped as "Other".</li>'
                '<li><b>Top end.</b> Models in log space tend to pull the very highest values toward the middle.</li></ul>'
            )
    st.html(T.footer())


def page_about() -> None:
    from about_me import PROFILE
    st.html(T.about_page(PROFILE))
    st.html(T.footer())


# ---------------------------------------------------------------------------
# Navigation
# ---------------------------------------------------------------------------
PAGES["home"] = st.Page(page_home, title="Home", icon=":material/home:", url_path="home", default=True)
PAGES["players"] = st.Page(page_players, title="Players", icon=":material/person:", url_path="players")
PAGES["explorer"] = st.Page(page_explorer, title="Explorer", icon=":material/table_chart:", url_path="explorer")
PAGES["estimator"] = st.Page(page_estimator, title="Estimator", icon=":material/calculate:", url_path="estimator")
PAGES["method"] = st.Page(page_method, title="How it works", icon=":material/menu_book:", url_path="method")
PAGES["about"] = st.Page(page_about, title="About me", icon=":material/badge:", url_path="about")

try:
    nav = st.navigation(list(PAGES.values()), position="top")
except TypeError:  # very old Streamlit without a top bar
    nav = st.navigation(list(PAGES.values()))
nav.run()
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st

DATA_PATH = Path(__file__).parent / "data" / "predictions.csv"

st.set_page_config(page_title="PL Transfer Value Predictor", page_icon="⚽", layout="wide")


@st.cache_data
def load_data():
    df = pd.read_csv(DATA_PATH)
    df["club_short"] = (
        df["club"].str.replace(" FC", "", regex=False).str.replace("AFC ", "", regex=False)
    )
    return df


df = load_data()

# ---------- Sidebar filters ----------
st.sidebar.header("Filters")
season = st.sidebar.selectbox("Season", sorted(df["season_name"].unique(), reverse=True))
positions = st.sidebar.multiselect(
    "Position", ["GKP", "DEF", "MID", "FWD"], default=["GKP", "DEF", "MID", "FWD"]
)
club_options = sorted(df.loc[df["season_name"] == season, "club_short"].unique())
clubs = st.sidebar.multiselect("Club (empty = all)", club_options)
min_value = st.sidebar.slider("Minimum market value (€M)", 0, 100, 0, step=5)

view = df[(df["season_name"] == season) & (df["position"].isin(positions))]
if clubs:
    view = view[view["club_short"].isin(clubs)]
view = view[view["market_m"] >= min_value]

# ---------- Header ----------
st.title("Premier League Transfer Value Predictor")
st.caption(
    "A linear regression model estimates each player's Transfermarkt value from their stats, "
    "age, position and club. The gap shows where the market and the model disagree."
)

if view.empty:
    st.warning("No players match these filters.")
    st.stop()

c1, c2, c3, c4 = st.columns(4)
c1.metric("Players shown", len(view))
c2.metric("Median market value", f"€{view['market_m'].median():.0f}M")
c3.metric("Median model estimate", f"€{view['predicted_m'].median():.0f}M")
c4.metric("Average miss", f"€{view['gap_m'].abs().mean():.1f}M")

tab_gaps, tab_player, tab_model = st.tabs(["Biggest gaps", "Player lookup", "Model accuracy"])


def show_table(frame):
    out = frame[["player", "club_short", "position", "age", "market_m", "predicted_m", "gap_m", "gap_pct"]]
    out = out.rename(columns={
        "player": "Player", "club_short": "Club", "position": "Pos", "age": "Age",
        "market_m": "Market (€M)", "predicted_m": "Model (€M)",
        "gap_m": "Gap (€M)", "gap_pct": "Gap (%)",
    })
    st.dataframe(out.round(1), hide_index=True)


# ---------- Tab 1: biggest gaps ----------
with tab_gaps:
    st.write(
        "Gap = Transfermarkt value minus the model's estimate. "
        "A positive gap means the market values the player above what stats, age and club predict."
    )
    left, right = st.columns(2)
    with left:
        st.subheader("Market values him more")
        show_table(view.nlargest(10, "gap_m"))
    with right:
        st.subheader("Market values him less")
        show_table(view.nsmallest(10, "gap_m"))

# ---------- Tab 2: player lookup ----------
with tab_player:
    name = st.selectbox("Search for a player", sorted(df["player"].unique()))
    p = df[df["player"] == name].sort_values("season_name")

    long = p.melt(
        id_vars=["season_name"], value_vars=["market_m", "predicted_m"],
        var_name="series", value_name="value_m",
    )
    long["series"] = long["series"].map(
        {"market_m": "Transfermarkt", "predicted_m": "Model estimate"}
    )
    chart = (
        alt.Chart(long)
        .mark_line(point=True)
        .encode(
            x=alt.X("season_name:N", title="Season"),
            y=alt.Y("value_m:Q", title="Value (€M)"),
            color=alt.Color("series:N", title=None),
            tooltip=["season_name", "series", alt.Tooltip("value_m:Q", format=".1f")],
        )
        .properties(height=320)
    )
    st.altair_chart(chart)
    show_table(p)

# ---------- Tab 3: model accuracy ----------
with tab_model:
    st.write(
        "Every prediction comes from a model that never saw that player, "
        "so this is an honest test, not a fit to known answers."
    )
    scale = alt.Scale(type="log", domain=[0.2, 250])
    scatter = (
        alt.Chart(view)
        .mark_circle(size=60, opacity=0.65)
        .encode(
            x=alt.X("predicted_m:Q", scale=scale, title="Model estimate (€M, log scale)"),
            y=alt.Y("market_m:Q", scale=scale, title="Transfermarkt value (€M, log scale)"),
            color=alt.Color("position:N", title="Position"),
            tooltip=["player", "club_short", "position",
                     alt.Tooltip("market_m:Q", format=".1f"),
                     alt.Tooltip("predicted_m:Q", format=".1f")],
        )
    )
    diagonal = (
        alt.Chart(pd.DataFrame({"x": [0.2, 250], "y": [0.2, 250]}))
        .mark_line(color="gray", strokeDash=[4, 4])
        .encode(x=alt.X("x:Q", scale=scale), y=alt.Y("y:Q", scale=scale))
    )
    st.altair_chart((scatter + diagonal).properties(height=480))

    with st.expander("How the model improved"):
        st.dataframe(pd.DataFrame({
            "Model": ["A", "B", "C", "D", "F2 (final)"],
            "Features added": [
                "Goals, assists, position",
                "+ age, minutes, per-90 stats",
                "+ age curve, season, clean sheets/saves/bonus",
                "+ club",
                "+ age hinges, grouped rare clubs",
            ],
            "CV R²": [0.183, 0.430, 0.589, 0.728, 0.739],
            "MAE (€M)": [18.2, 16.1, 14.0, 10.7, 10.4],
        }), hide_index=True)
import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="Basho Tracker · Grand Sumo",
    page_icon="🏯",
    layout="wide"
)

BASE_URL = "https://sumo-api.com/api"
DIVISIONS = ["Makuuchi", "Juryo", "Makushita", "Sandanme", "Jonidan", "Jonokuchi"]
BASHO_MONTHS = [1, 3, 5, 7, 9, 11]


def get_recent_basho_options():
    options = []
    now = datetime.utcnow()
    year, month = now.year, now.month
    months = sorted(BASHO_MONTHS, reverse=True)
    count = 0
    y = year
    while count < 6:
        for m in months:
            if y == year and m > month:
                continue
            month_name = datetime(y, m, 1).strftime("%B")
            options.append((f"{month_name} {y}", f"{y}{str(m).zfill(2)}"))
            count += 1
            if count >= 6:
                break
        y -= 1
    return options


@st.cache_data(ttl=300)
def get_basho(basho_id):
    r = requests.get(f"{BASE_URL}/basho/{basho_id}")
    return r.json() if r.status_code == 200 else None


@st.cache_data(ttl=300)
def get_banzuke(basho_id, division):
    r = requests.get(f"{BASE_URL}/basho/{basho_id}/banzuke/{division}")
    return r.json() if r.status_code == 200 else None


@st.cache_data(ttl=300)
def get_torikumi(basho_id, division, day):
    r = requests.get(f"{BASE_URL}/basho/{basho_id}/torikumi/{division}/{day}")
    return r.json() if r.status_code == 200 else None


# ── Header ───────────────────────────────────────────────────────────────────
st.title("🏯 Basho Tracker")
st.caption("Live tournament standings and daily match results")
st.divider()

# ── Controls ──────────────────────────────────────────────────────────────────
basho_options = get_recent_basho_options()
labels = [o[0] for o in basho_options]
ids = [o[1] for o in basho_options]

ctrl1, ctrl2 = st.columns(2)
with ctrl1:
    selected_label = st.selectbox("Tournament", labels)
with ctrl2:
    selected_division = st.selectbox("Division", DIVISIONS)

selected_id = ids[labels.index(selected_label)]

# ── Basho Meta ────────────────────────────────────────────────────────────────
basho = get_basho(selected_id)

if basho:
    start = basho.get("startDate", "")[:10] if basho.get("startDate") else "—"
    end = basho.get("endDate", "")[:10] if basho.get("endDate") else "—"
    location = basho.get("location", "Japan") or "Japan"
    yusho_name = ""
    if basho.get("yusho") and isinstance(basho["yusho"], dict):
        yusho_name = basho["yusho"].get("shikonaEn", "")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("📅 Start", start)
    m2.metric("📅 End", end)
    m3.metric("📍 Location", location)
    m4.metric("🏆 Champion", yusho_name if yusho_name else "TBD")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📊  Standings", "🥊  Daily Bouts"])

# ── STANDINGS ─────────────────────────────────────────────────────────────────
with tab1:
    with st.spinner("Loading standings..."):
        banzuke = get_banzuke(selected_id, selected_division)

    if banzuke:
        east = banzuke.get("east", [])
        west = banzuke.get("west", [])

        rows = []
        for w in east:
            wins = w.get("wins", 0) or 0
            losses = w.get("losses", 0) or 0
            absences = w.get("absences", 0) or 0
            total = wins + losses
            pct = round((wins / total) * 100, 1) if total > 0 else None
            rows.append({
                "Rikishi": w.get("shikonaEn", "Unknown"),
                "Side": "East",
                "Rank": w.get("rank", ""),
                "W": wins,
                "L": losses,
                "Abs": absences,
                "Win %": pct,
            })
        for w in west:
            wins = w.get("wins", 0) or 0
            losses = w.get("losses", 0) or 0
            absences = w.get("absences", 0) or 0
            total = wins + losses
            pct = round((wins / total) * 100, 1) if total > 0 else None
            rows.append({
                "Rikishi": w.get("shikonaEn", "Unknown"),
                "Side": "West",
                "Rank": w.get("rank", ""),
                "W": wins,
                "L": losses,
                "Abs": absences,
                "Win %": pct,
            })

        if rows:
            df = pd.DataFrame(rows)
            active = df[df["W"] + df["L"] > 0].sort_values("W", ascending=False)
            inactive = df[df["W"] + df["L"] == 0]
            df = pd.concat([active, inactive]).reset_index(drop=True)

            st.subheader(f"{selected_division} · {selected_label}")
            st.caption(f"{len(df)} wrestlers · sorted by wins")

            def style_wins(val):
                if pd.isna(val) or val == 0:
                    return "color: #a0aec0"
                return "color: #276749; font-weight: bold"

            def style_losses(val):
                if pd.isna(val) or val == 0:
                    return "color: #a0aec0"
                return "color: #9b2335; font-weight: bold"

            def style_pct(val):
                if val is None or pd.isna(val):
                    return "color: #a0aec0"
                if val > 50:
                    return "color: #276749; font-weight: bold"
                elif val < 50:
                    return "color: #9b2335; font-weight: bold"
                return "color: #744210; font-weight: bold"

            styled = (
                df.style
                .applymap(style_wins, subset=["W"])
                .applymap(style_losses, subset=["L"])
                .applymap(style_pct, subset=["Win %"])
                .format({"Win %": lambda x: f"{x}%" if x is not None and not pd.isna(x) else "—"})
                .bar(subset=["Win %"], color=["#fed7d7", "#c6f6d5"], vmin=0, vmax=100)
            )

            st.dataframe(
                styled,
                use_container_width=True,
                hide_index=True,
                height=min(600, 36 * len(df) + 38),
            )
        else:
            st.info("No standings data yet for this tournament.")
    else:
        st.warning("Could not load standings.")

# ── DAILY BOUTS ───────────────────────────────────────────────────────────────
with tab2:
    day = st.slider("Day", min_value=1, max_value=15, value=1)

    with st.spinner(f"Loading Day {day}..."):
        torikumi = get_torikumi(selected_id, selected_division, day)

    if torikumi:
        matches = torikumi.get("torikumi", torikumi) if isinstance(torikumi, dict) else torikumi

        if matches:
            bout_rows = []
            for match in matches:
                east_name = match.get("eastShikonaEn", match.get("east", "?"))
                west_name = match.get("westShikonaEn", match.get("west", "?"))
                winner_id = match.get("winnerId")
                east_id = match.get("eastId")
                kimarite = match.get("kimarite", "—") or "—"

                east_won = bool(winner_id and winner_id == east_id)
                west_won = bool(winner_id and winner_id != east_id)

                if east_won:
                    winner = f"🏆 {east_name}"
                elif west_won:
                    winner = f"🏆 {west_name}"
                else:
                    winner = "—"

                bout_rows.append({
                    "East": east_name,
                    "Technique": kimarite,
                    "West": west_name,
                    "Winner": winner,
                })

            st.subheader(f"Day {day} · {selected_division}")
            st.caption(f"{len(bout_rows)} bouts")

            bouts_df = pd.DataFrame(bout_rows)
            st.dataframe(
                bouts_df,
                use_container_width=True,
                hide_index=True,
                height=min(600, 36 * len(bouts_df) + 38),
                column_config={
                    "East": st.column_config.TextColumn("East", width="medium"),
                    "Technique": st.column_config.TextColumn("Technique", width="small"),
                    "West": st.column_config.TextColumn("West", width="medium"),
                    "Winner": st.column_config.TextColumn("Winner", width="medium"),
                }
            )
        else:
            st.info(f"No results yet for Day {day}.")
    else:
        st.warning("Could not load match data.")

st.divider()
st.caption("Data from [sumo-api.com](https://sumo-api.com) · Refreshes every 5 minutes")

import streamlit as st
import requests
from datetime import datetime

st.set_page_config(
    page_title="Basho Tracker · Grand Sumo",
    page_icon="🏯",
    layout="wide"
)

BASE_URL = "https://sumo-api.com/api"

DIVISIONS = ["Makuuchi", "Juryo", "Makushita", "Sandanme", "Jonidan", "Jonokuchi"]

# Basho happen in Jan, Mar, May, Jul, Sep, Nov
BASHO_MONTHS = [1, 3, 5, 7, 9, 11]

def get_current_basho_id():
    """Work out the most recent or ongoing basho ID."""
    now = datetime.utcnow()
    year = now.year
    month = now.month
    # Find the most recent basho month
    recent = max((m for m in BASHO_MONTHS if m <= month), default=11)
    if recent == 11 and month < 11:
        year -= 1
        recent = 11
    return f"{year}{str(recent).zfill(2)}"

def get_recent_basho_options():
    """Build a list of the last 6 basho IDs as (label, id) tuples."""
    options = []
    now = datetime.utcnow()
    year = now.year
    month = now.month
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

def win_loss_bar(wins, losses):
    """Render a compact wins/losses display."""
    total = wins + losses
    if total == 0:
        return "—"
    return f"**{wins}W - {losses}L**"

def record_color(wins, losses):
    total = wins + losses
    if total == 0:
        return ""
    if wins > losses:
        return "🟢"
    elif losses > wins:
        return "🔴"
    else:
        return "🟡"

# --- Page ---
st.title("🏯 Basho Tracker")
st.caption("Live tournament standings and daily match results")

# --- Basho selector ---
basho_options = get_recent_basho_options()
labels = [o[0] for o in basho_options]
ids = [o[1] for o in basho_options]

col1, col2 = st.columns([2, 1])
with col1:
    selected_label = st.selectbox("Select Basho", labels)
with col2:
    selected_division = st.selectbox("Division", DIVISIONS)

selected_id = ids[labels.index(selected_label)]

# --- Basho Info ---
with st.spinner("Loading basho..."):
    basho = get_basho(selected_id)

if basho:
    info_cols = st.columns(4)
    info_cols[0].metric("Tournament", selected_label)
    if basho.get("startDate"):
        info_cols[1].metric("Start Date", basho["startDate"][:10])
    if basho.get("endDate"):
        info_cols[2].metric("End Date", basho["endDate"][:10])
    if basho.get("yusho") and basho["yusho"].get("shikonaEn"):
        info_cols[3].metric("🏆 Yusho", basho["yusho"]["shikonaEn"])

st.divider()

# --- Tabs: Standings | Daily Results ---
tab1, tab2 = st.tabs(["📊 Standings", "🥊 Daily Results"])

# --- Standings Tab ---
with tab1:
    with st.spinner("Loading standings..."):
        banzuke = get_banzuke(selected_id, selected_division)

    if banzuke:
        east = banzuke.get("east", [])
        west = banzuke.get("west", [])

        # Merge and sort by rank order
        wrestlers = []
        for w in east:
            w["side"] = "East"
            wrestlers.append(w)
        for w in west:
            w["side"] = "West"
            wrestlers.append(w)

        if wrestlers:
            # Sort by wins descending for leaderboard view
            wrestlers_with_record = [w for w in wrestlers if w.get("wins", 0) + w.get("losses", 0) > 0]
            wrestlers_no_record = [w for w in wrestlers if w.get("wins", 0) + w.get("losses", 0) == 0]
            wrestlers_sorted = sorted(wrestlers_with_record, key=lambda x: x.get("wins", 0), reverse=True) + wrestlers_no_record

            # Display as a clean table
            st.subheader(f"{selected_division} Division — {selected_label}")

            header_cols = st.columns([3, 2, 1, 1, 1])
            header_cols[0].markdown("**Rikishi**")
            header_cols[1].markdown("**Rank**")
            header_cols[2].markdown("**W**")
            header_cols[3].markdown("**L**")
            header_cols[4].markdown("**Result**")
            st.divider()

            for w in wrestlers_sorted:
                name = w.get("shikonaEn", "Unknown")
                rank = w.get("rank", "")
                side = w.get("side", "")
                wins = w.get("wins", 0)
                losses = w.get("losses", 0)
                absences = w.get("absences", 0)

                row = st.columns([3, 2, 1, 1, 1])
                row[0].write(f"{name} ({side})")
                row[1].write(rank)
                row[2].write(str(wins))
                row[3].write(str(losses))
                row[4].write(record_color(wins, losses))

                if absences > 0:
                    row[4].caption(f"Abs: {absences}")
        else:
            st.info("No banzuke data available yet for this tournament.")
    else:
        st.warning(f"No standings data found for {selected_label} — {selected_division}.")

# --- Daily Results Tab ---
with tab2:
    day = st.slider("Day", min_value=1, max_value=15, value=1)

    with st.spinner(f"Loading Day {day} results..."):
        torikumi = get_torikumi(selected_id, selected_division, day)

    if torikumi:
        matches = torikumi.get("torikumi", torikumi) if isinstance(torikumi, dict) else torikumi

        if matches:
            st.subheader(f"Day {day} — {selected_division} Division")

            for match in matches:
                east_name = match.get("eastShikonaEn", match.get("east", "?"))
                west_name = match.get("westShikonaEn", match.get("west", "?"))
                winner = match.get("winnerId")
                east_id = match.get("eastId")
                kimarite = match.get("kimarite", "")

                east_won = winner and winner == east_id
                west_won = winner and winner != east_id

                m_col1, m_col2, m_col3 = st.columns([2, 1, 2])

                # East side
                east_display = f"**{east_name}**" if east_won else east_name
                if east_won:
                    m_col1.success(f"🏆 {east_display}")
                else:
                    m_col1.write(f"{'🔴 ' if west_won else ''}{east_display}")

                # Kimarite in center
                m_col2.markdown(f"<div style='text-align:center; color: gray; font-size:0.8em'>{kimarite or 'vs'}</div>", unsafe_allow_html=True)

                # West side
                west_display = f"**{west_name}**"
                if west_won:
                    m_col3.success(f"🏆 {west_display}")
                else:
                    m_col3.write(f"{west_display}{'  🔴' if east_won else ''}")
        else:
            st.info(f"No match results for Day {day} yet.")
    else:
        st.warning(f"Could not load Day {day} data — results may not be available yet.")

st.divider()
st.caption("Data from [sumo-api.com](https://sumo-api.com) · Refreshes every 5 minutes")

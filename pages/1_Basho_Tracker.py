import streamlit as st
import requests
from datetime import datetime

st.set_page_config(
    page_title="Basho Tracker · Grand Sumo",
    page_icon="🏯",
    layout="wide"
)

# --- Custom CSS ---
st.markdown("""
<style>
    .basho-header {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
        padding: 2rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        color: white;
    }
    .basho-title {
        font-size: 2rem;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .basho-subtitle {
        color: #a0aec0;
        margin: 0.25rem 0 0 0;
        font-size: 0.95rem;
    }
    .kimarite-tag {
        background: #edf2f7;
        color: #4a5568;
        font-size: 0.75rem;
        padding: 2px 8px;
        border-radius: 12px;
        font-weight: 500;
    }
    .section-header {
        font-size: 1rem;
        font-weight: 700;
        color: #2d3748;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.75rem;
    }
</style>
""", unsafe_allow_html=True)

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

# --- Header ---
st.markdown("""
<div class="basho-header">
    <p class="basho-title">🏯 Basho Tracker</p>
    <p class="basho-subtitle">Tournament standings and daily match results</p>
</div>
""", unsafe_allow_html=True)

# --- Controls ---
basho_options = get_recent_basho_options()
labels = [o[0] for o in basho_options]
ids = [o[1] for o in basho_options]

ctrl1, ctrl2 = st.columns([2, 2])
with ctrl1:
    selected_label = st.selectbox("**Tournament**", labels)
with ctrl2:
    selected_division = st.selectbox("**Division**", DIVISIONS)

selected_id = ids[labels.index(selected_label)]

# --- Basho Meta Info ---
with st.spinner(""):
    basho = get_basho(selected_id)

if basho:
    meta_cols = st.columns(4)
    start = basho.get("startDate", "")[:10] if basho.get("startDate") else "—"
    end = basho.get("endDate", "")[:10] if basho.get("endDate") else "—"
    yusho_name = basho.get("yusho", {}).get("shikonaEn", "") if basho.get("yusho") else ""

    meta_cols[0].metric("Start", start)
    meta_cols[1].metric("End", end)
    meta_cols[2].metric("Location", basho.get("location", "Japan"))
    if yusho_name:
        meta_cols[3].metric("🏆 Champion", yusho_name)

st.divider()

# --- Tabs ---
tab1, tab2 = st.tabs(["📊  Standings", "🥊  Daily Bouts"])

# ---- STANDINGS ----
with tab1:
    with st.spinner("Loading standings..."):
        banzuke = get_banzuke(selected_id, selected_division)

    if banzuke:
        east = banzuke.get("east", [])
        west = banzuke.get("west", [])

        wrestlers = []
        for w in east:
            w["side"] = "E"
            wrestlers.append(w)
        for w in west:
            w["side"] = "W"
            wrestlers.append(w)

        active = [w for w in wrestlers if w.get("wins", 0) + w.get("losses", 0) > 0]
        inactive = [w for w in wrestlers if w.get("wins", 0) + w.get("losses", 0) == 0]
        sorted_wrestlers = sorted(active, key=lambda x: x.get("wins", 0), reverse=True) + inactive

        if sorted_wrestlers:
            # Column headers
            h1, h2, h3, h4, h5 = st.columns([3, 3, 1, 1, 2])
            h1.markdown("<span style='color:#718096;font-size:0.8rem;font-weight:700;text-transform:uppercase'>Rikishi</span>", unsafe_allow_html=True)
            h2.markdown("<span style='color:#718096;font-size:0.8rem;font-weight:700;text-transform:uppercase'>Rank</span>", unsafe_allow_html=True)
            h3.markdown("<span style='color:#276749;font-size:0.8rem;font-weight:700;text-transform:uppercase'>W</span>", unsafe_allow_html=True)
            h4.markdown("<span style='color:#9b2335;font-size:0.8rem;font-weight:700;text-transform:uppercase'>L</span>", unsafe_allow_html=True)
            h5.markdown("<span style='color:#718096;font-size:0.8rem;font-weight:700;text-transform:uppercase'>Record</span>", unsafe_allow_html=True)
            st.markdown("<hr style='border:none;border-top:1px solid #e2e8f0;margin:4px 0 8px 0'>", unsafe_allow_html=True)

            for w in sorted_wrestlers:
                name = w.get("shikonaEn", "Unknown")
                rank = w.get("rank", "")
                side = w.get("side", "")
                wins = w.get("wins", 0)
                losses = w.get("losses", 0)
                absences = w.get("absences", 0)
                total = wins + losses

                if total > 0:
                    pct = wins / total
                    if pct > 0.5:
                        record_html = f"<span style='color:#276749;font-weight:700'>{wins}–{losses}</span>"
                        indicator = "🟢"
                    elif pct < 0.5:
                        record_html = f"<span style='color:#9b2335;font-weight:700'>{wins}–{losses}</span>"
                        indicator = "🔴"
                    else:
                        record_html = f"<span style='color:#744210;font-weight:700'>{wins}–{losses}</span>"
                        indicator = "🟡"
                else:
                    record_html = "<span style='color:#a0aec0'>—</span>"
                    indicator = ""

                absence_note = f" <span style='color:#a0aec0;font-size:0.75rem'>({absences} abs)</span>" if absences > 0 else ""

                c1, c2, c3, c4, c5 = st.columns([3, 3, 1, 1, 2])
                c1.markdown(f"**{name}** <span style='color:#a0aec0;font-size:0.8rem'>({side})</span>", unsafe_allow_html=True)
                c2.markdown(f"<span style='color:#4a5568;font-size:0.9rem'>{rank}</span>", unsafe_allow_html=True)
                c3.markdown(f"<span style='color:#276749;font-weight:700'>{wins}</span>", unsafe_allow_html=True)
                c4.markdown(f"<span style='color:#9b2335;font-weight:700'>{losses}</span>", unsafe_allow_html=True)
                c5.markdown(f"{indicator} {record_html}{absence_note}", unsafe_allow_html=True)
                st.markdown("<hr style='border:none;border-top:1px solid #f7f7f7;margin:2px 0'>", unsafe_allow_html=True)
        else:
            st.info("No standings available yet for this tournament.")
    else:
        st.warning("Could not load standings data.")

# ---- DAILY BOUTS ----
with tab2:
    day = st.slider("**Day**", min_value=1, max_value=15, value=1)

    with st.spinner(f"Loading Day {day}..."):
        torikumi = get_torikumi(selected_id, selected_division, day)

    if torikumi:
        matches = torikumi.get("torikumi", torikumi) if isinstance(torikumi, dict) else torikumi

        if matches:
            st.markdown(f"<p class='section-header'>Day {day} · {selected_division} Division</p>", unsafe_allow_html=True)

            for match in matches:
                east_name = match.get("eastShikonaEn", match.get("east", "?"))
                west_name = match.get("westShikonaEn", match.get("west", "?"))
                winner_id = match.get("winnerId")
                east_id = match.get("eastId")
                kimarite = match.get("kimarite", "")

                east_won = bool(winner_id and winner_id == east_id)
                west_won = bool(winner_id and winner_id != east_id)
                completed = bool(winner_id)

                col1, col2, col3 = st.columns([5, 3, 5])

                with col1:
                    if east_won:
                        st.markdown(f"🏆 **{east_name}**")
                    elif completed:
                        st.markdown(f"<span style='color:#a0aec0'>{east_name}</span>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"**{east_name}**")

                with col2:
                    center_content = f"<span class='kimarite-tag'>{kimarite}</span>" if kimarite else "<span style='color:#cbd5e0'>vs</span>"
                    st.markdown(f"<div style='text-align:center;padding-top:4px'>{center_content}</div>", unsafe_allow_html=True)

                with col3:
                    if west_won:
                        st.markdown(f"<div style='text-align:right'>🏆 <b>{west_name}</b></div>", unsafe_allow_html=True)
                    elif completed:
                        st.markdown(f"<div style='text-align:right;color:#a0aec0'>{west_name}</div>", unsafe_allow_html=True)
                    else:
                        st.markdown(f"<div style='text-align:right'><b>{west_name}</b></div>", unsafe_allow_html=True)

                st.markdown("<hr style='border:none;border-top:1px solid #f0f0f0;margin:6px 0'>", unsafe_allow_html=True)
        else:
            st.info(f"No results yet for Day {day}.")
    else:
        st.warning("Could not load match data.")

st.markdown("<br>", unsafe_allow_html=True)
st.caption("Data from [sumo-api.com](https://sumo-api.com) · Refreshes every 5 minutes")

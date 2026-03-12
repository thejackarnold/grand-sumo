import streamlit as st
import requests

# --- Page Config ---
st.set_page_config(
    page_title="Grand Sumo",
    page_icon="🏯",
    layout="centered"
)

BASE_URL = "https://sumo-api.com/api"

# --- API Helpers ---
@st.cache_data(ttl=3600)
def get_all_rikishi():
    """Fetch all rikishi from the API."""
    response = requests.get(f"{BASE_URL}/rikishis")
    if response.status_code == 200:
        return response.json()
    return None

@st.cache_data(ttl=3600)
def get_rikishi_stats(rikishi_id):
    """Fetch stats for a specific rikishi."""
    response = requests.get(f"{BASE_URL}/rikishi/{rikishi_id}/stats")
    if response.status_code == 200:
        return response.json()
    return None

def get_rank_display(rank):
    """Return a friendly rank label."""
    if not rank:
        return "Unknown"
    rank_lower = rank.lower()
    if "yokozuna" in rank_lower:
        return f"🏆 {rank}"
    elif "ozeki" in rank_lower:
        return f"⭐ {rank}"
    elif "sekiwake" in rank_lower or "komusubi" in rank_lower:
        return f"🔷 {rank}"
    elif "maegashira" in rank_lower:
        return f"▪️ {rank}"
    else:
        return rank

# --- App ---
st.title("🏯 Grand Sumo")
st.caption("Rikishi stats powered by sumo-api.com")

st.divider()

# Load rikishi list
with st.spinner("Loading rikishi..."):
    data = get_all_rikishi()

if not data:
    st.error("Could not reach the Sumo API. Please try again later.")
    st.stop()

# Build a name -> rikishi dict for the dropdown
rikishi_list = data.get("records", data) if isinstance(data, dict) else data
name_to_rikishi = {r.get("shikonaEn", "Unknown"): r for r in rikishi_list if r.get("shikonaEn")}
sorted_names = sorted(name_to_rikishi.keys())

# --- Search ---
selected_name = st.selectbox(
    "Search for a rikishi",
    options=[""] + sorted_names,
    format_func=lambda x: "Select a wrestler..." if x == "" else x
)

if selected_name:
    rikishi = name_to_rikishi[selected_name]
    rikishi_id = rikishi.get("id")

    st.divider()

    # --- Profile Header ---
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader(selected_name)
        if rikishi.get("shikonaJp"):
            st.caption(rikishi["shikonaJp"])
        st.markdown(f"**Rank:** {get_rank_display(rikishi.get('currentRank', 'N/A'))}")
        if rikishi.get("heya"):
            st.markdown(f"**Stable:** {rikishi['heya']}")
        if rikishi.get("birthDate"):
            st.markdown(f"**Born:** {rikishi['birthDate'][:10]}")
        if rikishi.get("debut"):
            st.markdown(f"**Debut:** {rikishi['debut']}")

    with col2:
        if rikishi.get("heightCm"):
            st.metric("Height", f"{rikishi['heightCm']} cm")
        if rikishi.get("weightKg"):
            st.metric("Weight", f"{rikishi['weightKg']} kg")
        if rikishi.get("nationality"):
            st.metric("Nationality", rikishi["nationality"])

    # --- Career Stats ---
    st.divider()
    st.subheader("Career Stats")

    with st.spinner("Loading stats..."):
        stats = get_rikishi_stats(rikishi_id)

    if stats:
        s_col1, s_col2, s_col3, s_col4 = st.columns(4)

        basho = stats.get("basho", 0)
        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)
        absences = stats.get("absences", 0)
        total_bouts = wins + losses
        win_pct = round((wins / total_bouts) * 100, 1) if total_bouts > 0 else 0.0

        s_col1.metric("Tournaments", basho)
        s_col2.metric("Wins", wins)
        s_col3.metric("Losses", losses)
        s_col4.metric("Win %", f"{win_pct}%")

        if absences > 0:
            st.caption(f"Absences: {absences}")

        # Special achievements
        achievements = []
        if stats.get("yusho"):
            achievements.append(f"🏆 Yusho (Championships): {stats['yusho']}")
        if stats.get("specialPrizes"):
            achievements.append(f"🎖️ Special Prizes: {stats['specialPrizes']}")
        if stats.get("kinboshi"):
            achievements.append(f"⭐ Kinboshi (Gold Stars): {stats['kinboshi']}")

        if achievements:
            st.divider()
            st.subheader("Achievements")
            for a in achievements:
                st.markdown(a)
    else:
        st.info("No stats available for this rikishi.")

st.divider()
st.caption("Data from [sumo-api.com](https://sumo-api.com) · Built with Streamlit")

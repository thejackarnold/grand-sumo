import streamlit as st
import requests

st.set_page_config(
    page_title="Grand Sumo",
    page_icon="🏯",
    layout="wide"
)

BASE_URL = "https://sumo-api.com/api"


@st.cache_data(ttl=3600)
def get_all_rikishi():
    r = requests.get(f"{BASE_URL}/rikishis")
    return r.json() if r.status_code == 200 else None


@st.cache_data(ttl=3600)
def get_rikishi_stats(rikishi_id):
    r = requests.get(f"{BASE_URL}/rikishi/{rikishi_id}/stats")
    return r.json() if r.status_code == 200 else None


def get_rank_display(rank):
    if not rank:
        return "Unknown"
    rank_lower = rank.lower()
    if "yokozuna" in rank_lower:
        return f"👑 {rank}"
    elif "ozeki" in rank_lower:
        return f"⭐ {rank}"
    elif "sekiwake" in rank_lower or "komusubi" in rank_lower:
        return f"🔷 {rank}"
    elif "maegashira" in rank_lower:
        return f"▪️ {rank}"
    return rank


# ── Favorites init ────────────────────────────────────────────────────────────
if "favorites" not in st.session_state:
    st.session_state.favorites = []

# ── Header ────────────────────────────────────────────────────────────────────
st.title("🏯 Grand Sumo")
st.caption("Rikishi profiles, basho tracking, head-to-head stats and more")
st.divider()

# ── Load rikishi ──────────────────────────────────────────────────────────────
with st.spinner("Loading rikishi..."):
    data = get_all_rikishi()

if not data:
    st.error("Could not reach the Sumo API. Please try again later.")
    st.stop()

rikishi_list = data.get("records", data) if isinstance(data, dict) else data
name_to_rikishi = {r.get("shikonaEn", "Unknown"): r for r in rikishi_list if r.get("shikonaEn")}
sorted_names = sorted(name_to_rikishi.keys())

# ── Global search ─────────────────────────────────────────────────────────────
st.subheader("🔍 Rikishi Search")

search_col, fav_col = st.columns([3, 1])
with search_col:
    selected_name = st.selectbox(
        "Search for a rikishi",
        options=[""] + sorted_names,
        format_func=lambda x: "Search by name..." if x == "" else x,
        label_visibility="collapsed"
    )

if selected_name:
    rikishi = name_to_rikishi[selected_name]
    rikishi_id = rikishi.get("id")

    # Add/remove favorites
    with fav_col:
        if selected_name in st.session_state.favorites:
            if st.button("★ Remove Favourite", use_container_width=True):
                st.session_state.favorites.remove(selected_name)
                st.rerun()
        else:
            if st.button("☆ Add to Favourites", use_container_width=True):
                st.session_state.favorites.append(selected_name)
                st.rerun()

    st.divider()

    # ── Profile ───────────────────────────────────────────────────────────────
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
        if rikishi.get("nationality"):
            st.markdown(f"**Nationality:** {rikishi['nationality']}")

    with col2:
        if rikishi.get("heightCm"):
            st.metric("Height", f"{rikishi['heightCm']} cm")
        if rikishi.get("weightKg"):
            st.metric("Weight", f"{rikishi['weightKg']} kg")

    # ── Career stats ──────────────────────────────────────────────────────────
    st.divider()
    st.subheader("Career Stats")

    with st.spinner("Loading stats..."):
        stats = get_rikishi_stats(rikishi_id)

    if stats:
        basho_count = stats.get("basho", 0)
        wins = stats.get("wins", 0)
        losses = stats.get("losses", 0)
        absences = stats.get("absences", 0)
        total_bouts = wins + losses
        win_pct = round((wins / total_bouts) * 100, 1) if total_bouts > 0 else 0.0

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Tournaments", basho_count)
        s2.metric("Wins", wins)
        s3.metric("Losses", losses)
        s4.metric("Win %", f"{win_pct}%")

        if absences > 0:
            st.caption(f"Absences: {absences}")

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

    # ── Quick links ───────────────────────────────────────────────────────────
    st.divider()
    st.caption("Explore more: use the sidebar to view this wrestler's Kimarite breakdown or Performance Trend.")

# ── Favourites dashboard ──────────────────────────────────────────────────────
st.divider()
st.subheader("★ Favourites")

if not st.session_state.favorites:
    st.info("No favourites yet. Search for a rikishi above and click 'Add to Favourites'.")
else:
    fav_cols = st.columns(min(len(st.session_state.favorites), 3))
    for i, fav_name in enumerate(st.session_state.favorites):
        col = fav_cols[i % 3]
        fav_rikishi = name_to_rikishi.get(fav_name)
        if not fav_rikishi:
            continue
        fav_id = fav_rikishi.get("id")
        fav_stats = get_rikishi_stats(fav_id)

        with col:
            with st.container(border=True):
                st.markdown(f"**{fav_name}**")
                rank = fav_rikishi.get("currentRank", "—")
                st.caption(get_rank_display(rank))

                if fav_stats:
                    wins = fav_stats.get("wins", 0)
                    losses = fav_stats.get("losses", 0)
                    total = wins + losses
                    pct = round(wins / total * 100, 1) if total > 0 else 0
                    st.markdown(f"Career: **{wins}W – {losses}L** ({pct}%)")
                    if fav_stats.get("yusho"):
                        st.markdown(f"🏆 {fav_stats['yusho']} championship(s)")

                if st.button("Remove", key=f"remove_{fav_name}", use_container_width=True):
                    st.session_state.favorites.remove(fav_name)
                    st.rerun()

st.divider()
st.caption("Data from [sumo-api.com](https://sumo-api.com) · Built with Streamlit")

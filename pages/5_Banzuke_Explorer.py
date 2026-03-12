import streamlit as st
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(
    page_title="Banzuke Explorer · Grand Sumo",
    page_icon="🏯",
    layout="wide"
)

BASE_URL = "https://sumo-api.com/api"
DIVISIONS = ["Makuuchi", "Juryo", "Makushita", "Sandanme", "Jonidan", "Jonokuchi"]
BASHO_MONTHS = [1, 3, 5, 7, 9, 11]

RANK_ORDER = [
    "Yokozuna", "Ozeki", "Sekiwake", "Komusubi", "Maegashira",
    "Juryo", "Makushita", "Sandanme", "Jonidan", "Jonokuchi"
]

RANK_ICONS = {
    "Yokozuna": "👑",
    "Ozeki": "⭐",
    "Sekiwake": "🔷",
    "Komusubi": "🔹",
    "Maegashira": "▪️",
}


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


def rank_sort_key(rank_str):
    if not rank_str:
        return (99, 99)
    r = rank_str.strip()
    for i, base in enumerate(RANK_ORDER):
        if base.lower() in r.lower():
            # Extract number if present
            import re
            nums = re.findall(r'\d+', r)
            num = int(nums[0]) if nums else 0
            return (i, num)
    return (99, 99)


@st.cache_data(ttl=3600)
def get_banzuke(basho_id, division):
    r = requests.get(f"{BASE_URL}/basho/{basho_id}/banzuke/{division}")
    return r.json() if r.status_code == 200 else None


# ── Header ────────────────────────────────────────────────────────────────────
st.title("📋 Banzuke Explorer")
st.caption("Full division rankings, East vs West")
st.divider()

# ── Controls ──────────────────────────────────────────────────────────────────
basho_options = get_recent_basho_options()
labels = [o[0] for o in basho_options]
ids = [o[1] for o in basho_options]

c1, c2 = st.columns(2)
with c1:
    selected_label = st.selectbox("Tournament", labels)
with c2:
    selected_division = st.selectbox("Division", DIVISIONS)

selected_id = ids[labels.index(selected_label)]

# ── Fetch banzuke ─────────────────────────────────────────────────────────────
with st.spinner("Loading banzuke..."):
    banzuke = get_banzuke(selected_id, selected_division)

if not banzuke:
    st.warning("No banzuke data found.")
    st.stop()

east = banzuke.get("east", [])
west = banzuke.get("west", [])

if not east and not west:
    st.info("No wrestlers found for this division and tournament.")
    st.stop()

# ── Stats bar ─────────────────────────────────────────────────────────────────
st.subheader(f"{selected_division} Division · {selected_label}")

total = len(east) + len(west)
m1, m2, m3 = st.columns(3)
m1.metric("Total Wrestlers", total)
m2.metric("East Side", len(east))
m3.metric("West Side", len(west))

st.divider()

# ── Side-by-side banzuke view ─────────────────────────────────────────────────
st.subheader("East vs West")

# Sort each side by rank
def sort_side(wrestlers):
    return sorted(wrestlers, key=lambda w: rank_sort_key(w.get("rank", "")))

east_sorted = sort_side(east)
west_sorted = sort_side(west)

# Pair them up row by row
max_len = max(len(east_sorted), len(west_sorted))

# Header
h1, h2, h3, h4 = st.columns([3, 2, 2, 3])
h1.markdown("<span style='color:#718096;font-size:0.8rem;font-weight:700'>EAST</span>", unsafe_allow_html=True)
h2.markdown("<span style='color:#718096;font-size:0.8rem;font-weight:700'>RANK</span>", unsafe_allow_html=True)
h3.markdown("<span style='color:#718096;font-size:0.8rem;font-weight:700'>RANK</span>", unsafe_allow_html=True)
h4.markdown("<span style='color:#718096;font-size:0.8rem;font-weight:700'>WEST</span>", unsafe_allow_html=True)
st.markdown("<hr style='border:none;border-top:1px solid #e2e8f0;margin:4px 0 8px 0'>", unsafe_allow_html=True)

for i in range(max_len):
    e = east_sorted[i] if i < len(east_sorted) else None
    w = west_sorted[i] if i < len(west_sorted) else None

    e_name = e.get("shikonaEn", "—") if e else "—"
    e_rank = e.get("rank", "—") if e else "—"
    w_name = w.get("shikonaEn", "—") if w else "—"
    w_rank = w.get("rank", "—") if w else "—"

    # Rank icon
    icon = ""
    for base, ico in RANK_ICONS.items():
        if base.lower() in e_rank.lower():
            icon = ico
            break

    c1, c2, c3, c4 = st.columns([3, 2, 2, 3])
    c1.markdown(f"**{e_name}**" if e else "—")
    c2.markdown(f"{icon} {e_rank}" if e else "—")
    c3.markdown(f"{w_rank}" if w else "—")
    c4.markdown(f"**{w_name}**" if w else "—")

st.divider()

# ── Full searchable table ─────────────────────────────────────────────────────
st.subheader("Full Roster")

rows = []
for w in east:
    rows.append({
        "Rikishi": w.get("shikonaEn", "Unknown"),
        "Side": "East",
        "Rank": w.get("rank", ""),
        "Stable": w.get("heya", "—") or "—",
        "Nationality": w.get("nationality", "—") or "—",
    })
for w in west:
    rows.append({
        "Rikishi": w.get("shikonaEn", "Unknown"),
        "Side": "West",
        "Rank": w.get("rank", ""),
        "Stable": w.get("heya", "—") or "—",
        "Nationality": w.get("nationality", "—") or "—",
    })

df = pd.DataFrame(rows)
df["_sort"] = df["Rank"].apply(rank_sort_key)
df = df.sort_values("_sort").drop(columns=["_sort"]).reset_index(drop=True)

st.dataframe(
    df,
    use_container_width=True,
    hide_index=True,
    height=min(600, 36 * len(df) + 38),
)

st.divider()
st.caption("Data from [sumo-api.com](https://sumo-api.com)")

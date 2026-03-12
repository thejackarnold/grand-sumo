import streamlit as st
import requests
import pandas as pd

st.set_page_config(
    page_title="Head to Head · Grand Sumo",
    page_icon="🏯",
    layout="wide"
)

BASE_URL = "https://sumo-api.com/api"


@st.cache_data(ttl=3600)
def get_all_rikishi():
    r = requests.get(f"{BASE_URL}/rikishis")
    return r.json() if r.status_code == 200 else None


@st.cache_data(ttl=3600)
def get_h2h(id_a, id_b):
    r = requests.get(f"{BASE_URL}/rikishi/{id_a}/matches/{id_b}")
    return r.json() if r.status_code == 200 else None


# ── Header ────────────────────────────────────────────────────────────────────
st.title("🥊 Head to Head")
st.caption("Historical match record between any two rikishi")
st.divider()

# ── Load rikishi list ─────────────────────────────────────────────────────────
with st.spinner("Loading rikishi..."):
    data = get_all_rikishi()

if not data:
    st.error("Could not reach the Sumo API.")
    st.stop()

rikishi_list = data.get("records", data) if isinstance(data, dict) else data
name_to_rikishi = {r.get("shikonaEn", "Unknown"): r for r in rikishi_list if r.get("shikonaEn")}
sorted_names = sorted(name_to_rikishi.keys())

# ── Wrestler selectors ────────────────────────────────────────────────────────
col1, col2 = st.columns(2)
with col1:
    name_a = st.selectbox("Rikishi A", [""] + sorted_names, format_func=lambda x: "Select wrestler..." if x == "" else x, key="a")
with col2:
    name_b = st.selectbox("Rikishi B", [""] + sorted_names, format_func=lambda x: "Select wrestler..." if x == "" else x, key="b")

if not name_a or not name_b:
    st.info("Select two rikishi above to see their head-to-head record.")
    st.stop()

if name_a == name_b:
    st.warning("Please select two different rikishi.")
    st.stop()

rikishi_a = name_to_rikishi[name_a]
rikishi_b = name_to_rikishi[name_b]
id_a = rikishi_a.get("id")
id_b = rikishi_b.get("id")

# ── Fetch H2H ─────────────────────────────────────────────────────────────────
with st.spinner("Loading match history..."):
    h2h = get_h2h(id_a, id_b)

if not h2h:
    st.warning("No match data found between these two wrestlers.")
    st.stop()

matches = h2h.get("matches", h2h) if isinstance(h2h, dict) else h2h

if not matches:
    st.info(f"No recorded bouts between {name_a} and {name_b}.")
    st.stop()

# ── Tally wins ────────────────────────────────────────────────────────────────
wins_a = sum(1 for m in matches if m.get("winnerId") == id_a)
wins_b = sum(1 for m in matches if m.get("winnerId") == id_b)
total = wins_a + wins_b

# ── Summary scoreboard ────────────────────────────────────────────────────────
st.divider()
s1, s2, s3 = st.columns([2, 1, 2])

with s1:
    st.metric(name_a, f"{wins_a} wins", delta=f"{round(wins_a/total*100)}%" if total > 0 else "0%")

with s2:
    st.markdown(f"<h3 style='text-align:center;color:#718096;padding-top:1rem'>vs</h3>", unsafe_allow_html=True)
    st.markdown(f"<p style='text-align:center;color:#a0aec0;font-size:0.85rem'>{total} bouts total</p>", unsafe_allow_html=True)

with s3:
    st.metric(name_b, f"{wins_b} wins", delta=f"{round(wins_b/total*100)}%" if total > 0 else "0%")

# Win bar
if total > 0:
    pct_a = wins_a / total
    st.markdown(f"""
    <div style='margin: 1rem 0; border-radius: 8px; overflow: hidden; height: 20px; background: #fed7d7;'>
        <div style='width: {pct_a*100:.1f}%; height: 100%; background: #276749;'></div>
    </div>
    <div style='display:flex; justify-content:space-between; font-size:0.8rem; color:#718096;'>
        <span>{name_a} {pct_a*100:.1f}%</span>
        <span>{(1-pct_a)*100:.1f}% {name_b}</span>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Match history table ───────────────────────────────────────────────────────
st.subheader("Match History")

rows = []
for m in matches:
    winner_id = m.get("winnerId")
    if winner_id == id_a:
        winner = name_a
    elif winner_id == id_b:
        winner = name_b
    else:
        winner = "—"

    basho_id = m.get("bashoId", "")
    if basho_id and len(str(basho_id)) == 6:
        year = str(basho_id)[:4]
        month_num = int(str(basho_id)[4:])
        import calendar
        month_name = calendar.month_abbr[month_num]
        basho_label = f"{month_name} {year}"
    else:
        basho_label = str(basho_id)

    rows.append({
        "Basho": basho_label,
        "Day": m.get("day", "—"),
        "Division": m.get("division", "—"),
        "Technique": m.get("kimarite", "—") or "—",
        "Winner": f"🏆 {winner}" if winner != "—" else "—",
    })

if rows:
    df = pd.DataFrame(rows)
    # Most recent first
    df = df.iloc[::-1].reset_index(drop=True)

    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        height=min(600, 36 * len(df) + 38),
        column_config={
            "Basho": st.column_config.TextColumn("Basho", width="small"),
            "Day": st.column_config.NumberColumn("Day", width="small"),
            "Division": st.column_config.TextColumn("Division", width="small"),
            "Technique": st.column_config.TextColumn("Technique", width="medium"),
            "Winner": st.column_config.TextColumn("Winner", width="medium"),
        }
    )

st.divider()
st.caption("Data from [sumo-api.com](https://sumo-api.com)")

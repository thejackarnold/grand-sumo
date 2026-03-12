import streamlit as st
import requests
import pandas as pd

st.set_page_config(
    page_title="Performance Trend · Grand Sumo",
    page_icon="🏯",
    layout="wide"
)

BASE_URL = "https://sumo-api.com/api"
BASHO_MONTHS = [1, 3, 5, 7, 9, 11]


@st.cache_data(ttl=3600)
def get_all_rikishi():
    r = requests.get(f"{BASE_URL}/rikishis")
    return r.json() if r.status_code == 200 else None


@st.cache_data(ttl=3600)
def get_matches(rikishi_id):
    r = requests.get(f"{BASE_URL}/rikishi/{rikishi_id}/matches")
    return r.json() if r.status_code == 200 else None


def basho_label(basho_id):
    import calendar
    s = str(basho_id)
    if len(s) == 6:
        month_num = int(s[4:])
        return f"{calendar.month_abbr[month_num]} {s[:4]}"
    return s


# ── Header ────────────────────────────────────────────────────────────────────
st.title("📈 Performance Trend")
st.caption("Win/loss record across tournaments over time")
st.divider()

# ── Load rikishi ──────────────────────────────────────────────────────────────
with st.spinner("Loading rikishi..."):
    data = get_all_rikishi()

if not data:
    st.error("Could not reach the Sumo API.")
    st.stop()

rikishi_list = data.get("records", data) if isinstance(data, dict) else data
name_to_rikishi = {r.get("shikonaEn", "Unknown"): r for r in rikishi_list if r.get("shikonaEn")}
sorted_names = sorted(name_to_rikishi.keys())

col1, col2 = st.columns([3, 1])
with col1:
    selected_name = st.selectbox(
        "Select a rikishi",
        [""] + sorted_names,
        format_func=lambda x: "Select wrestler..." if x == "" else x
    )
with col2:
    num_basho = st.slider("Tournaments to show", min_value=5, max_value=30, value=15)

if not selected_name:
    st.info("Select a rikishi above to see their performance trend.")
    st.stop()

rikishi = name_to_rikishi[selected_name]
rikishi_id = rikishi.get("id")

# ── Fetch matches ─────────────────────────────────────────────────────────────
with st.spinner("Loading match history..."):
    match_data = get_matches(rikishi_id)

if not match_data:
    st.warning("No match data found.")
    st.stop()

matches = match_data.get("matches", match_data) if isinstance(match_data, dict) else match_data

if not matches:
    st.info(f"No match history found for {selected_name}.")
    st.stop()

# ── Aggregate by basho ────────────────────────────────────────────────────────
basho_records = {}
for m in matches:
    bid = m.get("bashoId")
    div = m.get("division", "")
    if not bid:
        continue
    if bid not in basho_records:
        basho_records[bid] = {"wins": 0, "losses": 0, "absences": 0, "division": div}
    winner_id = m.get("winnerId")
    if winner_id == rikishi_id:
        basho_records[bid]["wins"] += 1
    elif winner_id is None:
        basho_records[bid]["absences"] += 1
    else:
        basho_records[bid]["losses"] += 1

# Sort basho chronologically
sorted_basho = sorted(basho_records.keys())

# Take last N
sorted_basho = sorted_basho[-num_basho:]

rows = []
for bid in sorted_basho:
    rec = basho_records[bid]
    wins = rec["wins"]
    losses = rec["losses"]
    absences = rec["absences"]
    total = wins + losses
    pct = round(wins / total * 100, 1) if total > 0 else None
    rows.append({
        "Basho": basho_label(bid),
        "BashoId": bid,
        "Division": rec["division"],
        "W": wins,
        "L": losses,
        "Abs": absences,
        "Win %": pct,
        "Record": f"{wins}–{losses}" if total > 0 else "—",
    })

df = pd.DataFrame(rows)

if df.empty:
    st.info("No tournament data to display.")
    st.stop()

# ── Summary metrics ───────────────────────────────────────────────────────────
st.subheader(f"{selected_name} — Last {len(df)} Tournaments")

total_wins = df["W"].sum()
total_losses = df["L"].sum()
total_bouts = total_wins + total_losses
overall_pct = round(total_wins / total_bouts * 100, 1) if total_bouts > 0 else 0

# Streak calc
streak = 0
streak_type = ""
for _, row in df.iloc[::-1].iterrows():
    if row["W"] > row["L"]:
        if streak_type == "winning" or streak_type == "":
            streak += 1
            streak_type = "winning"
        else:
            break
    elif row["L"] > row["W"]:
        if streak_type == "losing" or streak_type == "":
            streak += 1
            streak_type = "losing"
        else:
            break
    else:
        break

streak_label = f"{streak} {'🔥 winning' if streak_type == 'winning' else '📉 losing'} basho streak" if streak > 1 else "—"

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total Wins", total_wins)
m2.metric("Total Losses", total_losses)
m3.metric("Win Rate", f"{overall_pct}%")
m4.metric("Streak", streak_label)

st.divider()

# ── Win % trend chart ─────────────────────────────────────────────────────────
st.subheader("Win % Over Time")

chart_df = df[df["Win %"].notna()].set_index("Basho")["Win %"]
st.line_chart(chart_df, height=300)

# Reference line note
st.caption("50% line = kachi-koshi threshold (winning record)")

st.divider()

# ── W/L bar chart ─────────────────────────────────────────────────────────────
st.subheader("Wins & Losses Per Tournament")

bar_df = df.set_index("Basho")[["W", "L"]]
st.bar_chart(bar_df, height=300, color=["#276749", "#9b2335"])

st.divider()

# ── Full table ────────────────────────────────────────────────────────────────
st.subheader("Tournament Log")

display_df = df[["Basho", "Division", "W", "L", "Abs", "Win %", "Record"]].iloc[::-1].reset_index(drop=True)

def style_pct(val):
    if val is None or pd.isna(val):
        return "color: #a0aec0"
    if val >= 50:
        return "color: #276749; font-weight: bold"
    return "color: #9b2335; font-weight: bold"

styled = (
    display_df.style
    .applymap(style_pct, subset=["Win %"])
    .format({"Win %": lambda x: f"{x}%" if x is not None and not pd.isna(x) else "—"})
)

st.dataframe(
    styled,
    use_container_width=True,
    hide_index=True,
    height=min(500, 36 * len(display_df) + 38),
)

st.divider()
st.caption("Data from [sumo-api.com](https://sumo-api.com)")

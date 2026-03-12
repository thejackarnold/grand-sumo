import streamlit as st
import requests
import pandas as pd

st.set_page_config(
    page_title="Kimarite · Grand Sumo",
    page_icon="🏯",
    layout="wide"
)

BASE_URL = "https://sumo-api.com/api"


@st.cache_data(ttl=3600)
def get_all_rikishi():
    r = requests.get(f"{BASE_URL}/rikishis")
    return r.json() if r.status_code == 200 else None


@st.cache_data(ttl=3600)
def get_matches(rikishi_id):
    r = requests.get(f"{BASE_URL}/rikishi/{rikishi_id}/matches")
    return r.json() if r.status_code == 200 else None


@st.cache_data(ttl=3600)
def get_all_kimarite():
    r = requests.get(f"{BASE_URL}/kimarite")
    return r.json() if r.status_code == 200 else None


# Kimarite categories (broad groupings)
KIMARITE_CATEGORIES = {
    "Push/Thrust": ["oshidashi", "tsukidashi", "oshitaoshi", "tsukitaoshi", "hatakikomi", "hikiotoshi",
                    "tsukiotoshi", "okuridashi", "okuritaoshi", "okuritsukidashi", "okuritsukitaoshi"],
    "Belt": ["yorikiri", "yoritaoshi", "uwatenage", "shitatenage", "uwatedashinage", "shitatedashinage",
             "tsuriotoshi", "kotehineri", "kotenage", "kubinage"],
    "Trip/Leg": ["ketaguri", "sotogake", "uchigake", "kirikaeshi", "chongake", "mitokorozeme",
                 "nimaigeri", "watashikomi", "ashitori"],
    "Throw": ["ipponzeoi", "sukuinage", "tsuridashi", "tsuriotoshi", "kakenage", "shitatehineri",
              "uwatehineri", "tottan"],
    "Special": ["isamiashi", "fumidashi", "kachikoshi", "fusensho", "zunonmari"],
}


def categorize_kimarite(technique):
    if not technique:
        return "Other"
    t = technique.lower()
    for cat, techniques in KIMARITE_CATEGORIES.items():
        if any(k in t for k in techniques):
            return cat
    return "Other"


# ── Header ────────────────────────────────────────────────────────────────────
st.title("⚡ Kimarite Breakdown")
st.caption("Winning technique analysis for any rikishi")
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

selected_name = st.selectbox(
    "Select a rikishi",
    [""] + sorted_names,
    format_func=lambda x: "Select wrestler..." if x == "" else x
)

if not selected_name:
    st.info("Select a rikishi above to see their kimarite breakdown.")
    st.stop()

rikishi = name_to_rikishi[selected_name]
rikishi_id = rikishi.get("id")

# ── Fetch matches ─────────────────────────────────────────────────────────────
with st.spinner("Loading match history..."):
    match_data = get_matches(rikishi_id)

if not match_data:
    st.warning("No match data found.")
    st.stop()

# Handle all possible API response shapes
if isinstance(match_data, dict):
    matches = (
        match_data.get("matches")
        or match_data.get("records")
        or match_data.get("data")
        or []
    )
elif isinstance(match_data, list):
    matches = match_data
else:
    matches = []

if not matches:
    st.info(f"No match history found for {selected_name}.")
    st.stop()

# Filter to wins only for kimarite analysis
wins = [m for m in matches if isinstance(m, dict) and m.get("winnerId") == rikishi_id]

if not wins:
    st.info(f"No recorded wins found for {selected_name}.")
    st.stop()

# ── Build kimarite dataframe ──────────────────────────────────────────────────
kimarite_counts = {}
for m in wins:
    k = m.get("kimarite", "Unknown") or "Unknown"
    kimarite_counts[k] = kimarite_counts.get(k, 0) + 1

df_k = pd.DataFrame([
    {"Technique": k, "Wins": v, "Category": categorize_kimarite(k)}
    for k, v in kimarite_counts.items()
]).sort_values("Wins", ascending=False).reset_index(drop=True)

total_wins = df_k["Wins"].sum()
df_k["Share %"] = (df_k["Wins"] / total_wins * 100).round(1)

# ── Summary ───────────────────────────────────────────────────────────────────
st.subheader(f"{selected_name} — Kimarite Analysis")

m1, m2, m3 = st.columns(3)
m1.metric("Total Wins Analysed", total_wins)
m2.metric("Distinct Techniques", len(df_k))
top_technique = df_k.iloc[0]["Technique"] if len(df_k) > 0 else "—"
top_pct = df_k.iloc[0]["Share %"] if len(df_k) > 0 else 0
m3.metric("Signature Move", top_technique, delta=f"{top_pct}% of wins")

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
chart_col, table_col = st.columns([3, 2])

with chart_col:
    st.subheader("Top Techniques")
    top_df = df_k.head(15)

    # Use st.bar_chart with a clean dataframe
    chart_data = top_df.set_index("Technique")["Wins"]
    st.bar_chart(chart_data, height=400)

with table_col:
    st.subheader("Full Breakdown")
    st.dataframe(
        df_k[["Technique", "Category", "Wins", "Share %"]],
        use_container_width=True,
        hide_index=True,
        height=400,
        column_config={
            "Technique": st.column_config.TextColumn("Technique", width="medium"),
            "Category": st.column_config.TextColumn("Category", width="small"),
            "Wins": st.column_config.NumberColumn("Wins", width="small"),
            "Share %": st.column_config.NumberColumn("Share %", width="small", format="%.1f%%"),
        }
    )

# ── Category summary ──────────────────────────────────────────────────────────
st.divider()
st.subheader("By Style Category")

cat_df = df_k.groupby("Category")["Wins"].sum().reset_index()
cat_df["Share %"] = (cat_df["Wins"] / total_wins * 100).round(1)
cat_df = cat_df.sort_values("Wins", ascending=False).reset_index(drop=True)

# Style label
dominant = cat_df.iloc[0]["Category"] if len(cat_df) > 0 else "—"
dominant_pct = cat_df.iloc[0]["Share %"] if len(cat_df) > 0 else 0

if dominant == "Push/Thrust":
    style_label = "🔥 Pusher/Thruster — aggressive forward style"
elif dominant == "Belt":
    style_label = "🤼 Belt fighter — grappling and throws"
elif dominant == "Trip/Leg":
    style_label = "🦵 Leg technique specialist"
elif dominant == "Throw":
    style_label = "💫 Throw specialist"
else:
    style_label = "🎯 Versatile / Unconventional"

st.info(f"**Fighting style: {style_label}** ({dominant_pct}% of wins via {dominant} techniques)")

st.dataframe(
    cat_df,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Category": st.column_config.TextColumn("Category", width="medium"),
        "Wins": st.column_config.NumberColumn("Wins", width="small"),
        "Share %": st.column_config.NumberColumn("Share %", width="small", format="%.1f%%"),
    }
)

st.divider()
st.caption("Data from [sumo-api.com](https://sumo-api.com) · Wins only used for technique analysis")

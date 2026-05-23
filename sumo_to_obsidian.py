import os
import pandas as pd
from collections import Counter
from datetime import datetime
from client import SumoSyncClient

# --- Configuration ---
VAULT_PATH = os.environ.get("SUMO_VAULT_PATH", "data")

# ---------------------------------------------------------------------------
# Helper Utilities
# ---------------------------------------------------------------------------

RANK_ORDER = ["Yokozuna", "Ozeki", "Sekiwake", "Komusubi", "Maegashira"]

def rank_sort_key(rank: str) -> tuple:
    """Returns a sort tuple for ordering banzuke ranks correctly."""
    for i, r in enumerate(RANK_ORDER):
        if rank.startswith(r):
            parts = rank.replace(r, "").strip().split()
            num = int(parts[0]) if parts and parts[0].isdigit() else 0
            side = 0 if "East" in rank else 1
            return (i, num, side)
    return (99, 0, 0)

def format_basho_id(basho_id: int) -> str:
    """Format 202603 -> 'March 2026'."""
    months = {
        "01": "January", "03": "March", "05": "May",
        "07": "July",    "09": "September", "11": "November"
    }
    s = str(basho_id)
    year, month = s[:4], s[4:]
    return f"{months.get(month, month)} {year}"

def fetch_rikishi_kimarite(client: SumoSyncClient, rikishi_id: int) -> str:
    """Fetches and calculates the top 3 kimarite for a rikishi."""
    matches_resp = client.get_rikishi_matches(rikishi_id)
    kimarite_counts = Counter()
    for match in matches_resp.records:
        if match.winner_id == rikishi_id:
            if match.kimarite and match.kimarite != 'fusen':
                kimarite_counts[match.kimarite] += 1
    if not kimarite_counts:
        return "None"
    top_3 = kimarite_counts.most_common(3)
    return ", ".join([f"{k.capitalize()} ({c})" for k, c in top_3])

# ---------------------------------------------------------------------------
# Data Compilation
# ---------------------------------------------------------------------------

def compile_makuuchi_dataframe(basho_id: int):
    """Orchestrates the fetch and merge logic using SumoSyncClient."""
    all_details = []

    with SumoSyncClient() as client:
        banzuke = client.get_banzuke(str(basho_id), "Makuuchi")
        roster = banzuke.east + banzuke.west

        print(f"  Starting collection for {len(roster)} Makuuchi rikishi...")

        for entry in roster:
            try:
                profile_obj = client.get_rikishi(str(entry.rikishi_id))
                stats_obj   = client.get_rikishi_stats(str(entry.rikishi_id))

                debut_raw = profile_obj.debut if profile_obj.debut else ""
                debut_fmt = f"{debut_raw[:4]}-{debut_raw[4:]}" if len(debut_raw) >= 6 else debut_raw
                bd        = profile_obj.birth_date
                today     = datetime.now()
                age       = today.year - bd.year - ((today.month, today.day) < (bd.month, bd.day)) if bd else ""

                profile = {
                    "ID":           profile_obj.id,
                    "SumoDB_ID":    profile_obj.sumodb_id,
                    "NSK_ID":       profile_obj.nsk_id,
                    "Name":         profile_obj.shikona_en,
                    "Name_Jp":      profile_obj.shikona_jp,
                    "Current_Rank": profile_obj.current_rank,
                    "Heya":         profile_obj.heya,
                    "Weight":       profile_obj.weight,
                    "Height":       profile_obj.height,
                    "Birthplace":   profile_obj.shusshin,
                    "Birth_Date":   bd.strftime('%Y-%m-%d') if bd else "",
                    "Age":          age,
                    "Debut":        debut_fmt,
                    "Basho_Rank":   entry.rank,
                }

                wins    = stats_obj.total_wins
                losses  = stats_obj.total_losses
                win_pct = round(wins / (wins + losses) * 100, 1) if (wins + losses) > 0 else 0.0

                profile['Wins']           = wins
                profile['Losses']         = losses
                profile['Absences']       = stats_obj.total_absences
                profile['Win_Percentage'] = win_pct
                profile['Yusho']          = stats_obj.yusho

                sansho_list = []
                if stats_obj.sansho:
                    if stats_obj.sansho.Gino_sho:  sansho_list.append(f"Gino-sho ({stats_obj.sansho.Gino_sho})")
                    if stats_obj.sansho.Kanto_sho:  sansho_list.append(f"Kanto-sho ({stats_obj.sansho.Kanto_sho})")
                    if stats_obj.sansho.Shukun_sho: sansho_list.append(f"Shukun-sho ({stats_obj.sansho.Shukun_sho})")
                profile['Sansho'] = ", ".join(sansho_list) if sansho_list else "None"

                profile['Top_Kimarite'] = fetch_rikishi_kimarite(client, entry.rikishi_id)

                all_details.append(profile)
                print(f"  Processed: {profile['Name']}")
            except Exception as e:
                print(f"  Error on ID {entry.rikishi_id}: {e}")

    return pd.DataFrame(all_details)

# ---------------------------------------------------------------------------
# Export 1: Individual Rikishi Pages
# ---------------------------------------------------------------------------

def export_rikishi_pages(df):
    """Saves one Markdown file per rikishi with full stats and career data."""
    out_dir = os.path.join(VAULT_PATH, "Rikishi")
    os.makedirs(out_dir, exist_ok=True)

    for _, row in df.iterrows():
        safe_name = row['Name'].replace(' ', '_')
        image_ref = f"{row['Name']}.png"
        file_path = os.path.join(out_dir, f"{safe_name}.md")

        md = f"""---
type: rikishi
tags: [sumo, rikishi]
rank: {row['Basho_Rank']}
heya: {row['Heya']}
weight: {row['Weight']}
height: {row['Height']}
birthdate: {row['Birth_Date']}
age: {row['Age']}
wins: {row['Wins']}
losses: {row['Losses']}
absences: {row['Absences']}
win_percentage: {row['Win_Percentage']}
yusho: {row['Yusho']}
sansho: "{row['Sansho']}"
top_kimarite: "{row['Top_Kimarite']}"
headshot: "[[{image_ref}]]"
sumodb_id: {row['SumoDB_ID']}
nsk_id: {row['NSK_ID']}
id: {row['ID']}
updated: {pd.Timestamp.now().strftime('%Y-%m-%d')}
---
# {row['Name']} ({row['Name_Jp']})

![[{image_ref}|right|200]]

- **Rank:** {row['Basho_Rank']}
- **Heya:** [[Heya/{row['Heya']}]]
- **Hometown:** {row['Birthplace']}
- **Age:** {row['Age']} (born {row['Birth_Date']})
- **Stats:** {row['Weight']}kg | {row['Height']}cm
- **Debut:** {row['Debut']}

### Career
- **Record:** {row['Wins']} wins, {row['Losses']} losses, {row['Absences']} absences ({row['Win_Percentage']}% win rate)
- **Championships (Yusho):** {row['Yusho']}
- **Special Prizes (Sansho):** {row['Sansho']}
- **Top Winning Techniques:** {row['Top_Kimarite']}
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(md)

    print(f"  ✓ {len(df)} rikishi pages written to Rikishi/")

# ---------------------------------------------------------------------------
# Export 2: Banzuke (Rankings) Index Page
# ---------------------------------------------------------------------------

def export_banzuke_page(df, basho_id: int):
    """Creates a single ranked Banzuke hierarchy index page."""
    out_dir = os.path.join(VAULT_PATH, "Basho")
    os.makedirs(out_dir, exist_ok=True)

    basho_label = format_basho_id(basho_id)
    file_path   = os.path.join(out_dir, f"Banzuke {basho_label}.md")

    sorted_df = df.copy()
    sorted_df['_sort'] = sorted_df['Basho_Rank'].apply(rank_sort_key)
    sorted_df = sorted_df.sort_values('_sort')

    lines = []
    current_group = None
    for _, row in sorted_df.iterrows():
        rank  = row['Basho_Rank']
        group = next((r for r in RANK_ORDER if rank.startswith(r)), rank)
        if group != current_group:
            if current_group is not None:
                lines.append("")
            lines.append(f"### {group}")
            current_group = group
        side_icon = "🔴" if "East" in rank else "🔵"
        lines.append(
            f"- {side_icon} **{rank}** — "
            f"[[Rikishi/{row['Name'].replace(' ', '_')}|{row['Name']}]] "
            f"({row['Name_Jp']}) · [[Heya/{row['Heya']}|{row['Heya']}]]"
        )

    md = f"""---
type: banzuke
tags: [sumo, banzuke]
basho: {basho_id}
basho_label: {basho_label}
updated: {pd.Timestamp.now().strftime('%Y-%m-%d')}
---
# Banzuke — {basho_label}

> 🔴 East side · 🔵 West side

{chr(10).join(lines)}
"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"  ✓ Banzuke page written → Basho/Banzuke {basho_label}.md")

# ---------------------------------------------------------------------------
# Export 3: Basho Summary Page
# ---------------------------------------------------------------------------

def export_basho_summary(basho_id: int):
    """Fetches basho tournament results and writes a summary page."""
    out_dir = os.path.join(VAULT_PATH, "Basho")
    os.makedirs(out_dir, exist_ok=True)

    basho_label = format_basho_id(basho_id)
    file_path   = os.path.join(out_dir, f"{basho_label} Basho.md")

    with SumoSyncClient() as client:
        basho = client.get_basho(str(basho_id))

    start = basho.start_date.strftime('%B %d, %Y')
    end   = basho.end_date.strftime('%B %d, %Y')
    location = basho.location or "_TBD_"

    if basho.yusho:
        yusho_rows = "\n".join(
            f"| {p.type} | [[Rikishi/{p.shikona_en.replace(' ', '_')}|{p.shikona_en}]] | {p.shikona_jp} |"
            for p in basho.yusho
        )
        yusho_section = f"""## 🏆 Tournament Champions (Yusho)

| Division | Rikishi | Japanese |
|----------|---------|----------|
{yusho_rows}"""
    else:
        yusho_section = "## 🏆 Tournament Champions (Yusho)\n\n_Tournament still in progress._"

    if basho.special_prizes:
        sansho_rows = "\n".join(
            f"| {p.type} | [[Rikishi/{p.shikona_en.replace(' ', '_')}|{p.shikona_en}]] | {p.shikona_jp} |"
            for p in basho.special_prizes
        )
        sansho_section = f"""## 🎖️ Special Prizes (Sansho)

| Prize | Rikishi | Japanese |
|-------|---------|----------|
{sansho_rows}"""
    else:
        sansho_section = "## 🎖️ Special Prizes (Sansho)\n\n_Awarded after the tournament ends._"

    day_links = "\n".join(
        f"- [[Torikumi/{basho_label} Day {d:02d}|Day {d}]]"
        for d in range(1, 16)
    )

    md = f"""---
type: basho
tags: [sumo, basho]
basho_id: {basho_id}
location: {location}
start_date: {basho.start_date.strftime('%Y-%m-%d')}
end_date: {basho.end_date.strftime('%Y-%m-%d')}
updated: {pd.Timestamp.now().strftime('%Y-%m-%d')}
---
# {basho_label} Basho

- **Location:** {location}
- **Dates:** {start} – {end}
- **Banzuke:** [[Basho/Banzuke {basho_label}]]

{yusho_section}

{sansho_section}

## 📅 Daily Match Logs

{day_links}
"""
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(md)
    print(f"  ✓ Basho summary written → Basho/{basho_label} Basho.md")

# ---------------------------------------------------------------------------
# Export 4: Daily Torikumi Pages
# ---------------------------------------------------------------------------

def export_torikumi_pages(basho_id: int, days: int = 15):
    """Fetches and writes one match-log page per day of the basho."""
    out_dir = os.path.join(VAULT_PATH, "Torikumi")
    os.makedirs(out_dir, exist_ok=True)

    basho_label = format_basho_id(basho_id)

    with SumoSyncClient() as client:
        for day in range(1, days + 1):
            try:
                torikumi  = client.get_torikumi(str(basho_id), "Makuuchi", day)
                file_path = os.path.join(out_dir, f"{basho_label} Day {day:02d}.md")

                match_lines = []
                for m in torikumi.matches:
                    east       = m.east_shikona or "?"
                    west       = m.west_shikona or "?"
                    east_rank  = m.east_rank or ""
                    west_rank  = m.west_rank or ""
                    east_link  = f"[[Rikishi/{east.replace(' ', '_')}|{east}]]"
                    west_link  = f"[[Rikishi/{west.replace(' ', '_')}|{west}]]"
                    technique  = m.kimarite.capitalize() if m.kimarite else "—"

                    if m.winner_id:
                        if m.winner_id == m.east_id:
                            result = "🏆 East"
                        else:
                            result = "🏆 West"
                    else:
                        result = "_TBD_"
                        technique = "—"

                    match_lines.append(
                        f"| {east_rank} | {east_link} | {west_link} | {west_rank} | {result} | {technique} |"
                    )

                table_md = "\n".join(match_lines) if match_lines else "_No bouts scheduled._"

                prev_link = f"[[Torikumi/{basho_label} Day {(day-1):02d}|← Day {day-1}]]  " if day > 1 else ""
                next_link = f"  [[Torikumi/{basho_label} Day {(day+1):02d}|Day {day+1} →]]" if day < 15 else ""

                md = f"""---
type: torikumi
tags: [sumo, torikumi]
basho_id: {basho_id}
basho_label: {basho_label}
day: {day}
updated: {pd.Timestamp.now().strftime('%Y-%m-%d')}
---
# {basho_label} — Day {day}

{prev_link}[[Basho/{basho_label} Basho|🏠 Basho Summary]]{next_link}

| East Rank | East | West | West Rank | Result | Kimarite |
|-----------|------|------|-----------|--------|----------|
{table_md}
"""
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(md)
                print(f"  ✓ Day {day:02d} written")
            except Exception as e:
                print(f"  ⚠ Day {day} skipped: {e}")

# ---------------------------------------------------------------------------
# Export 5: Heya (Stable) Pages
# ---------------------------------------------------------------------------

def export_heya_pages(df):
    """Groups rikishi by stable and writes one page per Heya."""
    out_dir = os.path.join(VAULT_PATH, "Heya")
    os.makedirs(out_dir, exist_ok=True)

    for heya, group in df.groupby("Heya"):
        file_path    = os.path.join(out_dir, f"{heya}.md")
        group_sorted = group.copy()
        group_sorted['_sort'] = group_sorted['Basho_Rank'].apply(rank_sort_key)
        group_sorted = group_sorted.sort_values('_sort')

        wrestler_lines = "\n".join(
            f"- **{row['Basho_Rank']}** — "
            f"[[Rikishi/{row['Name'].replace(' ', '_')}|{row['Name']}]] ({row['Name_Jp']}) "
            f"· {row['Wins']}W {row['Losses']}L ({row['Win_Percentage']}%)"
            for _, row in group_sorted.iterrows()
        )

        count = len(group)
        md = f"""---
type: heya
tags: [sumo, heya]
name: {heya}
makuuchi_count: {count}
updated: {pd.Timestamp.now().strftime('%Y-%m-%d')}
---
# {heya} Stable

**Active Makuuchi wrestlers ({count}):**

{wrestler_lines}
"""
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(md)

    print(f"  ✓ {df['Heya'].nunique()} heya pages written to Heya/")

# ---------------------------------------------------------------------------
# Main Pipeline
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    current_basho = 202603

    try:
        print("=== Step 1: Compiling Makuuchi data ===")
        final_df = compile_makuuchi_dataframe(current_basho)
        print(f"\n--- Preview ---\n{final_df[['Name', 'Basho_Rank', 'Heya', 'Win_Percentage']].head()}\n")

        print("=== Step 2: Rikishi pages ===")
        export_rikishi_pages(final_df)

        print("\n=== Step 3: Banzuke index ===")
        export_banzuke_page(final_df, current_basho)

        print("\n=== Step 4: Basho summary ===")
        export_basho_summary(current_basho)

        print("\n=== Step 5: Torikumi day logs ===")
        export_torikumi_pages(current_basho)

        print("\n=== Step 6: Heya pages ===")
        export_heya_pages(final_df)

        print("\n✅ All exports complete!")

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"Pipeline Failed: {e}")

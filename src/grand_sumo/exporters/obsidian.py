"""Obsidian vault exporter for Grand Sumo data."""

import os
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Callable, Optional

from grand_sumo.client import SumoSyncClient
from grand_sumo.config import DEFAULT_VAULT_PATH

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
    kimarite_counts: Counter = Counter()
    for match in matches_resp.records:
        if match.winner_id == rikishi_id:
            if match.kimarite and match.kimarite != "fusen":
                kimarite_counts[match.kimarite] += 1
    if not kimarite_counts:
        return "None"
    top_3 = kimarite_counts.most_common(3)
    return ", ".join([f"{k.capitalize()} ({c})" for k, c in top_3])


# ---------------------------------------------------------------------------
# Data Compilation
# ---------------------------------------------------------------------------

def compile_makuuchi_data(
    basho_id: int,
    progress_callback: Optional[Callable] = None,
) -> list[dict]:
    """Orchestrates the fetch and merge logic using SumoSyncClient.

    Returns a plain list of dicts (one per rikishi) instead of a DataFrame.
    """
    all_details: list[dict] = []

    def _log(msg: str) -> None:
        if progress_callback:
            progress_callback("compile", msg)
        else:
            print(msg)

    with SumoSyncClient() as client:
        banzuke = client.get_banzuke(str(basho_id), "Makuuchi")
        roster = banzuke.east + banzuke.west

        _log(f"  Starting collection for {len(roster)} Makuuchi rikishi...")

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
                    "Birth_Date":   bd.strftime("%Y-%m-%d") if bd else "",
                    "Age":          age,
                    "Debut":        debut_fmt,
                    "Basho_Rank":   entry.rank,
                }

                wins    = stats_obj.total_wins
                losses  = stats_obj.total_losses
                win_pct = round(wins / (wins + losses) * 100, 1) if (wins + losses) > 0 else 0.0

                profile["Wins"]           = wins
                profile["Losses"]         = losses
                profile["Absences"]       = stats_obj.total_absences
                profile["Win_Percentage"] = win_pct
                profile["Yusho"]          = stats_obj.yusho

                sansho_list = []
                if stats_obj.sansho:
                    if stats_obj.sansho.Gino_sho:   sansho_list.append(f"Gino-sho ({stats_obj.sansho.Gino_sho})")
                    if stats_obj.sansho.Kanto_sho:  sansho_list.append(f"Kanto-sho ({stats_obj.sansho.Kanto_sho})")
                    if stats_obj.sansho.Shukun_sho: sansho_list.append(f"Shukun-sho ({stats_obj.sansho.Shukun_sho})")
                profile["Sansho"] = ", ".join(sansho_list) if sansho_list else "None"

                profile["Top_Kimarite"] = fetch_rikishi_kimarite(client, entry.rikishi_id)

                all_details.append(profile)
                _log(f"  Processed: {profile['Name']}")
            except Exception as e:
                _log(f"  Error on ID {entry.rikishi_id}: {e}")

    return all_details


# ---------------------------------------------------------------------------
# Export 1: Individual Rikishi Pages
# ---------------------------------------------------------------------------

def export_rikishi_pages(
    data: list[dict],
    vault_path: Path = DEFAULT_VAULT_PATH,
    progress_callback: Optional[Callable] = None,
) -> None:
    """Saves one Markdown file per rikishi with full stats and career data."""
    out_dir = vault_path / "Rikishi"
    out_dir.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        if progress_callback:
            progress_callback("rikishi_pages", msg)
        else:
            print(msg)

    for row in data:
        safe_name  = row["Name"].replace(" ", "_")
        image_ref  = f"{row['Name']}.png"
        file_path  = out_dir / f"{safe_name}.md"

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
updated: {datetime.now().strftime('%Y-%m-%d')}
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
        file_path.write_text(md, encoding="utf-8")

    _log(f"  ✓ {len(data)} rikishi pages written to Rikishi/")


# ---------------------------------------------------------------------------
# Export 2: Banzuke (Rankings) Index Page
# ---------------------------------------------------------------------------

def export_banzuke_page(
    data: list[dict],
    basho_id: int,
    vault_path: Path = DEFAULT_VAULT_PATH,
    progress_callback: Optional[Callable] = None,
) -> None:
    """Creates a single ranked Banzuke hierarchy index page."""
    out_dir = vault_path / "Basho"
    out_dir.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        if progress_callback:
            progress_callback("banzuke_page", msg)
        else:
            print(msg)

    basho_label = format_basho_id(basho_id)
    file_path   = out_dir / f"Banzuke {basho_label}.md"

    sorted_data = sorted(data, key=lambda r: rank_sort_key(r["Basho_Rank"]))

    lines = []
    current_group = None
    for row in sorted_data:
        rank  = row["Basho_Rank"]
        group = next((r for r in RANK_ORDER if rank.startswith(r)), rank)
        if group != current_group:
            if current_group is not None:
                lines.append("")
            lines.append(f"### {group}")
            current_group = group
        side_icon = "\U0001f534" if "East" in rank else "\U0001f535"
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
updated: {datetime.now().strftime('%Y-%m-%d')}
---
# Banzuke — {basho_label}

> \U0001f534 East side · \U0001f535 West side

{chr(10).join(lines)}
"""
    file_path.write_text(md, encoding="utf-8")
    _log(f"  ✓ Banzuke page written → Basho/Banzuke {basho_label}.md")


# ---------------------------------------------------------------------------
# Export 3: Basho Summary Page
# ---------------------------------------------------------------------------

def export_basho_summary(
    basho_id: int,
    vault_path: Path = DEFAULT_VAULT_PATH,
    progress_callback: Optional[Callable] = None,
) -> None:
    """Fetches basho tournament results and writes a summary page."""
    out_dir = vault_path / "Basho"
    out_dir.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        if progress_callback:
            progress_callback("basho_summary", msg)
        else:
            print(msg)

    basho_label = format_basho_id(basho_id)
    file_path   = out_dir / f"{basho_label} Basho.md"

    with SumoSyncClient() as client:
        basho = client.get_basho(str(basho_id))

    start    = basho.start_date.strftime("%B %d, %Y")
    end      = basho.end_date.strftime("%B %d, %Y")
    location = basho.location or "_TBD_"

    if basho.yusho:
        yusho_rows = "\n".join(
            f"| {p.type} | [[Rikishi/{p.shikona_en.replace(' ', '_')}|{p.shikona_en}]] | {p.shikona_jp} |"
            for p in basho.yusho
        )
        yusho_section = f"""## \U0001f3c6 Tournament Champions (Yusho)

| Division | Rikishi | Japanese |
|----------|---------|----------|
{yusho_rows}"""
    else:
        yusho_section = "## \U0001f3c6 Tournament Champions (Yusho)\n\n_Tournament still in progress._"

    if basho.special_prizes:
        sansho_rows = "\n".join(
            f"| {p.type} | [[Rikishi/{p.shikona_en.replace(' ', '_')}|{p.shikona_en}]] | {p.shikona_jp} |"
            for p in basho.special_prizes
        )
        sansho_section = f"""## \U0001f396️ Special Prizes (Sansho)

| Prize | Rikishi | Japanese |
|-------|---------|----------|
{sansho_rows}"""
    else:
        sansho_section = "## \U0001f396️ Special Prizes (Sansho)\n\n_Awarded after the tournament ends._"

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
updated: {datetime.now().strftime('%Y-%m-%d')}
---
# {basho_label} Basho

- **Location:** {location}
- **Dates:** {start} – {end}
- **Banzuke:** [[Basho/Banzuke {basho_label}]]

{yusho_section}

{sansho_section}

## \U0001f4c5 Daily Match Logs

{day_links}
"""
    file_path.write_text(md, encoding="utf-8")
    _log(f"  ✓ Basho summary written → Basho/{basho_label} Basho.md")


# ---------------------------------------------------------------------------
# Export 4: Daily Torikumi Pages
# ---------------------------------------------------------------------------

def export_torikumi_pages(
    basho_id: int,
    vault_path: Path = DEFAULT_VAULT_PATH,
    days: int = 15,
    progress_callback: Optional[Callable] = None,
) -> None:
    """Fetches and writes one match-log page per day of the basho."""
    out_dir = vault_path / "Torikumi"
    out_dir.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        if progress_callback:
            progress_callback("torikumi_pages", msg)
        else:
            print(msg)

    basho_label = format_basho_id(basho_id)

    with SumoSyncClient() as client:
        for day in range(1, days + 1):
            try:
                torikumi  = client.get_torikumi(str(basho_id), "Makuuchi", day)
                file_path = out_dir / f"{basho_label} Day {day:02d}.md"

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
                            result = "\U0001f3c6 East"
                        else:
                            result = "\U0001f3c6 West"
                    else:
                        result    = "_TBD_"
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
updated: {datetime.now().strftime('%Y-%m-%d')}
---
# {basho_label} — Day {day}

{prev_link}[[Basho/{basho_label} Basho|\U0001f3e0 Basho Summary]]{next_link}

| East Rank | East | West | West Rank | Result | Kimarite |
|-----------|------|------|-----------|--------|----------|
{table_md}
"""
                file_path.write_text(md, encoding="utf-8")
                _log(f"  ✓ Day {day:02d} written")
            except Exception as e:
                _log(f"  ⚠ Day {day} skipped: {e}")


# ---------------------------------------------------------------------------
# Export 5: Heya (Stable) Pages
# ---------------------------------------------------------------------------

def export_heya_pages(
    data: list[dict],
    vault_path: Path = DEFAULT_VAULT_PATH,
    progress_callback: Optional[Callable] = None,
) -> None:
    """Groups rikishi by stable and writes one page per Heya."""
    out_dir = vault_path / "Heya"
    out_dir.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        if progress_callback:
            progress_callback("heya_pages", msg)
        else:
            print(msg)

    # Group by heya
    heya_groups: dict[str, list[dict]] = {}
    for row in data:
        heya = row["Heya"]
        heya_groups.setdefault(heya, []).append(row)

    for heya, group in heya_groups.items():
        file_path    = out_dir / f"{heya}.md"
        group_sorted = sorted(group, key=lambda r: rank_sort_key(r["Basho_Rank"]))

        wrestler_lines = "\n".join(
            f"- **{row['Basho_Rank']}** — "
            f"[[Rikishi/{row['Name'].replace(' ', '_')}|{row['Name']}]] ({row['Name_Jp']}) "
            f"· {row['Wins']}W {row['Losses']}L ({row['Win_Percentage']}%)"
            for row in group_sorted
        )

        count = len(group)
        md = f"""---
type: heya
tags: [sumo, heya]
name: {heya}
makuuchi_count: {count}
updated: {datetime.now().strftime('%Y-%m-%d')}
---
# {heya} Stable

**Active Makuuchi wrestlers ({count}):**

{wrestler_lines}
"""
        file_path.write_text(md, encoding="utf-8")

    heya_count = len(heya_groups)
    _log(f"  ✓ {heya_count} heya pages written to Heya/")


# ---------------------------------------------------------------------------
# Export 5: Basho Tracker Page
# ---------------------------------------------------------------------------

def _determine_current_day(client: SumoSyncClient, basho_id: str) -> int:
    """Scan torikumi days to find the latest day with match data."""
    for day in range(1, 16):
        try:
            torikumi = client.get_torikumi(basho_id, "Makuuchi", day)
            if not torikumi.matches:
                return day - 1
        except Exception:
            return day - 1
    return 15


def _build_result_grid(
    rikishi_map: dict,
    client: SumoSyncClient,
    basho_id: str,
    current_day: int,
) -> None:
    """Fill result grids for each rikishi from torikumi data."""
    # Initialise results as unknown
    for rid in rikishi_map:
        rikishi_map[rid]["results"] = [""] * 16

    for day in range(1, current_day + 1):
        torikumi = client.get_torikumi(basho_id, "Makuuchi", day)
        seen: set[int] = set()
        for match in torikumi.matches:
            for rid, side_id in ((match.east_id, match.east_id), (match.west_id, match.west_id)):
                if rid and rid in rikishi_map:
                    seen.add(rid)
                    if match.winner_id is None:
                        rikishi_map[rid]["results"][day] = "·"
                    elif match.winner_id == side_id:
                        rikishi_map[rid]["results"][day] = "W"
                    elif match.kimarite and "fusen" in match.kimarite.lower():
                        rikishi_map[rid]["results"][day] = "A"
                    else:
                        rikishi_map[rid]["results"][day] = "L"

        # Rikishi not seen on this day were absent
        for rid in rikishi_map:
            if rid not in seen:
                rikishi_map[rid]["results"][day] = "A"

    # Mark future days
    for rid in rikishi_map:
        for d in range(current_day + 1, 16):
            rikishi_map[rid]["results"][d] = "·"
        # Fill any remaining empty slots as unknown
        for d in range(1, 16):
            if not rikishi_map[rid]["results"][d]:
                rikishi_map[rid]["results"][d] = "·"


def _sort_rikishi_list(
    rikishi_map: dict,
) -> list[tuple[int, dict]]:
    """Sort rikishi by rank order (Yokozuna → Maegashira)."""
    items = [(rid, data) for rid, data in rikishi_map.items()]
    items.sort(key=lambda x: rank_sort_key(x[1]["rank"]))
    return items


def _render_kkmk(wins: int, losses: int) -> str:
    """Return KK/MK badge string if applicable."""
    if wins >= 8:
        return "**KK**"
    if losses >= 7:
        return "**MK**"
    return ""


def export_tracker_page(
    basho_id: int,
    vault_path: Path = DEFAULT_VAULT_PATH,
    progress_callback: Optional[Callable] = None,
) -> None:
    """Fetches banzuke + torikumi and writes a live tournament tracker page."""
    out_dir = vault_path / "Basho"
    out_dir.mkdir(parents=True, exist_ok=True)

    def _log(msg: str) -> None:
        if progress_callback:
            progress_callback("tracker", msg)
        else:
            print(msg)

    basho_label = format_basho_id(basho_id)
    file_path = out_dir / f"{basho_label} Tracker.md"

    with SumoSyncClient() as client:
        basho = client.get_basho(str(basho_id))
        banzuke = client.get_banzuke(str(basho_id), "Makuuchi")
        current_day = _determine_current_day(client, str(basho_id))

        # Build rikishi map
        rikishi_map: dict = {}
        for entry in banzuke.east + banzuke.west:
            rikishi_map[entry.rikishi_id] = {
                "shikona": entry.shikona_en,
                "rank": entry.rank,
                "side": entry.side,
                "wins": entry.wins,
                "losses": entry.losses,
                "absences": entry.absences,
            }

        _build_result_grid(rikishi_map, client, str(basho_id), current_day)

    # Compute Yusho Race (top 8 by wins)
    sorted_by_wins = sorted(
        rikishi_map.items(), key=lambda x: (-x[1]["wins"], x[1]["losses"])
    )
    max_wins = sorted_by_wins[0][1]["wins"] if sorted_by_wins else 0
    yusho_race = sorted_by_wins[:8]

    # Sort by rank for sections
    sorted_rikishi = _sort_rikishi_list(rikishi_map)

    # Section buckets
    yokozuna_ozeki: list = []
    sekiwake_komusubi: list = []
    maegashira: list = []
    for rid, data in sorted_rikishi:
        rank = data["rank"]
        if rank.startswith("Yokozuna") or rank.startswith("Ozeki"):
            yokozuna_ozeki.append((rid, data))
        elif rank.startswith("Sekiwake") or rank.startswith("Komusubi"):
            sekiwake_komusubi.append((rid, data))
        else:
            maegashira.append((rid, data))

    def _gb(entry_wins: int) -> str:
        diff = max_wins - entry_wins
        return "—" if diff == 0 else str(diff)

    def _grid_row(rid: int, data: dict) -> str:
        cells = "  ".join(data["results"][1:])  # days 1-15
        cells = cells.replace("·", "·")  # keep middle dot
        return cells

    def _section_table(entries: list) -> str:
        rows = []
        for rid, data in entries:
            safe_name = data["shikona"].replace(" ", "_")
            link = f"[[Rikishi/{safe_name}|{data['shikona']}]]"
            grid = _grid_row(rid, data)
            kkmk = _render_kkmk(data["wins"], data["losses"])
            sep = f" | {kkmk}" if kkmk else ""
            gb = _gb(data["wins"])
            rows.append(
                f"| {data['rank']} | {link} | {grid} | "
                f"{data['wins']} | {data['losses']} | {data['absences']} |{sep} | {gb} |"
            )
        return "\n".join(rows)

    # Yusho Race table
    yusho_rows = []
    for rid, data in yusho_race:
        safe_name = data["shikona"].replace(" ", "_")
        link = f"[[Rikishi/{safe_name}|{data['shikona']}]]"
        yusho_rows.append(
            f"| {link} | {data['rank']} | {data['wins']} | {data['losses']} | {_gb(data['wins'])} |"
        )
    yusho_table = "\n".join(yusho_rows)

    # Day header
    day_header = "  ".join(str(d) for d in range(1, 16))

    # Venue + dates
    start = basho.start_date.strftime("%B %d, %Y") if basho.start_date else "TBD"
    end = basho.end_date.strftime("%B %d, %Y") if basho.end_date else "TBD"
    location = basho.location or "TBD"

    days_remaining = 15 - current_day
    day_info = f"Day {current_day} of 15" if current_day > 0 else "Not started"
    if current_day > 0:
        day_info += f" — {days_remaining} days remaining"

    md = f"""---
type: tracker
basho_id: {basho_id}
basho_label: {basho_label}
updated: {datetime.now().strftime('%Y-%m-%d')}
---
# {basho_label} — Tournament Tracker

> [!info] {day_info}
> 📍 {location} · 📅 {start} – {end}

> [!note]- Legend
> **W** win · **L** loss · **A** absent · **·** upcoming · **KK** kachikoshi (≥ 8W) · **MK** makekoshi (≥ 7L) · **GB** games behind leader

---

## Yusho Race

| Rikishi | Rank | W | L | GB |
|---------|------|---|---|-----|
{yusho_table}

---

## Yokozuna · Ozeki

| Rank | Rikishi | {day_header} | W | L | A | | GB |
|------|---------|{'-' * (len(day_header) + 2)}|---|---|---|--------|-----|
{_section_table(yokozuna_ozeki)}

---

## Sekiwake · Komusubi

| Rank | Rikishi | {day_header} | W | L | A | | GB |
|------|---------|{'-' * (len(day_header) + 2)}|---|---|---|--------|-----|
{_section_table(sekiwake_komusubi)}

---

## Maegashira

| Rank | Rikishi | {day_header} | W | L | A | | GB |
|------|---------|{'-' * (len(day_header) + 2)}|---|---|---|--------|-----|
{_section_table(maegashira)}

---

## Special Prize Watchlist

> [!note] Sansho Candidates
> _Add notes here as the tournament progresses._
>
> - **Gino-sho** (Technique):
> - **Kanto-sho** (Fighting Spirit):
> - **Shukun-sho** (Outstanding Performance):

## Notes
"""
    file_path.write_text(md, encoding="utf-8")
    _log(f"  ✓ Tracker page written → Basho/{basho_label} Tracker.md")


# ---------------------------------------------------------------------------
# Full Pipeline
# ---------------------------------------------------------------------------

def run_full_pipeline(
    basho_id: int,
    vault_path: Path = DEFAULT_VAULT_PATH,
    progress_callback: Optional[Callable] = None,
) -> None:
    """Run all 7 export steps in sequence.

    Args:
        basho_id: Basho ID in YYYYMM format (int)
        vault_path: Path to the Obsidian vault root
        progress_callback: Optional callable receiving (step: str, message: str)
    """
    def _log(step: str, msg: str) -> None:
        if progress_callback:
            progress_callback(step, msg)
        else:
            print(f"[{step}] {msg}")

    _log("pipeline", "=== Step 1: Compiling Makuuchi data ===")
    roster_data = compile_makuuchi_data(basho_id, progress_callback=progress_callback)

    _log("pipeline", "=== Step 2: Rikishi pages ===")
    export_rikishi_pages(roster_data, vault_path=vault_path, progress_callback=progress_callback)

    _log("pipeline", "=== Step 3: Banzuke index ===")
    export_banzuke_page(roster_data, basho_id, vault_path=vault_path, progress_callback=progress_callback)

    _log("pipeline", "=== Step 4: Basho summary ===")
    export_basho_summary(basho_id, vault_path=vault_path, progress_callback=progress_callback)

    _log("pipeline", "=== Step 5: Torikumi day logs ===")
    export_torikumi_pages(basho_id, vault_path=vault_path, progress_callback=progress_callback)

    _log("pipeline", "=== Step 6: Heya pages ===")
    export_heya_pages(roster_data, vault_path=vault_path, progress_callback=progress_callback)

    _log("pipeline", "=== Step 7: Tournament tracker ===")
    export_tracker_page(basho_id, vault_path=vault_path, progress_callback=progress_callback)

    _log("pipeline", "✅ All exports complete!")

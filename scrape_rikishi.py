#!/usr/bin/env python3
"""
scrape_rikishi.py
-----------------
Scrapes the Makuuchi division roster from sumo.or.jp, downloads each rikishi's
profile page and portrait image, and writes one Obsidian .md note per rikishi
using the rikishi-profile-template.md format.

Usage:
    python3 scrape_rikishi.py [--vault PATH] [--images-dir PATH] [--delay 0.5]

Outputs:
    <vault>/<RingName>.md         — one note per rikishi
    <images-dir>/<RingName>.jpg   — portrait image (270x474)

Requirements: Python 3.8+, no third-party libraries needed.
"""

import argparse
import re
import time
import urllib.request
from datetime import date
from pathlib import Path

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BASE_URL    = "https://sumo.or.jp"
SEARCH_URL  = f"{BASE_URL}/EnSumoDataRikishi/search/"
PROFILE_URL = f"{BASE_URL}/EnSumoDataRikishi/profile/"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# web_fetch strips HTML to markdown-ish plain text, so patterns match that.

TEMPLATE = """\
---
title: "Rikishi Profile – {ring_name}"
date: {date}
type: profile
tags:
  - sumo
  - rikishi
  - {division}
  - {stable_tag}-stable
ring_name:: {ring_name}
given_name:: {given_name}
stable:: {stable}
division:: {division}
rank:: {current_rank}
birthdate:: {birthday}
birthplace:: {birthplace}
height_cm:: {height}
weight_kg:: {weight}
debut:: {debut}
highest_rank:: {highest_rank}
status:: #active
---

# {ring_name}

![[{ring_name}.jpg]]

## Basic Information

| Field | Value |
|---|---|
| **Ring Name** | {ring_name} |
| **Given Name** | {given_name} |
| **Stable** | [[{stable} Stable\\|{stable}]] |
| **Current Rank** | {current_rank} |
| **Birthday** | {birthday} |
| **Birthplace** | {birthplace} |
| **Height** | {height} cm |
| **Weight** | {weight} kg |
| **Signature Moves** | {signature_moves} |

---

## Career Milestones

| Milestone | Date |
|---|---|
| Debut | {debut} |
| Jūryō Debut | {juryo_debut} |
| Makuuchi Debut | {makuuchi_debut} |
| Sanyaku Debut | {sanyaku_debut} |
| Highest Rank | {highest_rank} |

---

## Career Record

**Overall:** {career_wins}-{career_losses}-{career_absences}
**Makuuchi:** {makuuchi_wins}-{makuuchi_losses}-{makuuchi_absences}

### Division Championships

| Division | Count |
|---|---|
| Makuuchi | {champ_makuuchi} |
| Jūryō | {champ_juryo} |
| Makushita | {champ_makushita} |
| Sandanme | {champ_sandanme} |
| Jonidan | {champ_jonidan} |
| Jonokuchi | {champ_jonokuchi} |

### Special Prizes

| Prize | Count |
|---|---|
| Outstanding Performance | {prize_outstanding} |
| Fighting Spirit | {prize_fighting_spirit} |
| Technique | {prize_technique} |
| Kinboshi (gold stars) | {kinboshi} |

---

## Winning Techniques

| Rank | Technique | % |
|---|---|---|
{technique_rows}

---

## Recent Rankings (Past Year)

| Basho | Rank |
|---|---|
{recent_ranking_rows}

---

## Tournament Results

| Basho | Rank | Record | Notes |
|---|---|---|---|
{tournament_rows}

---

## Stablemates

| Rikishi | Rank |
|---|---|
{stablemate_rows}

---

## Notes

<!-- Personal observations, fighting style, storylines, rivalries -->

"""

# ---------------------------------------------------------------------------
# HTTP helpers
# ---------------------------------------------------------------------------

def fetch(url: str, binary: bool = False, referer: str = SEARCH_URL, timeout: int = 15):
    headers = {**HEADERS, "Referer": referer}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read() if binary else resp.read().decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Roster parsing  (from the search page)
# ---------------------------------------------------------------------------

def parse_roster(html: str) -> list[tuple[str, str]]:
    """
    Return list of (profile_id, ring_name) for all Makuuchi rikishi.
    The search page lists them in a markdown table with links like:
      [Hoshoryu](https://sumo.or.jp/EnSumoDataRikishi/profile/3842)
    """
    pattern = r'\[([^\]]+)\]\(https?://sumo\.or\.jp/EnSumoDataRikishi/profile/(\d+)\)'
    seen: dict[str, str] = {}
    for m in re.finditer(pattern, html):
        name, pid = m.group(1).strip(), m.group(2)
        if pid not in seen:
            seen[pid] = name
    return [(pid, name) for pid, name in seen.items()]


# ---------------------------------------------------------------------------
# Profile parsing  (from the stripped plain-text page)
#
# web_fetch converts the page to markdown-like plain text.
# Key structural patterns after conversion:
#
#   Basic info table row:    | Label  | Value  |
#   Prize block:             ![Alt text](url)\nCOUNT
#   Career record:           Career Record:\nW-L-A
#   Makuuchi record:         Makuuchi Records:\nW-L-A  (note trailing 's')
#   Techniques:              1.\n\nTECHNIQUE\nPCT%
#   Recent rankings:         RANK_LABEL\nMONTH   (after rank icon lines)
#   Tournament rows:         - YYYY MONTH SIDE DIVISION# NAME W-L[-A] ...
#   Milestones:              Debut\nMONTH, YEAR  (plain text section)
#   Stablemates:             | ![...](small_img) RANK [NAME](profile_url) | [STABLE](url) |
# ---------------------------------------------------------------------------

def _table_value(text: str, label: str) -> str:
    """Extract the value cell from a markdown table row matching label."""
    m = re.search(
        r'\|\s*\*?\*?' + re.escape(label) + r'\*?\*?\s*\|([^|\n]+)',
        text, re.IGNORECASE
    )
    return m.group(1).strip() if m else ""


def parse_profile(text: str, ring_name: str) -> dict:
    d: dict = {}

    # ---- Basic info --------------------------------------------------------
    for label, key in [
        ("Name",               "given_name"),
        ("Ring Name",          "ring_name_raw"),
        ("Current Rank",       "current_rank"),
        ("Birthday",           "birthday"),
        ("Birthplace",         "birthplace"),
        ("Height",             "height"),
        ("Weight",             "weight"),
        ("Signature Maneuver", "signature_moves"),
    ]:
        d[key] = _table_value(text, label)

    # Strip units from height/weight  e.g. "188.0cm" → "188.0"
    d["height"] = re.sub(r"[^\d.]", "", d.get("height", ""))
    d["weight"] = re.sub(r"[^\d.]", "", d.get("weight", ""))

    # Stable: first markdown link in the table section pointing to SumoBeya
    stable_m = re.search(r'\[([^\]]+)\]\([^)]*EnSumoDataSumoBeya[^)]+\)', text)
    d["stable"] = stable_m.group(1).strip() if stable_m else ""
    d["stable_tag"] = re.sub(r'[^a-z0-9]+', '-', d["stable"].lower()).strip('-')

    # ---- Image URL ---------------------------------------------------------
    img_m = re.search(r'/img/sumo_data/rikishi/270x474/(\d+\.jpg)', text)
    d["image_url"] = (
        f"{BASE_URL}/img/sumo_data/rikishi/270x474/{img_m.group(1)}" if img_m else ""
    )

    # ---- Career & Makuuchi records -----------------------------------------
    # Pattern in plain text: "Career Record:\n510-395-65"
    cr_m = re.search(r'Career Record:\s*\n([\d]+)-([\d]+)-([\d]+)', text)
    if cr_m:
        d["career_wins"], d["career_losses"], d["career_absences"] = cr_m.groups()
    else:
        d["career_wins"] = d["career_losses"] = d["career_absences"] = "?"

    mk_m = re.search(r'Makuuchi Records?:\s*\n([\d]+)-([\d]+)-([\d]+)', text)
    if mk_m:
        d["makuuchi_wins"], d["makuuchi_losses"], d["makuuchi_absences"] = mk_m.groups()
    else:
        d["makuuchi_wins"] = d["makuuchi_losses"] = d["makuuchi_absences"] = "?"

    # ---- Division championships & special prizes ---------------------------
    # Plain-text format after conversion:
    #   ![Makuuchi Division Championships](https://...prize01.gif)\n1
    prize_map = [
        ("champ_makuuchi",       "prize01"),
        ("champ_juryo",          "prize02"),
        ("champ_makushita",      "prize03"),
        ("champ_sandanme",       "prize04"),
        ("champ_jonidan",        "prize05"),
        ("champ_jonokuchi",      "prize06"),
        ("prize_outstanding",    "prize07"),
        ("prize_fighting_spirit","prize08"),
        ("prize_technique",      "prize09"),
        ("kinboshi",             "prize10"),
    ]
    for key, prize_file in prize_map:
        m = re.search(
            re.escape(prize_file) + r'\.gif\)[^\n]*\n(\d+)',
            text
        )
        d[key] = m.group(1) if m else "0"

    # ---- Winning techniques ------------------------------------------------
    # Plain-text:  "1.\n\noshidashi\n28%"
    tech_matches = re.findall(
        r'\d+\.\n\n([^\n]+)\n(\d+)%',
        text
    )
    d["techniques"] = [(t.strip(), p.strip()) for t, p in tech_matches[:4]
                       if t.strip().lower() != "etc"]

    # ---- Recent rankings (past year) ---------------------------------------
    # Plain-text block after the technique section:
    #   Maegashira #2\nJuly
    # Each entry is RANK\nMONTH, triggered by the rank_ic image lines.
    # The block appears after "Rankings for the Past Year"
    rankings_section = re.search(
        r'Rankings for the Past Year(.*?)(?:Debut\s*\n|Stablemates|$)',
        text, re.DOTALL
    )
    recent_rankings = []
    if rankings_section:
        rr_text = rankings_section.group(1)
        # Each ranking: lines like "\nSekiwake\nJuly\n"
        rr_matches = re.findall(
            r'\n((?:Yokozuna|Ozeki|Sekiwake|Komusubi|Maegashira[^\n]*))\n'
            r'(January|March|May|July|September|November)\n',
            rr_text
        )
        recent_rankings = [(rank.strip(), month.strip()) for rank, month in rr_matches[:6]]
    d["recent_rankings"] = recent_rankings

    # ---- Career milestones -------------------------------------------------
    # Plain text block near end:
    #   Debut\nMay, 2013\nJuryo Debut\nMarch, 2015\n...
    for label, key in [
        ("Debut",           "debut"),
        ("Juryo Debut",     "juryo_debut"),
        ("Makuuchi Debut",  "makuuchi_debut"),
        ("Sanyaku Debut",   "sanyaku_debut"),
        ("Highest Rank",    "highest_rank"),
    ]:
        m = re.search(r'\b' + re.escape(label) + r'\s*\n([^\n]+)', text)
        val = m.group(1).strip() if m else ""
        # Avoid accidentally picking up table rows (contain |)
        d[key] = val if val and "|" not in val else ""

    # ---- Tournament results ------------------------------------------------
    # Plain-text list items:
    #   - 2026 May East Maegashira #9 Abi Masatora 5-9 白丸 ...
    # We want: year, month, rank (East/West + division + number), record W-L[-A]
    # Notes: prize lines like "Kanto-sho(Fighting Spirit Prize)" follow some records
    MONTHS = "January|March|May|July|September|November"
    tourney_rows = []
    for m in re.finditer(
        r'^-\s+(20\d\d)\s+(' + MONTHS + r')\s+'
        r'((?:East|West)\s+\S+(?:\s+#\d+)?)\s+'   # rank
        r'[^\d\n]+?'                                # name (skip)
        r'(\d+)-(\d+)(?:-(\d+))?'                  # W-L[-A]
        r'([^\n]*)',                                # rest of line (prizes etc.)
        text, re.MULTILINE
    ):
        year, month, rank_raw = m.group(1), m.group(2), m.group(3)
        wins, losses, absences = m.group(4), m.group(5), m.group(6) or "0"
        rest = m.group(7).strip()

        # Pull out any special prize mentions
        prize_m = re.search(
            r'((?:Makuuchi Division Champion|Shukun-sho|Kanto-sho|Gino-sho)[^)]*\))',
            rest
        )
        notes = prize_m.group(1) if prize_m else ""

        tourney_rows.append({
            "basho":    f"{year} {month}",
            "rank":     rank_raw.strip(),
            "wins":     wins,
            "losses":   losses,
            "absences": absences,
            "notes":    notes,
        })
    d["tournament_rows"] = tourney_rows

    # ---- Stablemates -------------------------------------------------------
    # Appears as a markdown table section headed "Stablemates"
    # Row format:  | ![...](small.jpg)RANK  [NAME](profile_url) | [STABLE](url) |
    stablemates = []
    sm_section = re.search(
        r'### Stablemates\s*\n(.*?)(?:###|\Z)',
        text, re.DOTALL
    )
    if sm_section:
        for sm in re.finditer(
            r'\|\s*!\[.*?\]\([^)]+\)'     # thumbnail
            r'(.*?)'                       # rank text
            r'\[([^\]]+)\]'               # [NAME]
            r'\([^)]+profile/\d+[^)]*\)'  # (url)
            r'\s*\|',
            sm_section.group(1)
        ):
            rank_text = re.sub(r'\s+', ' ', sm.group(1)).strip()
            name = sm.group(2).strip()
            if name and name != ring_name:
                stablemates.append((name, rank_text))
    d["stablemates"] = stablemates[:6]

    return d


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------

def render_note(d: dict, ring_name: str) -> str:
    # Technique rows (skip "etc")
    tech_rows = ""
    for i, (tech, pct) in enumerate(d.get("techniques", []), 1):
        tech_rows += f"| {i} | {tech} | {pct}% |\n"
    tech_rows = tech_rows.rstrip() or "| — | — | — |"

    # Recent ranking rows  (rank, month)
    rr_rows = ""
    for rank, month in d.get("recent_rankings", []):
        rr_rows += f"| {month} | {rank} |\n"
    rr_rows = rr_rows.rstrip() or "| — | — |"

    # Tournament rows (most recent first, cap at 20 for readability)
    t_rows = ""
    for row in d.get("tournament_rows", [])[:20]:
        record = f"{row['wins']}-{row['losses']}-{row['absences']}"
        t_rows += f"| {row['basho']} | {row['rank']} | {record} | {row['notes']} |\n"
    t_rows = t_rows.rstrip() or "| — | — | — | — |"

    # Stablemate rows
    sm_rows = ""
    for name, rank in d.get("stablemates", []):
        sm_rows += f"| [[{name}]] | {rank} |\n"
    sm_rows = sm_rows.rstrip() or "| — | — |"

    return TEMPLATE.format(
        ring_name        = ring_name,
        date             = date.today().isoformat(),
        division         = "makuuchi",
        stable           = d.get("stable", ""),
        stable_tag       = d.get("stable_tag", ""),
        given_name       = d.get("given_name", ""),
        current_rank     = d.get("current_rank", ""),
        birthday         = d.get("birthday", ""),
        birthplace       = d.get("birthplace", ""),
        height           = d.get("height", ""),
        weight           = d.get("weight", ""),
        signature_moves  = d.get("signature_moves", ""),
        debut            = d.get("debut", ""),
        juryo_debut      = d.get("juryo_debut", ""),
        makuuchi_debut   = d.get("makuuchi_debut", ""),
        sanyaku_debut    = d.get("sanyaku_debut", ""),
        highest_rank     = d.get("highest_rank", ""),
        career_wins      = d.get("career_wins", "?"),
        career_losses    = d.get("career_losses", "?"),
        career_absences  = d.get("career_absences", "?"),
        makuuchi_wins    = d.get("makuuchi_wins", "?"),
        makuuchi_losses  = d.get("makuuchi_losses", "?"),
        makuuchi_absences= d.get("makuuchi_absences", "?"),
        champ_makuuchi   = d.get("champ_makuuchi", "0"),
        champ_juryo      = d.get("champ_juryo", "0"),
        champ_makushita  = d.get("champ_makushita", "0"),
        champ_sandanme   = d.get("champ_sandanme", "0"),
        champ_jonidan    = d.get("champ_jonidan", "0"),
        champ_jonokuchi  = d.get("champ_jonokuchi", "0"),
        prize_outstanding    = d.get("prize_outstanding", "0"),
        prize_fighting_spirit= d.get("prize_fighting_spirit", "0"),
        prize_technique      = d.get("prize_technique", "0"),
        kinboshi             = d.get("kinboshi", "0"),
        technique_rows       = tech_rows,
        recent_ranking_rows  = rr_rows,
        tournament_rows      = t_rows,
        stablemate_rows      = sm_rows,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scrape Makuuchi rikishi profiles into Obsidian notes."
    )
    parser.add_argument("--vault",      default="./rikishi_vault",
                        help="Output dir for .md notes (default: ./rikishi_vault)")
    parser.add_argument("--images-dir", default="./rikishi_images",
                        help="Output dir for .jpg portraits (default: ./rikishi_images)")
    parser.add_argument("--delay",      type=float, default=0.5,
                        help="Seconds between requests (default: 0.5)")
    parser.add_argument("--no-images",  action="store_true",
                        help="Skip image downloads")
    args = parser.parse_args()

    vault_dir  = Path(args.vault)
    images_dir = Path(args.images_dir)
    vault_dir.mkdir(parents=True, exist_ok=True)
    if not args.no_images:
        images_dir.mkdir(parents=True, exist_ok=True)

    print("Fetching Makuuchi roster …")
    roster_html = fetch(SEARCH_URL)
    roster = parse_roster(roster_html)
    print(f"Found {len(roster)} rikishi.\n")

    success, failed = 0, []

    for profile_id, ring_name in roster:
        profile_url = f"{PROFILE_URL}{profile_id}/"
        print(f"  [{profile_id}] {ring_name} …", end=" ", flush=True)

        try:
            text = fetch(profile_url, referer=SEARCH_URL)
            data = parse_profile(text, ring_name)

            # Write .md note
            note_path = vault_dir / f"{ring_name}.md"
            note_path.write_text(render_note(data, ring_name), encoding="utf-8")

            # Download portrait image
            img_status = ""
            if not args.no_images and data.get("image_url"):
                img_bytes = fetch(data["image_url"], binary=True, referer=profile_url)
                (images_dir / f"{ring_name}.jpg").write_bytes(img_bytes)
                img_status = " + image"

            print(f"✓ note{img_status}")
            success += 1

        except Exception as e:
            print(f"✗  {e}")
            failed.append((ring_name, str(e)))

        time.sleep(args.delay)

    print(f"\n{'─'*50}")
    print(f"Completed: {success}/{len(roster)}")
    if failed:
        print("Failed:")
        for name, err in failed:
            print(f"  {name}: {err}")
    print(f"Notes  → {vault_dir.resolve()}/")
    if not args.no_images:
        print(f"Images → {images_dir.resolve()}/")


if __name__ == "__main__":
    main()

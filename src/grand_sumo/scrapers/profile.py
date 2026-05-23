"""
profile.py
----------
Scrapes the Makuuchi division roster from sumo.or.jp, downloads each rikishi's
profile page and portrait image, and writes one Obsidian .md note per rikishi
using the rikishi-profile-template.md format.

The GUI drives this module via scrape_all_profiles().
"""

import re
import time
import urllib.request
from datetime import date
from pathlib import Path
from typing import Callable, Optional

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

def _fetch(url: str, binary: bool = False, referer: str = SEARCH_URL, timeout: int = 15):
    headers = {**HEADERS, "Referer": referer}
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read() if binary else resp.read().decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Roster parsing  (from the search page)
# ---------------------------------------------------------------------------

def parse_roster(html: str) -> list[tuple[str, str]]:
    """Return list of (profile_id, ring_name) for all Makuuchi rikishi."""
    # The search page returns HTML; match <a href="...profile/ID...">Name</a>
    pattern = (
        r'<a[^>]+href=["\'](?:https?://sumo\.or\.jp)?'
        r'/EnSumoDataRikishi/profile/(\d+)/?["\'][^>]*>'
        r'([^<]+)</a>'
    )
    seen: dict[str, str] = {}
    for m in re.finditer(pattern, html, re.IGNORECASE):
        pid, name = m.group(1), m.group(2).strip()
        if pid not in seen and name:
            seen[pid] = name
    return [(pid, name) for pid, name in seen.items()]


# ---------------------------------------------------------------------------
# Profile parsing
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

    # Strip units from height/weight
    d["height"] = re.sub(r"[^\d.]", "", d.get("height", ""))
    d["weight"] = re.sub(r"[^\d.]", "", d.get("weight", ""))

    # Stable
    stable_m = re.search(r'\[([^\]]+)\]\([^)]*EnSumoDataSumoBeya[^)]+\)', text)
    d["stable"] = stable_m.group(1).strip() if stable_m else ""
    d["stable_tag"] = re.sub(r'[^a-z0-9]+', '-', d["stable"].lower()).strip('-')

    # ---- Image URL ---------------------------------------------------------
    img_m = re.search(r'/img/sumo_data/rikishi/270x474/(\d+\.jpg)', text)
    d["image_url"] = (
        f"{BASE_URL}/img/sumo_data/rikishi/270x474/{img_m.group(1)}" if img_m else ""
    )

    # ---- Career & Makuuchi records -----------------------------------------
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
    prize_map = [
        ("champ_makuuchi",        "prize01"),
        ("champ_juryo",           "prize02"),
        ("champ_makushita",       "prize03"),
        ("champ_sandanme",        "prize04"),
        ("champ_jonidan",         "prize05"),
        ("champ_jonokuchi",       "prize06"),
        ("prize_outstanding",     "prize07"),
        ("prize_fighting_spirit", "prize08"),
        ("prize_technique",       "prize09"),
        ("kinboshi",              "prize10"),
    ]
    for key, prize_file in prize_map:
        m = re.search(re.escape(prize_file) + r'\.gif\)[^\n]*\n(\d+)', text)
        d[key] = m.group(1) if m else "0"

    # ---- Winning techniques ------------------------------------------------
    tech_matches = re.findall(r'\d+\.\n\n([^\n]+)\n(\d+)%', text)
    d["techniques"] = [(t.strip(), p.strip()) for t, p in tech_matches[:4]
                       if t.strip().lower() != "etc"]

    # ---- Recent rankings (past year) ---------------------------------------
    rankings_section = re.search(
        r'Rankings for the Past Year(.*?)(?:Debut\s*\n|Stablemates|$)',
        text, re.DOTALL
    )
    recent_rankings = []
    if rankings_section:
        rr_text = rankings_section.group(1)
        rr_matches = re.findall(
            r'\n((?:Yokozuna|Ozeki|Sekiwake|Komusubi|Maegashira[^\n]*))\n'
            r'(January|March|May|July|September|November)\n',
            rr_text
        )
        recent_rankings = [(rank.strip(), month.strip()) for rank, month in rr_matches[:6]]
    d["recent_rankings"] = recent_rankings

    # ---- Career milestones -------------------------------------------------
    for label, key in [
        ("Debut",           "debut"),
        ("Juryo Debut",     "juryo_debut"),
        ("Makuuchi Debut",  "makuuchi_debut"),
        ("Sanyaku Debut",   "sanyaku_debut"),
        ("Highest Rank",    "highest_rank"),
    ]:
        m = re.search(r'\b' + re.escape(label) + r'\s*\n([^\n]+)', text)
        val = m.group(1).strip() if m else ""
        d[key] = val if val and "|" not in val else ""

    # ---- Tournament results ------------------------------------------------
    MONTHS = "January|March|May|July|September|November"
    tourney_rows = []
    for m in re.finditer(
        r'^-\s+(20\d\d)\s+(' + MONTHS + r')\s+'
        r'((?:East|West)\s+\S+(?:\s+#\d+)?)\s+'
        r'[^\d\n]+?'
        r'(\d+)-(\d+)(?:-(\d+))?'
        r'([^\n]*)',
        text, re.MULTILINE
    ):
        year, month, rank_raw = m.group(1), m.group(2), m.group(3)
        wins, losses, absences = m.group(4), m.group(5), m.group(6) or "0"
        rest = m.group(7).strip()

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
    stablemates = []
    sm_section = re.search(r'### Stablemates\s*\n(.*?)(?:###|\Z)', text, re.DOTALL)
    if sm_section:
        for sm in re.finditer(
            r'\|\s*!\[.*?\]\([^)]+\)'
            r'(.*?)'
            r'\[([^\]]+)\]'
            r'\([^)]+profile/\d+[^)]*\)'
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
    tech_rows = ""
    for i, (tech, pct) in enumerate(d.get("techniques", []), 1):
        tech_rows += f"| {i} | {tech} | {pct}% |\n"
    tech_rows = tech_rows.rstrip() or "| — | — | — |"

    rr_rows = ""
    for rank, month in d.get("recent_rankings", []):
        rr_rows += f"| {month} | {rank} |\n"
    rr_rows = rr_rows.rstrip() or "| — | — |"

    t_rows = ""
    for row in d.get("tournament_rows", [])[:20]:
        record = f"{row['wins']}-{row['losses']}-{row['absences']}"
        t_rows += f"| {row['basho']} | {row['rank']} | {record} | {row['notes']} |\n"
    t_rows = t_rows.rstrip() or "| — | — | — | — |"

    sm_rows = ""
    for name, rank in d.get("stablemates", []):
        sm_rows += f"| [[{name}]] | {rank} |\n"
    sm_rows = sm_rows.rstrip() or "| — | — |"

    return TEMPLATE.format(
        ring_name             = ring_name,
        date                  = date.today().isoformat(),
        division              = "makuuchi",
        stable                = d.get("stable", ""),
        stable_tag            = d.get("stable_tag", ""),
        given_name            = d.get("given_name", ""),
        current_rank          = d.get("current_rank", ""),
        birthday              = d.get("birthday", ""),
        birthplace            = d.get("birthplace", ""),
        height                = d.get("height", ""),
        weight                = d.get("weight", ""),
        signature_moves       = d.get("signature_moves", ""),
        debut                 = d.get("debut", ""),
        juryo_debut           = d.get("juryo_debut", ""),
        makuuchi_debut        = d.get("makuuchi_debut", ""),
        sanyaku_debut         = d.get("sanyaku_debut", ""),
        highest_rank          = d.get("highest_rank", ""),
        career_wins           = d.get("career_wins", "?"),
        career_losses         = d.get("career_losses", "?"),
        career_absences       = d.get("career_absences", "?"),
        makuuchi_wins         = d.get("makuuchi_wins", "?"),
        makuuchi_losses       = d.get("makuuchi_losses", "?"),
        makuuchi_absences     = d.get("makuuchi_absences", "?"),
        champ_makuuchi        = d.get("champ_makuuchi", "0"),
        champ_juryo           = d.get("champ_juryo", "0"),
        champ_makushita       = d.get("champ_makushita", "0"),
        champ_sandanme        = d.get("champ_sandanme", "0"),
        champ_jonidan         = d.get("champ_jonidan", "0"),
        champ_jonokuchi       = d.get("champ_jonokuchi", "0"),
        prize_outstanding     = d.get("prize_outstanding", "0"),
        prize_fighting_spirit = d.get("prize_fighting_spirit", "0"),
        prize_technique       = d.get("prize_technique", "0"),
        kinboshi              = d.get("kinboshi", "0"),
        technique_rows        = tech_rows,
        recent_ranking_rows   = rr_rows,
        tournament_rows       = t_rows,
        stablemate_rows       = sm_rows,
    )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def scrape_all_profiles(
    vault_dir: Path,
    images_dir: Path,
    delay: float = 0.5,
    no_images: bool = False,
    progress_callback: Optional[Callable] = None,
) -> None:
    """Scrape all Makuuchi rikishi profiles and write Obsidian notes.

    Args:
        vault_dir: Output directory for .md notes
        images_dir: Output directory for .jpg portraits
        delay: Seconds to pause between HTTP requests
        no_images: If True, skip portrait downloads
        progress_callback: Optional callable receiving (name: str, status: str)
    """
    vault_dir.mkdir(parents=True, exist_ok=True)
    if not no_images:
        images_dir.mkdir(parents=True, exist_ok=True)

    def _log(name: str, status: str) -> None:
        if progress_callback:
            progress_callback(name, status)
        else:
            print(f"  [{name}] {status}")

    _log("roster", "Fetching Makuuchi roster...")
    roster_html = _fetch(SEARCH_URL)
    roster = parse_roster(roster_html)
    _log("roster", f"Found {len(roster)} rikishi.")

    success, failed = 0, []

    for profile_id, ring_name in roster:
        profile_url = f"{PROFILE_URL}{profile_id}/"
        try:
            text = _fetch(profile_url, referer=SEARCH_URL)
            data = parse_profile(text, ring_name)

            note_path = vault_dir / f"{ring_name}.md"
            note_path.write_text(render_note(data, ring_name), encoding="utf-8")

            img_status = ""
            if not no_images and data.get("image_url"):
                img_bytes = _fetch(data["image_url"], binary=True, referer=profile_url)
                (images_dir / f"{ring_name}.jpg").write_bytes(img_bytes)
                img_status = " + image"

            _log(ring_name, f"✓ note{img_status}")
            success += 1

        except Exception as e:
            _log(ring_name, f"✗ {e}")
            failed.append((ring_name, str(e)))

        time.sleep(delay)

    summary = f"Completed: {success}/{len(roster)}"
    if failed:
        failed_names = ", ".join(n for n, _ in failed)
        summary += f"  |  Failed: {failed_names}"
    _log("__summary__", summary)

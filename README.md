# Grand Sumo

Python client for the [Sumo API](https://sumo-api.com) and Obsidian vault exporter. Fetches rikishi profiles, tournament results, banzuke rankings, and torikumi match logs, then writes structured Markdown notes into an Obsidian vault.

## Features

- **Async & sync API clients** — `SumoClient` (async/httpx) and `SumoSyncClient` (sync wrapper)
- **Comprehensive data models** — Pydantic v2 models for all API endpoints
- **Obsidian vault export** — Rikishi pages, banzuke index, basho summaries, daily torikumi logs, heya (stable) pages
- **Portrait downloader** — Bulk download rikishi headshots from sumo.or.jp
- **Profile scraper** — Scrape rikishi profiles, career records, techniques, and rankings from sumo.or.jp
- **Desktop GUI** — Tkinter-based launcher for all operations

## Installation

```bash
pip install grand-sumo
```

For development:

```bash
pip install -e ".[dev]"
```

## Configuration

Set the vault path and basho ID via environment variable or the GUI:

| Variable | Default | Description |
|---|---|---|
| `GRAND_SUMO_VAULT` | `./data` | Path to your Obsidian vault |
| `CURRENT_BASHO` (in `config.py`) | `202605` | Current tournament in YYYYMM format |

## Usage

### CLI

```bash
sumo
```

Launches the tkinter desktop manager.

### Python API

```python
from grand_sumo import SumoClient, SumoSyncClient

# Async client
async with SumoClient() as client:
    rikishi = await client.get_rikishi("3842")
    banzuke = await client.get_banzuke("202501", "Makuuchi")
    torikumi = await client.get_torikumi("202501", "Makuuchi", 1)

# Sync client
with SumoSyncClient() as client:
    basho = client.get_basho("202501")
    stats = client.get_rikishi_stats("3842")
```

### Obsidian Export Pipeline

```python
from grand_sumo.exporters.obsidian import run_full_pipeline

run_full_pipeline(202501, vault_path="/path/to/vault")
```

Runs all 6 export steps:
1. Compile Makuuchi data
2. Write rikishi pages → `Rikishi/`
3. Write banzuke index → `Basho/Banzuke January 2025.md`
4. Write basho summary → `Basho/January 2025 Basho.md`
5. Write daily torikumi logs → `Torikumi/`
6. Write heya (stable) pages → `Heya/`

### Portrait Download

```python
from grand_sumo.exporters.images import download_rikishi_images

download_rikishi_images(output_dir="rikishi_images")
```

### Profile Scraper

```python
from grand_sumo.scrapers.profile import scrape_all_profiles

scrape_all_profiles(vault_dir="Rikishi", images_dir="rikishi_images")
```

## Client Reference

| Method | Description |
|---|---|
| `get_rikishi(id)` | Single rikishi by ID |
| `get_rikishis(...)` | List rikishi with filters |
| `get_rikishi_stats(id)` | Career statistics |
| `get_rikishi_matches(id, basho_id?)` | Match history |
| `get_rikishi_opponent_matches(id, opp, basho_id?)` | Head-to-head matches |
| `get_basho(basho_id)` | Tournament details |
| `get_banzuke(basho_id, division)` | Ranking charts |
| `get_torikumi(basho_id, division, day)` | Daily match cards |
| `get_kimarite(sort?, limit?, skip?)` | Technique usage stats |
| `get_kimarite_matches(kimarite, ...)` | Matches by technique |
| `get_measurements(basho_id?, rikishi_id?)` | Measurement changes |
| `get_ranks(basho_id?, rikishi_id?)` | Rank changes |
| `get_shikonas(basho_id?, rikishi_id?)` | Shikona (ring name) changes |

## Project Structure

```
src/grand_sumo/
├── __init__.py          # Package entry point
├── client.py            # SumoClient + SumoSyncClient
├── config.py            # Runtime configuration
├── models/              # Pydantic data models
│   ├── rikishi.py       # Rikishi, RikishiList
│   ├── basho.py         # Basho, RikishiPrize
│   ├── banzuke.py       # Banzuke, RikishiBanzuke
│   ├── torikumi.py      # Torikumi, YushoWinner
│   ├── match.py         # Match (unified across endpoints)
│   ├── kimarite.py      # Kimarite stats + match records
│   ├── measurements.py  # Measurement
│   ├── ranks.py         # Rank
│   ├── rikishi_matches.py
│   ├── rikishi_stats.py # RikishiStats, DivisionStats, Sansho
│   └── shikonas.py      # Shikona
├── exporters/
│   ├── obsidian.py      # Vault export pipeline
│   └── images.py        # Portrait image downloader
├── scrapers/
│   └── profile.py       # sumo.or.jp profile scraper
└── ui/
    └── app.py           # Tkinter desktop GUI

tests/
├── test_client.py       # 29 tests — client init, validation, mocked HTTP
├── test_models.py       # 22 tests — all Pydantic models
├── test_utils.py        # 11 tests — helpers + config
├── test_scraper.py      # 15 tests — roster/profile parsing, rendering
├── test_images.py       # 6 tests — image downloader
└── test_obsidian.py     # 11 tests — export functions with mocked client
```

## Testing

```bash
pytest           # 102 tests
pytest -v        # verbose
pytest --tb=long # full tracebacks
```

## Dependencies

- `httpx[http2]>=0.27` — HTTP client
- `pydantic>=2.0` — Data models
- `anyio>=4.0` — Async runtime
- `certifi` — SSL certificates
- `pandas` — Data handling

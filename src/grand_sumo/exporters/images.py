"""Download rikishi portrait images from sumo.or.jp."""

import re
import time
import urllib.request
from pathlib import Path
from typing import Callable, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RIKISHI = [
    ("Hoshoryu", 3842),
    ("Onosato", 4227),
    ("Kotozakura", 3661),
    ("Aonishiki", 4230),
    ("Kirishima", 3622),
    ("Atamifuji", 4055),
    ("Kotoshoho", 3840),
    ("Wakatakakage", 3761),
    ("Takayasu", 2775),
    ("Fujinokawa", 4191),
    ("Takanosho", 3265),
    ("Yoshinofuji", 4279),
    ("Ichiyamamoto", 3753),
    ("Hiradoumi", 3705),
    ("Oho", 3844),
    ("Daieisho", 3376),
    ("Gonoyama", 4079),
    ("Wakamotoharu", 3371),
    ("Shodai", 3521),
    ("Churanoumi", 3711),
    ("Fujiseiun", 4093),
    ("Chiyoshoma", 3207),
    ("Asakoryu", 4101),
    ("Oshoma", 4108),
    ("Asahakuryu", 4175),
    ("Abi", 3485),
    ("Nishikifuji", 3742),
    ("Asanoyama", 3682),
    ("Hakunofuji", 4187),
    ("Ura", 3616),
    ("Kinbozan", 4112),
    ("Shishi", 3990),
    ("Tokihayate", 3933),
    ("Kotoeiho", 4120),
    ("Tamawashi", 2629),
    ("Mitakeumi", 3620),
    ("Roga", 3907),
    ("Tobizaru", 3594),
    ("Oshoumi", 4025),
    ("Wakanosho", 4121),
    ("Ryuden", 2890),
    ("Fujiryoga", 4336),
]

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Referer": "https://sumo.or.jp/EnSumoDataRikishi/search/",
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _fetch_url(url: str, headers: dict, binary: bool = False, timeout: int = 15):
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read() if binary else resp.read().decode("utf-8", errors="replace")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def download_rikishi_images(
    output_dir: Path,
    progress_callback: Optional[Callable] = None,
) -> None:
    """Download portrait images for all rikishi in the RIKISHI list.

    Args:
        output_dir: Directory where .jpg files will be saved
        progress_callback: Optional callable receiving (name: str, status: str)
    """
    output_dir.mkdir(parents=True, exist_ok=True)

    def _log(name: str, status: str) -> None:
        if progress_callback:
            progress_callback(name, status)
        else:
            print(f"  {status}  {name}")

    # Work on a copy so we don't mutate the module-level dict
    headers = dict(HEADERS)
    success, failed = 0, []

    for name, profile_id in RIKISHI:
        profile_url = f"https://sumo.or.jp/EnSumoDataRikishi/profile/{profile_id}"
        try:
            headers["Referer"] = profile_url
            html = _fetch_url(profile_url, headers)

            match = re.search(r"/img/sumo_data/rikishi/270x474/(\d+\.jpg)", html)
            if not match:
                _log(name, "✗ image URL not found in profile page")
                failed.append(name)
                continue

            img_filename = match.group(1)
            img_url = f"https://sumo.or.jp/img/sumo_data/rikishi/270x474/{img_filename}"

            data = _fetch_url(img_url, headers, binary=True)
            out_path = output_dir / f"{name}.jpg"
            out_path.write_bytes(data)

            _log(name, f"✓ saved ({len(data):,} bytes)")
            success += 1

        except Exception as e:
            _log(name, f"✗ {e}")
            failed.append(name)

        time.sleep(0.4)  # be polite

    summary = f"Downloaded: {success}/{len(RIKISHI)}"
    if failed:
        summary += f"  |  Failed: {', '.join(failed)}"
    _log("__summary__", summary)

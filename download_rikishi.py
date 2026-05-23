#!/usr/bin/env python3
"""
Download rikishi profile images from sumo.or.jp and rename them to ring names.
Images are saved to ./rikishi_images/
"""

import urllib.request
import re
import time
import os

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


def fetch_url(url, binary=False, timeout=15):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read() if binary else resp.read().decode("utf-8", errors="replace")


def main():
    out_dir = os.path.join(os.path.dirname(__file__), "rikishi_images")
    os.makedirs(out_dir, exist_ok=True)

    success, failed = 0, []

    for name, profile_id in RIKISHI:
        profile_url = f"https://sumo.or.jp/EnSumoDataRikishi/profile/{profile_id}"
        try:
            # Update Referer to the profile page for the image request
            HEADERS["Referer"] = profile_url
            html = fetch_url(profile_url)

            match = re.search(r"/img/sumo_data/rikishi/270x474/(\d+\.jpg)", html)
            if not match:
                print(f"  ✗ {name}: image URL not found in profile page")
                failed.append(name)
                continue

            img_filename = match.group(1)
            img_url = f"https://sumo.or.jp/img/sumo_data/rikishi/270x474/{img_filename}"

            data = fetch_url(img_url, binary=True)
            out_path = os.path.join(out_dir, f"{name}.jpg")
            with open(out_path, "wb") as f:
                f.write(data)

            print(f"  ✓ {name}.jpg  ({len(data):,} bytes)")
            success += 1

        except Exception as e:
            print(f"  ✗ {name}: {e}")
            failed.append(name)

        time.sleep(0.4)  # be polite

    print(f"\n{'='*40}")
    print(f"Downloaded: {success}/{len(RIKISHI)}")
    if failed:
        print(f"Failed:     {', '.join(failed)}")
    print(f"Saved to:   {out_dir}/")


if __name__ == "__main__":
    main()

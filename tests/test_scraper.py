"""Tests for the sumo.or.jp scraper."""
import re
from unittest.mock import patch

from grand_sumo.scrapers.profile import (
    parse_roster,
    parse_profile,
    render_note,
    _table_value,
)

ROSTER_HTML = """
<html>
<body>
<a href="https://sumo.or.jp/EnSumoDataRikishi/profile/3842/">Hoshoryu</a>
<a href="https://sumo.or.jp/EnSumoDataRikishi/profile/4227/">Onosato</a>
<a href="/EnSumoDataRikishi/profile/3661/">Kotozakura</a>
</body>
</html>
"""

PROFILE_TEXT = """
| **Name** | Terunofuji |
| **Ring Name** | Terunofuji |
| **Current Rank** | Yokozuna East |
| **Birthday** | November 29, 1991 |
| **Birthplace** | Ulaanbaatar, Mongolia |
| **Height** | 192 cm |
| **Weight** | 165 kg |
| **Signature Maneuver** | Yorikiri |

[Some Stable](/EnSumoDataSumoBeya/123/)

Career Record:
700-200-50

Makuuchi Record:
400-100-30

prize01.gif)
6

prize02.gif)
2

prize10.gif)
3

1.

Yorikiri
45%

2.

Oshidashi
30%

Rankings for the Past Year
Yokozuna
January

Debut
2005

Juryo Debut
2007

Makuuchi Debut
2009

Sanyaku Debut
2011

Highest Rank
Yokozuna

- 2023 January East Yokozuna 14-1 Makuuchi Division Champion)
- 2023 March East Yokozuna 12-3


###  Stablemates
|  ![](img)  SomeName  [Stablemate](/EnSumoDataRikishi/profile/123/)  |
|  ![](img)  OtherName  [OtherGuy](/EnSumoDataRikishi/profile/456/)  |
"""


class TestParseRoster:
    def test_basic(self):
        result = parse_roster(ROSTER_HTML)
        assert len(result) == 3
        assert ("3842", "Hoshoryu") in result
        assert ("4227", "Onosato") in result
        assert ("3661", "Kotozakura") in result

    def test_empty(self):
        result = parse_roster("<html></html>")
        assert result == []


class TestTableValue:
    def test_basic(self):
        text = "| **Name** | Test Value |"
        assert _table_value(text, "Name") == "Test Value"

    def test_not_found(self):
        assert _table_value("| Foo | Bar |", "Missing") == ""


class TestParseProfile:
    def test_basic_fields(self):
        d = parse_profile(PROFILE_TEXT, "Terunofuji")
        assert d["given_name"] == "Terunofuji"
        assert d["current_rank"] == "Yokozuna East"
        assert d["height"] == "192"
        assert d["weight"] == "165"
        assert d["career_wins"] == "700"
        assert d["career_losses"] == "200"

    def test_with_stable(self):
        d = parse_profile(PROFILE_TEXT, "Terunofuji")
        assert d["stable"] == "Some Stable"
        assert d["stable_tag"] == "some-stable"

    def test_techniques(self):
        d = parse_profile(PROFILE_TEXT, "Terunofuji")
        assert len(d["techniques"]) == 2
        assert d["techniques"][0] == ("Yorikiri", "45")
        assert d["techniques"][1] == ("Oshidashi", "30")

    def test_recent_rankings(self):
        d = parse_profile(PROFILE_TEXT, "Terunofuji")
        assert len(d["recent_rankings"]) >= 1
        assert ("Yokozuna", "January") in d["recent_rankings"]

    def test_career_milestones(self):
        d = parse_profile(PROFILE_TEXT, "Terunofuji")
        assert d["debut"] == "2005"
        assert d["highest_rank"] == "Yokozuna"

    def test_tournament_rows(self):
        d = parse_profile(PROFILE_TEXT, "Terunofuji")
        assert len(d["tournament_rows"]) >= 2
        assert d["tournament_rows"][0]["wins"] == "14"
        assert d["tournament_rows"][0]["notes"] == "Makuuchi Division Champion)"

    def test_prizes(self):
        d = parse_profile(PROFILE_TEXT, "Terunofuji")
        assert d["champ_makuuchi"] == "6"
        assert d["champ_juryo"] == "2"
        assert d["kinboshi"] == "3"

    def test_image_url(self):
        text = 'src="/img/sumo_data/rikishi/270x474/1234.jpg"'
        d = parse_profile(text, "Test")
        assert d["image_url"] == "https://sumo.or.jp/img/sumo_data/rikishi/270x474/1234.jpg"

    def test_image_url_missing(self):
        d = parse_profile("no image here", "Test")
        assert d["image_url"] == ""


class TestRenderNote:
    def test_basic_render(self):
        d = {
            "given_name": "Test",
            "ring_name_raw": "Test",
            "current_rank": "M1e",
            "birthday": "Jan 1, 2000",
            "birthplace": "Tokyo",
            "height": "180",
            "weight": "150",
            "signature_moves": "Yorikiri",
            "stable": "Test Stable",
            "stable_tag": "test-stable",
            "image_url": "",
            "career_wins": "500",
            "career_losses": "200",
            "career_absences": "50",
            "makuuchi_wins": "300",
            "makuuchi_losses": "100",
            "makuuchi_absences": "30",
            "champ_makuuchi": "3",
            "champ_juryo": "1",
            "champ_makushita": "0",
            "champ_sandanme": "0",
            "champ_jonidan": "0",
            "champ_jonokuchi": "0",
            "prize_outstanding": "1",
            "prize_fighting_spirit": "2",
            "prize_technique": "0",
            "kinboshi": "1",
            "debut": "2020",
            "juryo_debut": "2022",
            "makuuchi_debut": "2024",
            "sanyaku_debut": "",
            "highest_rank": "Sekiwake",
            "techniques": [],
            "recent_rankings": [],
            "tournament_rows": [],
            "stablemates": [],
        }
        note = render_note(d, "Test")
        assert "# Test" in note
        assert "## Basic Information" in note
        assert "M1e" in note
        assert "Test Stable" in note


class TestScrapeAllProfiles:
    def test_dry_run_no_images(self, tmp_path):
        from grand_sumo.scrapers.profile import scrape_all_profiles

        with patch("grand_sumo.scrapers.profile._fetch") as mock_fetch:
            mock_fetch.return_value = ROSTER_HTML
            with patch("grand_sumo.scrapers.profile.time.sleep"):
                scrape_all_profiles(
                    vault_dir=tmp_path / "vault",
                    images_dir=tmp_path / "images",
                    delay=0,
                    no_images=True,
                )
        notes = list((tmp_path / "vault").iterdir())
        assert len(notes) > 0

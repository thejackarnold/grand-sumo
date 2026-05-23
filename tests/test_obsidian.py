"""Tests for the Obsidian vault exporter."""
from unittest.mock import MagicMock, patch

import pytest

from grand_sumo.exporters.obsidian import (
    compile_makuuchi_data,
    export_banzuke_page,
    export_basho_summary,
    export_heya_pages,
    export_rikishi_pages,
    export_torikumi_pages,
    export_tracker_page,
    fetch_rikishi_kimarite,
    format_basho_id,
    rank_sort_key,
    run_full_pipeline,
    _render_kkmk,
    _determine_current_day,
    _sort_rikishi_list,
)


class TestHelpers:
    def test_format_basho_id(self):
        assert format_basho_id(202501) == "January 2025"
        assert format_basho_id(202603) == "March 2026"

    def test_rank_sort_key(self):
        assert rank_sort_key("Yokozuna East") == (0, 0, 0)
        assert rank_sort_key("Maegashira 15 West") == (4, 15, 1)
        assert rank_sort_key("Unknown") == (99, 0, 0)


class TestFetchRikishiKimarite:
    def test_top_kimarite(self):
        mock_client = MagicMock()
        mock_match_win = MagicMock()
        mock_match_win.winner_id = 1
        mock_match_win.kimarite = "yorikiri"
        mock_match_loss = MagicMock()
        mock_match_loss.winner_id = 2
        mock_match_loss.kimarite = "oshidashi"
        mock_match_fusen = MagicMock()
        mock_match_fusen.winner_id = 1
        mock_match_fusen.kimarite = "fusen"
        mock_response = MagicMock()
        mock_response.records = [mock_match_win, mock_match_loss, mock_match_win, mock_match_fusen]
        mock_client.get_rikishi_matches.return_value = mock_response

        result = fetch_rikishi_kimarite(mock_client, 1)
        assert "Yorikiri" in result
        assert "2" in result

    def test_no_kimarite(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.records = []
        mock_client.get_rikishi_matches.return_value = mock_response

        result = fetch_rikishi_kimarite(mock_client, 1)
        assert result == "None"


class FakeRikishi:
    def __init__(self, id, shikona_en, sumodb_id, nsk_id, heya, birth_date,
                 shusshin, height, weight, debut, current_rank="", shikona_jp=""):
        self.id = id
        self.shikona_en = shikona_en
        self.shikona_jp = shikona_jp
        self.sumodb_id = sumodb_id
        self.nsk_id = nsk_id
        self.heya = heya
        self.birth_date = birth_date
        self.shusshin = shusshin
        self.height = height
        self.weight = weight
        self.debut = debut
        self.current_rank = current_rank


class FakeStats:
    def __init__(self, wins=0, losses=0, absences=0, yusho=0):
        self.total_wins = wins
        self.total_losses = losses
        self.total_absences = absences
        self.yusho = yusho

        class FakeSansho:
            Gino_sho = 0
            Kanto_sho = 0
            Shukun_sho = 0
        self.sansho = FakeSansho()


class TestCompileMakuuchiData:
    @pytest.fixture
    def mock_banzuke(self):
        from datetime import datetime
        entry = MagicMock()
        entry.rikishi_id = 1
        entry.rank = "Yokozuna East"
        entry.shikona_en = "Test Rikishi"
        banzuke = MagicMock()
        banzuke.east = [entry]
        banzuke.west = []
        return banzuke

    def test_compiles_data(self, mock_banzuke):
        mock_client = MagicMock()
        mock_client.get_banzuke.return_value = mock_banzuke
        mock_client.get_rikishi.return_value = FakeRikishi(
            id=1, shikona_en="Test Rikishi", sumodb_id=100, nsk_id=200,
            heya="Test Stable",
            birth_date=__import__("datetime").datetime(1990, 1, 15),
            shusshin="Tokyo", height=180, weight=150, debut="202001",
        )
        mock_client.get_rikishi_stats.return_value = FakeStats(wins=300, losses=100, yusho=2)
        mock_matches = MagicMock()
        mock_matches.records = []
        mock_client.get_rikishi_matches.return_value = mock_matches

        with patch("grand_sumo.exporters.obsidian.SumoSyncClient") as mock_cls:
            mock_cls.return_value.__enter__.return_value = mock_client
            result = compile_makuuchi_data(202501)

        assert len(result) == 1
        assert result[0]["Name"] == "Test Rikishi"
        assert result[0]["Wins"] == 300
        assert result[0]["Losses"] == 100
        assert result[0]["Yusho"] == 2


class TestExportRikishiPages:
    def test_writes_files(self, tmp_path):
        data = [{
            "Name": "Test Rikishi", "Name_Jp": "テスト", "Basho_Rank": "M1e",
            "Heya": "Test Stable", "Weight": 150, "Height": 180,
            "Birthplace": "Tokyo", "Birth_Date": "1990-01-15", "Age": 35,
            "Debut": "2020-01", "Wins": 300, "Losses": 100,
            "Absences": 50, "Win_Percentage": 75.0, "Yusho": 2,
            "Sansho": "Gino-sho (1)", "Top_Kimarite": "Yorikiri (10)",
            "SumoDB_ID": 100, "NSK_ID": 200, "ID": 1,
        }]
        export_rikishi_pages(data, vault_path=tmp_path)
        md_file = tmp_path / "Rikishi" / "Test_Rikishi.md"
        assert md_file.exists()
        content = md_file.read_text()
        assert "type: rikishi" in content
        assert "Test Rikishi" in content


class TestExportBanzukePage:
    def test_writes_file(self, tmp_path):
        data = [{
            "Name": "Test Rikishi", "Name_Jp": "テスト", "Basho_Rank": "Yokozuna East",
            "Heya": "Test Stable", "Weight": 150, "Height": 180,
            "Birthplace": "Tokyo", "Birth_Date": "1990-01-15", "Age": 35,
            "Debut": "2020-01", "Wins": 300, "Losses": 100,
            "Absences": 50, "Win_Percentage": 75.0, "Yusho": 2,
            "Sansho": "None", "Top_Kimarite": "None",
            "SumoDB_ID": 100, "NSK_ID": 200, "ID": 1,
        }]
        export_banzuke_page(data, 202501, vault_path=tmp_path)
        md_file = tmp_path / "Basho" / "Banzuke January 2025.md"
        assert md_file.exists()
        content = md_file.read_text()
        assert "type: banzuke" in content
        assert "Test Rikishi" in content


class TestExportBashoSummary:
    def test_writes_file(self, tmp_path):
        with patch("grand_sumo.exporters.obsidian.SumoSyncClient") as mock_cls:
            mock_client = MagicMock()
            basho = MagicMock()
            basho.start_date = __import__("datetime").datetime(2025, 1, 12)
            basho.end_date = __import__("datetime").datetime(2025, 1, 26)
            basho.location = "Tokyo"
            basho.yusho = None
            basho.special_prizes = None
            mock_client.get_basho.return_value = basho
            mock_cls.return_value.__enter__.return_value = mock_client
            export_basho_summary(202501, vault_path=tmp_path)
        md_file = tmp_path / "Basho" / "January 2025 Basho.md"
        assert md_file.exists()
        content = md_file.read_text(encoding="utf-8")
        assert "type: basho" in content


class TestExportTorikumiPages:
    def test_writes_files(self, tmp_path):
        with patch("grand_sumo.exporters.obsidian.SumoSyncClient") as mock_cls:
            mock_client = MagicMock()
            torikumi = MagicMock()
            match = MagicMock()
            match.east_shikona = "East"
            match.west_shikona = "West"
            match.east_rank = "M1e"
            match.west_rank = "M2w"
            match.kimarite = "yorikiri"
            match.winner_id = 1
            match.east_id = 1
            torikumi.matches = [match]
            mock_client.get_torikumi.return_value = torikumi
            mock_cls.return_value.__enter__.return_value = mock_client
            export_torikumi_pages(202501, vault_path=tmp_path, days=1)
        md_file = tmp_path / "Torikumi" / "January 2025 Day 01.md"
        assert md_file.exists()
        content = md_file.read_text(encoding="utf-8")
        assert "type: torikumi" in content


class TestExportHeyaPages:
    def test_writes_files(self, tmp_path):
        data = [{
            "Name": "Test Rikishi", "Name_Jp": "テスト", "Basho_Rank": "M1e",
            "Heya": "Test Stable", "Weight": 150, "Height": 180,
            "Birthplace": "Tokyo", "Birth_Date": "1990-01-15", "Age": 35,
            "Debut": "2020-01", "Wins": 300, "Losses": 100,
            "Absences": 50, "Win_Percentage": 75.0, "Yusho": 2,
            "Sansho": "None", "Top_Kimarite": "None",
            "SumoDB_ID": 100, "NSK_ID": 200, "ID": 1,
        }]
        export_heya_pages(data, vault_path=tmp_path)
        md_file = tmp_path / "Heya" / "Test Stable.md"
        assert md_file.exists()
        content = md_file.read_text()
        assert "type: heya" in content


class TestHelpersKkmk:
    def test_kachikoshi(self):
        assert _render_kkmk(8, 5) == "**KK**"
        assert _render_kkmk(10, 3) == "**KK**"

    def test_makekoshi(self):
        assert _render_kkmk(5, 8) == "**MK**"
        assert _render_kkmk(2, 12) == "**MK**"

    def test_neither(self):
        assert _render_kkmk(7, 6) == ""
        assert _render_kkmk(0, 0) == ""


class TestDetermineCurrentDay:
    def test_with_data(self):
        client = MagicMock()

        def torikumi_side_effect(basho_id, division, day):
            t = MagicMock()
            if day <= 3:
                t.matches = [MagicMock()]
            else:
                t.matches = []
            return t

        client.get_torikumi.side_effect = torikumi_side_effect
        assert _determine_current_day(client, "202605") == 3

    def test_no_data(self):
        client = MagicMock()
        client.get_torikumi.side_effect = Exception("No data")
        assert _determine_current_day(client, "202605") == 0


class TestSortRikishiList:
    def test_sorts_by_rank(self):
        rikishi_map = {
            1: {"rank": "Maegashira 5 East"},
            2: {"rank": "Yokozuna East"},
            3: {"rank": "Ozeki 1 West"},
        }
        sorted_items = _sort_rikishi_list(rikishi_map)
        ranks = [data["rank"] for _, data in sorted_items]
        assert ranks == ["Yokozuna East", "Ozeki 1 West", "Maegashira 5 East"]


class TestExportTrackerPage:
    def test_writes_file(self, tmp_path):
        import datetime

        with patch("grand_sumo.exporters.obsidian.SumoSyncClient") as mock_cls:
            mock_client = MagicMock()

            # Basho mock
            basho = MagicMock()
            basho.start_date = datetime.datetime(2026, 5, 10)
            basho.end_date = datetime.datetime(2026, 5, 24)
            basho.location = "Tokyo"
            mock_client.get_basho.return_value = basho

            # Banzuke mock — 4 rikishi across ranks
            def make_entry(rid, name, rank, side, wins, losses, absences):
                e = MagicMock()
                e.rikishi_id = rid
                e.shikona_en = name
                e.rank = rank
                e.side = side
                e.wins = wins
                e.losses = losses
                e.absences = absences
                return e

            east = [
                make_entry(1, "Hoshoryu", "Yokozuna 1 East", "East", 0, 2, 12),
                make_entry(3, "Atamifuji", "Sekiwake 1 East", "East", 7, 6, 0),
            ]
            west = [
                make_entry(2, "Onosato", "Yokozuna 1 West", "West", 0, 0, 14),
                make_entry(4, "Wakatakakage", "Komusubi 1 East", "West", 10, 3, 0),
            ]
            banzuke = MagicMock()
            banzuke.east = east
            banzuke.west = west
            mock_client.get_banzuke.return_value = banzuke

            # Torikumi mock — days 1-2 have data, day 3+ empty
            def torikumi_side(basho_id, division, day):
                t = MagicMock()
                if day == 1:
                    m1 = MagicMock()
                    m1.east_id = 1; m1.west_id = 2; m1.winner_id = 1
                    m1.kimarite = "yorikiri"
                    m2 = MagicMock()
                    m2.east_id = 3; m2.west_id = 4; m2.winner_id = 4
                    m2.kimarite = "oshidashi"
                    t.matches = [m1, m2]
                elif day == 2:
                    m1 = MagicMock()
                    m1.east_id = 1; m1.west_id = 3; m1.winner_id = 1
                    m1.kimarite = "yorikiri"
                    m2 = MagicMock()
                    m2.east_id = 2; m2.west_id = 4; m2.winner_id = 2
                    m2.kimarite = "oshidashi"
                    t.matches = [m1, m2]
                else:
                    t.matches = []
                return t

            mock_client.get_torikumi.side_effect = torikumi_side
            mock_cls.return_value.__enter__.return_value = mock_client

            export_tracker_page(202605, vault_path=tmp_path)

        md_file = tmp_path / "Basho" / "May 2026 Tracker.md"
        assert md_file.exists()
        content = md_file.read_text(encoding="utf-8")

        # Check basic structure
        assert "type: tracker" in content
        assert "basho_id: 202605" in content
        assert "May 2026" in content
        assert "Tournament Tracker" in content
        assert "Day 2 of 15" in content  # current_day=2
        assert "13 days remaining" in content
        assert "Tokyo" in content

        # Check rikishi names appear
        assert "Hoshoryu" in content
        assert "Onosato" in content
        assert "Atamifuji" in content
        assert "Wakatakakage" in content

        # Check day grid appears
        assert "1  2  3" in content  # day header
        assert "W  W" in content  # Hoshoryu's results

        # Check sections exist
        assert "Yusho Race" in content
        assert "Yokozuna · Ozeki" in content
        assert "Sekiwake · Komusubi" in content
        assert "Maegashira" in content

        # Check KK badge (Wakatakakage has 10W)
        assert "**KK**" in content
        # Check Hoshoryu's absences show in the row (not just legend)
        assert "12" in content  # absences count

        # Check GB column
        assert "—" in content  # leader gets dash
        assert "GB" in content


class TestRunFullPipeline:
    def test_runs_all_steps(self, tmp_path):
        with patch("grand_sumo.exporters.obsidian.SumoSyncClient") as mock_cls:
            mock_client = MagicMock()

            entry = MagicMock()
            entry.rikishi_id = 1
            entry.rank = "M1e"
            entry.shikona_en = "Test"
            entry.side = "East"
            entry.wins = 10
            entry.losses = 5
            entry.absences = 0
            banzuke = MagicMock()
            banzuke.east = [entry]
            banzuke.west = []
            mock_client.get_banzuke.return_value = banzuke
            mock_client.get_rikishi.return_value = FakeRikishi(
                id=1, shikona_en="Test", sumodb_id=100, nsk_id=200,
                heya="Stable",
                birth_date=__import__("datetime").datetime(1990, 1, 15),
                shusshin="Tokyo", height=180, weight=150, debut="202001",
            )
            mock_client.get_rikishi_stats.return_value = FakeStats(
                wins=10, losses=5, yusho=1
            )
            mock_matches = MagicMock()
            mock_matches.records = []
            mock_client.get_rikishi_matches.return_value = mock_matches
            basho = MagicMock()
            basho.start_date = __import__("datetime").datetime(2025, 1, 12)
            basho.end_date = __import__("datetime").datetime(2025, 1, 26)
            basho.location = "Tokyo"
            basho.yusho = None
            basho.special_prizes = None
            mock_client.get_basho.return_value = basho
            torikumi = MagicMock()
            torikumi.matches = []
            mock_client.get_torikumi.return_value = torikumi
            mock_cls.return_value.__enter__.return_value = mock_client

            run_full_pipeline(202501, vault_path=tmp_path)

        assert (tmp_path / "Rikishi").exists()
        assert (tmp_path / "Basho").exists()
        assert (tmp_path / "Torikumi").exists()
        assert (tmp_path / "Heya").exists()

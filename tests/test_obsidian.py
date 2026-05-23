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
    fetch_rikishi_kimarite,
    format_basho_id,
    rank_sort_key,
    run_full_pipeline,
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


class TestRunFullPipeline:
    def test_runs_all_steps(self, tmp_path):
        with patch("grand_sumo.exporters.obsidian.SumoSyncClient") as mock_cls:
            mock_client = MagicMock()

            entry = MagicMock()
            entry.rikishi_id = 1
            entry.rank = "M1e"
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

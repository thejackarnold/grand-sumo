"""Tests for utility functions in exporters and config."""
from grand_sumo.exporters.obsidian import format_basho_id, rank_sort_key
from grand_sumo.config import CURRENT_BASHO, DEFAULT_VAULT_PATH


class TestFormatBashoId:
    def test_march(self):
        assert format_basho_id(202603) == "March 2026"

    def test_january(self):
        assert format_basho_id(202501) == "January 2025"

    def test_may(self):
        assert format_basho_id(202505) == "May 2025"

    def test_july(self):
        assert format_basho_id(202507) == "July 2025"

    def test_september(self):
        assert format_basho_id(202509) == "September 2025"

    def test_november(self):
        assert format_basho_id(202511) == "November 2025"


class TestRankSortKey:
    def test_yokozuna_east(self):
        key = rank_sort_key("Yokozuna East")
        assert key == (0, 0, 0)

    def test_yokozuna_west(self):
        key = rank_sort_key("Yokozuna West")
        assert key == (0, 0, 1)

    def test_ozeki_1_east(self):
        key = rank_sort_key("Ozeki 1 East")
        assert key == (1, 1, 0)

    def test_maegashira_15_west(self):
        key = rank_sort_key("Maegashira 15 West")
        assert key == (4, 15, 1)

    def test_unknown_rank(self):
        key = rank_sort_key("Some Unknown Rank")
        assert key == (99, 0, 0)


class TestConfig:
    def test_current_basho_is_int(self):
        assert isinstance(CURRENT_BASHO, int)

    def test_default_vault_path_is_path(self):
        assert DEFAULT_VAULT_PATH is not None

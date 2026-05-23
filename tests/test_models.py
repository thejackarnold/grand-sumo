"""Tests for all Pydantic models."""
from datetime import datetime

import pytest
from pydantic import ValidationError

from grand_sumo.models import (
    Banzuke,
    Basho,
    KimariteMatch,
    KimariteMatchesResponse,
    KimariteRecord,
    KimariteResponse,
    Match,
    Measurement,
    Rank,
    Rikishi,
    RikishiBanzuke,
    RikishiList,
    RikishiMatchesResponse,
    RikishiOpponentMatchesResponse,
    RikishiPrize,
    RikishiStats,
    Shikona,
    Torikumi,
    YushoWinner,
)


class TestRikishi:
    def test_minimal(self):
        data = {
            "id": 1,
            "sumodbId": 100,
            "nskId": 200,
            "shikonaEn": "Test Rikishi",
            "shikonaJp": "テスト力士",
            "currentRank": "M1e",
            "heya": "Test Stable",
            "birthDate": "1990-01-15T00:00:00Z",
            "shusshin": "Tokyo",
            "height": 180,
            "weight": 150,
            "debut": "202001",
        }
        r = Rikishi.model_validate(data)
        assert r.id == 1
        assert r.sumodb_id == 100
        assert r.shikona_en == "Test Rikishi"
        assert r.heya == "Test Stable"
        assert isinstance(r.birth_date, datetime)

    def test_defaults(self):
        data = {
            "id": 2,
            "sumodbId": 101,
            "shikonaEn": "Another",
            "heya": "Heya",
            "birthDate": "1995-06-01T00:00:00Z",
            "shusshin": "Osaka",
            "height": 175,
            "weight": 130,
            "debut": "201901",
        }
        r = Rikishi.model_validate(data)
        assert r.nsk_id == 0
        assert r.shikona_jp == ""
        assert r.current_rank == ""
        assert r.intai is None


class TestRikishiList:
    def test_valid(self):
        data = {
            "limit": 10,
            "skip": 0,
            "total": 1,
            "records": [
                {
                    "id": 1,
                    "sumodbId": 100,
                    "shikonaEn": "Rikishi A",
                    "heya": "Stable",
                    "birthDate": "1990-01-01T00:00:00Z",
                    "shusshin": "Tokyo",
                    "height": 180,
                    "weight": 140,
                    "debut": "202001",
                }
            ],
        }
        rl = RikishiList.model_validate(data)
        assert rl.total == 1
        assert len(rl.records) == 1
        assert rl.records[0].shikona_en == "Rikishi A"


class TestMatch:
    def test_minimal(self):
        m = Match(bashoId="202501", day=5)
        assert m.basho_id == "202501"
        assert m.day == 5
        assert m.division is None

    def test_from_torikumi(self):
        data = {
            "bashoId": "202501",
            "division": "Makuuchi",
            "day": 3,
            "matchNo": 1,
            "eastId": 10,
            "eastShikona": "East Rikishi",
            "eastRank": "M1e",
            "westId": 20,
            "westShikona": "West Rikishi",
            "westRank": "M2w",
            "kimarite": "yorikiri",
            "winnerId": 10,
            "winnerEn": "East Rikishi",
            "winnerJp": "イースト",
        }
        m = Match.from_torikumi(data)
        assert m.basho_id == "202501"
        assert m.day == 3
        assert m.match_no == 1
        assert m.east_id == 10
        assert m.west_shikona == "West Rikishi"
        assert m.kimarite == "yorikiri"

    def test_from_banzuke(self):
        data = {
            "bashoId": "202501",
            "result": "win",
            "opponentID": 30,
            "opponentShikonaEn": "Opponent",
            "kimarite": "oshidashi",
        }
        m = Match.from_banzuke(data)
        assert m.result == "win"
        assert m.opponent_id == 30
        assert m.day == 0
        assert m.kimarite == "oshidashi"

    def test_invalid_result(self):
        with pytest.raises(ValidationError):
            Match(bashoId="202501", day=1, result="invalid_result")


class TestBasho:
    def test_minimal(self):
        data = {
            "date": "202501",
            "startDate": "2025-01-12T00:00:00Z",
            "endDate": "2025-01-26T00:00:00Z",
        }
        b = Basho.model_validate(data)
        assert b.date == "202501"
        assert b.location is None
        assert b.yusho is None
        assert b.special_prizes is None

    def test_with_prizes(self):
        data = {
            "date": "202505",
            "startDate": "2025-05-11T00:00:00Z",
            "endDate": "2025-05-25T00:00:00Z",
            "location": "Tokyo",
            "yusho": [
                {"type": "Makuuchi", "rikishiId": 1, "shikonaEn": "Winner", "shikonaJp": "ウィナー"}
            ],
            "specialPrizes": [
                {"type": "Kanto-sho", "rikishiId": 2, "shikonaEn": "Fighter", "shikonaJp": "ファイター"}
            ],
        }
        b = Basho.model_validate(data)
        assert b.location == "Tokyo"
        assert len(b.yusho) == 1
        assert b.yusho[0].shikona_en == "Winner"
        assert len(b.special_prizes) == 1


class TestBanzuke:
    def test_valid(self):
        data = {
            "bashoId": "202501",
            "division": "Makuuchi",
            "east": [
                {
                    "side": "East",
                    "rikishiID": 1,
                    "shikonaEn": "East Rikishi",
                    "rank": "Y1",
                    "wins": 12,
                    "losses": 3,
                    "absences": 0,
                    "record": [],
                }
            ],
            "west": [
                {
                    "side": "West",
                    "rikishiID": 2,
                    "shikonaEn": "West Rikishi",
                    "rank": "O1",
                    "wins": 10,
                    "losses": 5,
                    "absences": 0,
                    "record": [],
                }
            ],
        }
        b = Banzuke.model_validate(data)
        assert b.basho_id == "202501"
        assert b.division == "Makuuchi"
        assert len(b.east) == 1
        assert len(b.west) == 1
        assert b.east[0].shikona_en == "East Rikishi"
        assert b.west[0].rikishi_id == 2


class TestTorikumi:
    def test_valid(self):
        data = {
            "bashoId": "202501",
            "division": "Makuuchi",
            "day": 1,
            "torikumi": [
                {
                    "bashoId": "202501",
                    "division": "Makuuchi",
                    "day": 1,
                    "matchNo": 1,
                    "eastId": 10,
                    "eastShikona": "East",
                    "eastRank": "M1e",
                    "westId": 20,
                    "westShikona": "West",
                    "westRank": "M2w",
                    "kimarite": "yorikiri",
                    "winnerId": 10,
                    "winnerEn": "East",
                    "winnerJp": "イースト",
                }
            ],
        }
        t = Torikumi.model_validate(data)
        assert t.basho_id == "202501"
        assert t.day == 1
        assert len(t.matches) == 1
        assert t.matches[0].east_shikona == "East"


class TestKimarite:
    def test_kimarite_record(self):
        data = {"count": 100, "lastUsage": "202501-5", "kimarite": "yorikiri"}
        kr = KimariteRecord.model_validate(data)
        assert kr.count == 100
        assert kr.kimarite == "yorikiri"

    def test_kimarite_response(self):
        data = {
            "limit": 5,
            "skip": 0,
            "sortField": "count",
            "sortOrder": "desc",
            "records": [
                {"count": 100, "lastUsage": "202501-5", "kimarite": "yorikiri"},
                {"count": 80, "lastUsage": "202501-3", "kimarite": "oshidashi"},
            ],
        }
        resp = KimariteResponse(**data)
        assert len(resp.records) == 2
        assert resp.sort_field == "count"

    def test_kimarite_match(self):
        data = {
            "id": "202501-1-1-10-20",
            "bashoId": "202501",
            "division": "Makuuchi",
            "day": 1,
            "matchNo": 1,
            "eastId": 10,
            "eastShikona": "East",
            "eastRank": "M1e",
            "westId": 20,
            "westShikona": "West",
            "westRank": "M2w",
            "kimarite": "yorikiri",
            "winnerId": 10,
            "winnerEn": "East",
            "winnerJp": "イースト",
        }
        km = KimariteMatch.model_validate(data)
        assert km.basho_id == "202501"
        assert km.kimarite == "yorikiri"

    def test_kimarite_matches_response(self):
        data = {
            "limit": 10,
            "skip": 0,
            "total": 1,
            "records": [
                {
                    "id": "202501-1-1-10-20",
                    "bashoId": "202501",
                    "division": "Makuuchi",
                    "day": 1,
                    "matchNo": 1,
                    "eastId": 10,
                    "eastShikona": "East",
                    "eastRank": "M1e",
                    "westId": 20,
                    "westShikona": "West",
                    "westRank": "M2w",
                    "kimarite": "yorikiri",
                    "winnerId": 10,
                    "winnerEn": "East",
                    "winnerJp": "イースト",
                }
            ],
        }
        resp = KimariteMatchesResponse(**data)
        assert resp.total == 1


class TestMeasurement:
    def test_valid(self):
        data = {
            "id": "202501-1",
            "bashoId": "202501",
            "rikishiId": 1,
            "height": 180.5,
            "weight": 150.2,
        }
        m = Measurement.model_validate(data)
        assert m.basho_id == "202501"
        assert m.rikishi_id == 1
        assert m.height == 180.5


class TestRank:
    def test_valid(self):
        data = {
            "id": "202501-1",
            "bashoId": "202501",
            "rikishiId": 1,
            "rankValue": 1,
            "rank": "Yokozuna",
        }
        r = Rank.model_validate(data)
        assert r.basho_id == "202501"
        assert r.rank_value == 1


class TestShikona:
    def test_valid(self):
        data = {
            "id": "202501-1",
            "bashoId": "202501",
            "rikishiId": 1,
            "shikonaEn": "New Name",
            "shikonaJp": "新しい名前",
        }
        s = Shikona.model_validate(data)
        assert s.shikona_en == "New Name"


class TestRikishiMatchesResponse:
    def test_valid(self):
        data = {
            "limit": 10,
            "skip": 0,
            "total": 2,
            "records": [
                {"bashoId": "202501", "day": 1},
                {"bashoId": "202501", "day": 2},
            ],
        }
        resp = RikishiMatchesResponse.model_validate(data)
        assert resp.total == 2
        assert len(resp.records) == 2


class TestRikishiOpponentMatchesResponse:
    def test_valid(self):
        data = {
            "total": 5,
            "rikishiWins": 3,
            "opponentWins": 2,
            "kimariteWins": {"yorikiri": 2},
            "kimariteLosses": {"oshidashi": 1},
            "matches": [
                {"bashoId": "202501", "day": 1},
                {"bashoId": "202501", "day": 2},
            ],
        }
        resp = RikishiOpponentMatchesResponse.model_validate(data)
        assert resp.rikishi_wins == 3
        assert resp.opponent_wins == 2
        assert resp.kimarite_wins["yorikiri"] == 2


class TestRikishiStats:
    def test_valid(self):
        data = {
            "basho": 50,
            "totalMatches": 500,
            "totalWins": 300,
            "totalLosses": 195,
            "totalAbsences": 5,
            "yusho": 3,
            "absenceByDivision": {"Makuuchi": 2},
            "bashoByDivision": {"Makuuchi": 30},
            "lossByDivision": {"Makuuchi": 100},
            "totalByDivision": {"Makuuchi": 300},
            "winsByDivision": {"Makuuchi": 200},
            "yushoByDivision": {"Makuuchi": 3},
            "sansho": {"Gino-sho": 2, "Kanto-sho": 1, "Shukun-sho": 0},
        }
        s = RikishiStats.model_validate(data)
        assert s.basho == 50
        assert s.total_matches == 500
        assert s.sansho.Gino_sho == 2
        assert s.yusho_by_division.Makuuchi == 3


class TestRikishiBanzuke:
    def test_valid(self):
        data = {
            "side": "East",
            "rikishiID": 1,
            "shikonaEn": "Test",
            "rank": "M1e",
            "wins": 8,
            "losses": 7,
            "absences": 0,
        }
        rb = RikishiBanzuke.model_validate(data)
        assert rb.rikishi_id == 1
        assert rb.shikona_en == "Test"
        assert rb.wins == 8


class TestRikishiPrize:
    def test_valid(self):
        data = {
            "type": "Makuuchi",
            "rikishiId": 1,
            "shikonaEn": "Champ",
            "shikonaJp": "チャンプ",
        }
        rp = RikishiPrize.model_validate(data)
        assert rp.type == "Makuuchi"


class TestYushoWinner:
    def test_valid(self):
        data = {
            "id": "1",
            "shikonaEn": "Winner",
            "shikonaJp": "ウィナー",
            "rank": "Y1",
            "record": "14-1",
        }
        yw = YushoWinner.model_validate(data)
        assert yw.shikona_en == "Winner"

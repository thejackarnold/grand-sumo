"""Tests for SumoClient and SumoSyncClient."""
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from grand_sumo import SumoClient, SumoSyncClient


@pytest.fixture
def mock_client():
    """Create a SumoClient with mocked HTTP transport."""
    client = SumoClient(base_url="https://test.example.com")
    return client


@pytest.fixture
def sample_rikishi_data():
    return {
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


class TestSumoClientInit:
    def test_defaults(self):
        client = SumoClient()
        assert client.base_url == "https://sumo-api.com"
        assert client.verify_ssl is True
        assert client.connect_timeout == 5.0
        assert client.max_retries == 2

    def test_custom_values(self):
        client = SumoClient(
            base_url="https://custom.example.com",
            verify_ssl=False,
            connect_timeout=10.0,
            max_retries=0,
        )
        assert client.base_url == "https://custom.example.com"
        assert client.verify_ssl is False
        assert client.connect_timeout == 10.0
        assert client.max_retries == 0


class TestSumoClientValidation:
    """Tests for client-side validation (no HTTP calls)."""

    @pytest.mark.asyncio
    async def test_not_context_manager(self):
        client = SumoClient()
        with pytest.raises(RuntimeError, match="async context manager"):
            await client._make_request("GET", "/test")

    @pytest.mark.asyncio
    async def test_get_rikishi_matches_invalid_id(self, mock_client):
        with pytest.raises(ValueError, match="positive"):
            await mock_client.get_rikishi_matches(rikishi_id=0)

    @pytest.mark.asyncio
    async def test_get_rikishi_matches_invalid_basho_id(self, mock_client):
        with pytest.raises(ValueError, match="YYYYMM"):
            await mock_client.get_rikishi_matches(rikishi_id=1, basho_id="invalid")

    @pytest.mark.asyncio
    async def test_get_rikishi_opponent_matches_invalid_id(self, mock_client):
        with pytest.raises(ValueError, match="positive"):
            await mock_client.get_rikishi_opponent_matches(rikishi_id=-1, opponent_id=1)

    @pytest.mark.asyncio
    async def test_get_basho_invalid_id_format(self, mock_client):
        with pytest.raises(ValueError, match="YYYYMM"):
            await mock_client.get_basho(basho_id="abc")

    @pytest.mark.asyncio
    async def test_get_basho_future_date(self, mock_client):
        with pytest.raises(ValueError, match="future"):
            await mock_client.get_basho(basho_id="299901")

    @pytest.mark.asyncio
    async def test_get_banzuke_invalid_division(self, mock_client):
        with pytest.raises(ValueError, match="Invalid division"):
            await mock_client.get_banzuke(basho_id="202501", division="Invalid")

    @pytest.mark.asyncio
    async def test_get_banzuke_future_basho(self, mock_client):
        with pytest.raises(ValueError, match="future"):
            await mock_client.get_banzuke(basho_id="299901", division="Makuuchi")

    @pytest.mark.asyncio
    async def test_get_banzuke_invalid_basho_id(self, mock_client):
        with pytest.raises(ValueError, match="YYYYMM"):
            await mock_client.get_banzuke(basho_id="short", division="Makuuchi")

    @pytest.mark.asyncio
    async def test_get_banzuke_invalid_basho_id_nonnumeric(self, mock_client):
        with pytest.raises(ValueError, match="YYYYMM"):
            await mock_client.get_banzuke(basho_id="20a501", division="Makuuchi")

    @pytest.mark.asyncio
    async def test_get_torikumi_invalid_division(self, mock_client):
        with pytest.raises(ValueError, match="Invalid division"):
            await mock_client.get_torikumi(basho_id="202501", division="Invalid", day=1)

    @pytest.mark.asyncio
    async def test_get_torikumi_invalid_day(self, mock_client):
        with pytest.raises(ValueError, match="Day must be between 1 and 20"):
            await mock_client.get_torikumi(basho_id="202501", division="Makuuchi", day=0)

    @pytest.mark.asyncio
    async def test_get_torikumi_day_too_high(self, mock_client):
        with pytest.raises(ValueError, match="Day must be between 1 and 20"):
            await mock_client.get_torikumi(basho_id="202501", division="Makuuchi", day=21)

    @pytest.mark.asyncio
    async def test_get_torikumi_future_basho(self, mock_client):
        with pytest.raises(ValueError, match="future"):
            await mock_client.get_torikumi(basho_id="299901", division="Makuuchi", day=1)

    @pytest.mark.asyncio
    async def test_get_kimarite_invalid_sort_field(self, mock_client):
        with pytest.raises(ValueError, match="sort field"):
            await mock_client.get_kimarite(sort_field="invalid")

    @pytest.mark.asyncio
    async def test_get_kimarite_invalid_sort_order(self, mock_client):
        with pytest.raises(ValueError, match="Sort order"):
            await mock_client.get_kimarite(sort_order="invalid")

    @pytest.mark.asyncio
    async def test_get_kimarite_invalid_limit(self, mock_client):
        with pytest.raises(ValueError, match="positive"):
            await mock_client.get_kimarite(limit=0)

    @pytest.mark.asyncio
    async def test_get_kimarite_negative_skip(self, mock_client):
        with pytest.raises(ValueError, match="non-negative"):
            await mock_client.get_kimarite(skip=-1)

    @pytest.mark.asyncio
    async def test_get_kimarite_matches_empty(self, mock_client):
        with pytest.raises(ValueError, match="empty"):
            await mock_client.get_kimarite_matches(kimarite="")

    @pytest.mark.asyncio
    async def test_get_kimarite_matches_invalid_sort(self, mock_client):
        with pytest.raises(ValueError, match="Sort order"):
            await mock_client.get_kimarite_matches(kimarite="yorikiri", sort_order="bad")

    @pytest.mark.asyncio
    async def test_get_kimarite_matches_limit_too_high(self, mock_client):
        with pytest.raises(ValueError, match="1000"):
            await mock_client.get_kimarite_matches(kimarite="yorikiri", limit=1001)

    @pytest.mark.asyncio
    async def test_get_kimarite_matches_negative_skip(self, mock_client):
        with pytest.raises(ValueError, match="non-negative"):
            await mock_client.get_kimarite_matches(kimarite="yorikiri", skip=-1)

    @pytest.mark.asyncio
    async def test_get_measurements_no_params(self, mock_client):
        with pytest.raises(ValueError, match="must be provided"):
            await mock_client.get_measurements()

    @pytest.mark.asyncio
    async def test_get_measurements_invalid_basho_id(self, mock_client):
        with pytest.raises(ValueError, match="YYYYMM"):
            await mock_client.get_measurements(basho_id="bad")

    @pytest.mark.asyncio
    async def test_get_measurements_invalid_rikishi_id(self, mock_client):
        with pytest.raises(ValueError, match="positive"):
            await mock_client.get_measurements(rikishi_id=0)

    @pytest.mark.asyncio
    async def test_get_ranks_no_params(self, mock_client):
        with pytest.raises(ValueError, match="must be provided"):
            await mock_client.get_ranks()

    @pytest.mark.asyncio
    async def test_get_shikonas_no_params(self, mock_client):
        with pytest.raises(ValueError, match="must be provided"):
            await mock_client.get_shikonas()


class TestSumoClientHTTP:
    """Tests that mock the HTTP layer."""

    @pytest.mark.asyncio
    async def test_get_rikishi(self, sample_rikishi_data):
        client = SumoClient(base_url="https://test.example.com")
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = sample_rikishi_data
        mock_http.request.return_value = mock_response
        client._client = mock_http

        result = await client.get_rikishi("1")
        assert result.id == 1
        assert result.shikona_en == "Test Rikishi"
        mock_http.request.assert_called_once_with("GET", "/rikishi/1", params=None)

    @pytest.mark.asyncio
    async def test_404_with_error_message(self):
        client = SumoClient(base_url="https://test.example.com")
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 404
        mock_response.json.return_value = {"error": "Resource not found"}
        mock_http.request.return_value = mock_response
        client._client = mock_http

        with pytest.raises(ValueError, match="Resource not found"):
            await client.get_rikishi("999")

    @pytest.mark.asyncio
    async def test_invalid_json_response(self):
        client = SumoClient(base_url="https://test.example.com")
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.side_effect = Exception("bad json")
        mock_http.request.return_value = mock_response
        client._client = mock_http

        with pytest.raises(RuntimeError, match="Invalid JSON"):
            await client.get_rikishi("1")


class TestSumoSyncClient:
    def test_not_context_manager(self):
        client = SumoSyncClient()
        with pytest.raises(RuntimeError, match="context manager"):
            client.get_rikishi("1")

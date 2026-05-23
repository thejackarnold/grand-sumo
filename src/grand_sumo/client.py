import json
import anyio
import inspect
import functools
import types
import sys
from datetime import datetime
from typing import Any, Dict, Optional

import httpx

from grand_sumo.models import (
    Banzuke,
    Basho,
    KimariteMatchesResponse,
    KimariteResponse,
    Match,
    Measurement,
    MeasurementsResponse,
    Rank,
    RanksResponse,
    Rikishi,
    RikishiList,
    RikishiMatchesResponse,
    RikishiOpponentMatchesResponse,
    RikishiStats,
    Shikona,
    ShikonasResponse,
    Torikumi,
)


class SumoClient:
    """Client for interacting with the Sumo API."""

    def __init__(
        self,
        base_url: str = "https://sumo-api.com",
        verify_ssl: bool = True,
        connect_timeout: float = 5.0,
        read_timeout: float = 5.0,
        enable_http2: bool = True,
        max_retries: int = 2,
        retry_backoff_factor: float = 1.0,
    ):
        """Initialize the client with the base URL and HTTP configuration.

        Args:
            base_url: Base URL for the Sumo API
            verify_ssl: Whether to verify SSL certificates
            connect_timeout: Connection timeout in seconds
            read_timeout: Read timeout in seconds
            enable_http2: Whether to enable HTTP/2 support
            max_retries: Maximum number of retry attempts
            retry_backoff_factor: Factor for exponential backoff (delay = factor * (2 ** attempt))
        """
        self.base_url = base_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None
        self.verify_ssl = verify_ssl
        self.connect_timeout = connect_timeout
        self.read_timeout = read_timeout
        self.enable_http2 = enable_http2
        self.max_retries = max_retries
        self.retry_backoff_factor = retry_backoff_factor

    async def __aenter__(self) -> "SumoClient":
        """Create an async context manager."""
        import ssl

        # Configure SSL verification
        if self.verify_ssl:
            try:
                import certifi

                ssl_context = ssl.create_default_context(cafile=certifi.where())
            except (ImportError, FileNotFoundError):
                raise RuntimeError(
                    "certifi not available; set verify_ssl=False to proceed"
                )
        else:
            ssl_context = False

        # Configure timeout
        timeout = httpx.Timeout(
            connect=self.connect_timeout,
            read=self.read_timeout,
            write=self.read_timeout,  # Use read timeout for writes as well
            pool=self.connect_timeout,  # Use connect timeout for pool
        )

        # Configure retry transport
        from httpx import AsyncHTTPTransport

        transport = AsyncHTTPTransport(
            retries=self.max_retries,
        )

        self._client = httpx.AsyncClient(
            base_url=f"{self.base_url}/api",
            verify=ssl_context,
            timeout=timeout,
            http2=self.enable_http2,
            transport=transport,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Clean up the async client."""
        if self._client:
            await self._client.aclose()

    async def _make_request(
        self, method: str, path: str, params: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Make a request to the Sumo API.

        Args:
            method: HTTP method to use
            path: API endpoint path
            params: Optional query parameters

        Returns:
            JSON response data

        Raises:
            httpx.HTTPStatusError: If the API returns an error status code
            ValueError: If the API returns a 404 with a specific error message
            RuntimeError: If the response contains invalid JSON
        """
        if not self._client:
            raise RuntimeError("Client must be used as an async context manager")

        response = await self._client.request(method, path, params=params)

        # Handle 404 errors with specific error messages
        if response.status_code == 404:
            try:
                data = response.json()
                if "error" in data:
                    raise ValueError(f"API Error: {data['error']}")
            except (KeyError, TypeError, json.JSONDecodeError):
                # If JSON decode fails or doesn't have error key, fall through to raise_for_status
                pass

        response.raise_for_status()

        try:
            return response.json()
        except Exception as e:
            raise RuntimeError(f"Invalid JSON from API: {e}") from e

    async def get_rikishi(self, rikishi_id: str) -> Rikishi:
        """Get a single rikishi by ID."""
        data = await self._make_request("GET", f"/rikishi/{rikishi_id}")
        return Rikishi.model_validate(data)

    async def get_rikishi_stats(self, rikishi_id: str) -> RikishiStats:
        """Get statistics for a rikishi."""
        data = await self._make_request("GET", f"/rikishi/{rikishi_id}/stats")
        return RikishiStats.model_validate(data)

    async def get_rikishis(
        self,
        shikona_en: Optional[str] = None,
        heya: Optional[str] = None,
        sumodb_id: Optional[int] = None,
        nsk_id: Optional[int] = None,
        intai: Optional[bool] = None,
        measurements: bool = True,
        ranks: bool = True,
        shikonas: bool = True,
        limit: int = 10,
        skip: int = 0,
    ) -> RikishiList:
        """Get a list of rikishi with optional filters."""
        params = {
            "limit": limit,
            "skip": skip,
            "measurements": str(measurements).lower(),
            "ranks": str(ranks).lower(),
            "shikonas": str(shikonas).lower(),
        }

        if shikona_en:
            params["shikonaEn"] = shikona_en
        if heya:
            params["heya"] = heya
        if sumodb_id:
            params["sumodbId"] = sumodb_id
        if nsk_id:
            params["nskId"] = nsk_id
        if intai is not None:
            params["intai"] = str(intai).lower()

        data = await self._make_request("GET", "/rikishis", params=params)
        return RikishiList.model_validate(data)

    async def get_rikishi_matches(
        self, rikishi_id: int, basho_id: Optional[str] = None
    ) -> RikishiMatchesResponse:
        """
        Get all matches for a specific rikishi.

        Args:
            rikishi_id: The ID of the rikishi
            basho_id: Optional basho ID in YYYYMM format to filter matches

        Returns:
            RikishiMatchesResponse containing the matches

        Raises:
            ValueError: If rikishi_id is invalid or basho_id format is incorrect
        """
        if rikishi_id <= 0:
            raise ValueError("Rikishi ID must be positive")

        if basho_id and not (basho_id.isdigit() and len(basho_id) == 6):
            raise ValueError("Basho ID must be in YYYYMM format")

        params = {}
        if basho_id:
            params["bashoId"] = basho_id

        data = await self._make_request(
            "GET", f"/rikishi/{rikishi_id}/matches", params=params
        )
        return RikishiMatchesResponse.model_validate(data)

    async def get_rikishi_opponent_matches(
        self, rikishi_id: int, opponent_id: int, basho_id: Optional[str] = None
    ) -> RikishiOpponentMatchesResponse:
        """
        Get all matches between two specific rikishi.

        Args:
            rikishi_id: The ID of the first rikishi
            opponent_id: The ID of the second rikishi
            basho_id: Optional basho ID in YYYYMM format to filter matches

        Returns:
            RikishiOpponentMatchesResponse containing the matches between the two rikishi

        Raises:
            ValueError: If rikishi_id or opponent_id is invalid, or basho_id format is incorrect
        """
        if rikishi_id <= 0:
            raise ValueError("Rikishi ID must be positive")

        if opponent_id <= 0:
            raise ValueError("Opponent ID must be positive")

        if basho_id and not (basho_id.isdigit() and len(basho_id) == 6):
            raise ValueError("Basho ID must be in YYYYMM format")

        params = {}
        if basho_id:
            params["bashoId"] = basho_id

        data = await self._make_request(
            "GET", f"/rikishi/{rikishi_id}/matches/{opponent_id}", params=params
        )
        return RikishiOpponentMatchesResponse.model_validate(data)

    async def get_basho(self, basho_id: str) -> Basho:
        """
        Get details for a specific basho tournament.

        Args:
            basho_id: The basho ID in YYYYMM format (e.g., 202305)

        Returns:
            Basho object containing tournament details, winners, and special prizes

        Raises:
            ValueError: If basho_id format is incorrect or date is in the future
        """
        if not (basho_id.isdigit() and len(basho_id) == 6):
            raise ValueError("Basho ID must be in YYYYMM format")

        # Check if date is in the future
        year = int(basho_id[:4])
        month = int(basho_id[4:])
        basho_date = datetime(year, month, 1)
        if basho_date > datetime.now():
            raise ValueError("Cannot get details for future basho")

        data = await self._make_request("GET", f"/basho/{basho_id}")
        return Basho.model_validate(data)

    async def get_banzuke(self, basho_id: str, division: str) -> Banzuke:
        """Get banzuke details for a specific basho and division.

        Args:
            basho_id: Basho ID in YYYYMM format
            division: Division name (Makuuchi, Juryo, Makushita, Sandanme, Jonidan, Jonokuchi)

        Returns:
            Banzuke object containing the banzuke details

        Raises:
            ValueError: If basho_id is invalid or in the future, or if division is invalid
        """
        # Validate basho_id format
        try:
            year = int(basho_id[:4])
            month = int(basho_id[4:])
            basho_date = datetime(year, month, 1)
        except (ValueError, IndexError):
            raise ValueError("Basho ID must be in YYYYMM format")

        # Check if basho is in the future
        if basho_date > datetime.now():
            raise ValueError("Cannot fetch future basho")

        # Validate division
        valid_divisions = [
            "Makuuchi",
            "Juryo",
            "Makushita",
            "Sandanme",
            "Jonidan",
            "Jonokuchi",
        ]
        if division not in valid_divisions:
            raise ValueError("Invalid division")

        data = await self._make_request("GET", f"/basho/{basho_id}/banzuke/{division}")

        # Process east and west sides
        for side in ["east", "west"]:
            if side in data:
                for rikishi in data[side]:
                    # Add side to each rikishi
                    rikishi["side"] = side.title()
                    # Convert record to Match objects
                    if "record" in rikishi:
                        # Add basho_id to each match record
                        for match in rikishi["record"]:
                            match["bashoId"] = basho_id
                        rikishi["record"] = [
                            Match.from_banzuke(match) for match in rikishi["record"]
                        ]

        # Ensure bashoId is set
        data["bashoId"] = basho_id

        return Banzuke.model_validate(data)

    async def get_torikumi(self, basho_id: str, division: str, day: int) -> Torikumi:
        """Get torikumi details for a specific basho, division, and day.

        Args:
            basho_id: Basho ID in YYYYMM format
            division: Division name (Makuuchi, Juryo, Makushita, Sandanme, Jonidan, Jonokuchi)
            day: Day of the tournament (1-15)

        Returns:
            Torikumi object containing the matches for the specified day

        Raises:
            ValueError: If basho_id is invalid or in the future, division is invalid, or day is out of range
        """
        # Validate basho_id format
        try:
            year = int(basho_id[:4])
            month = int(basho_id[4:])
            basho_date = datetime(year, month, 1)
        except (ValueError, IndexError):
            raise ValueError("Basho ID must be in YYYYMM format")

        # Check if basho is in the future
        if basho_date > datetime.now():
            raise ValueError("Cannot fetch future basho")

        # Validate division
        valid_divisions = [
            "Makuuchi",
            "Juryo",
            "Makushita",
            "Sandanme",
            "Jonidan",
            "Jonokuchi",
        ]
        if division not in valid_divisions:
            raise ValueError("Invalid division")

        # Validate day
        if not 1 <= day <= 20:
            raise ValueError("Day must be between 1 and 20")

        data = await self._make_request(
            "GET", f"/basho/{basho_id}/torikumi/{division}/{day}"
        )

        # Convert matches to use the unified Match model
        if "torikumi" in data:
            data["torikumi"] = [
                Match.from_torikumi({**match, "division": division, "bashoId": basho_id, "day": day})
                for match in data["torikumi"]
            ]

        # Handle both 'bashoId' and 'date' fields in the response
        if "bashoId" not in data and "date" in data:
            data["bashoId"] = data["date"]

        # Add division and day fields
        data["division"] = division
        data["day"] = day

        # Convert rikishiId to string in specialPrizes
        if "specialPrizes" in data:
            for prize in data["specialPrizes"]:
                if "rikishiId" in prize:
                    prize["rikishiId"] = str(prize["rikishiId"])

        return Torikumi.model_validate(data)

    async def get_kimarite(
        self,
        sort_field: Optional[str] = None,
        sort_order: Optional[str] = "asc",
        limit: Optional[int] = None,
        skip: Optional[int] = 0,
    ) -> KimariteResponse:
        """Get statistics on kimarite usage.

        Args:
            sort_field: Field to sort by (count, kimarite, lastUsage)
            sort_order: Sort order (asc or desc)
            limit: Number of records to return
            skip: Number of records to skip

        Returns:
            KimariteResponse object containing kimarite statistics

        Raises:
            ValueError: If any of the parameters are invalid
        """
        # Validate parameters
        if sort_field and sort_field not in ["count", "kimarite", "lastUsage"]:
            raise ValueError(
                "Invalid sort field. Must be one of: count, kimarite, lastUsage"
            )

        if sort_order and sort_order not in ["asc", "desc"]:
            raise ValueError("Sort order must be either 'asc' or 'desc'")

        if limit is not None and limit <= 0:
            raise ValueError("Limit must be a positive integer")

        if skip < 0:
            raise ValueError("Skip must be a non-negative integer")

        # Build query parameters
        params: Dict[str, Any] = {}
        if sort_field:
            params["sortField"] = sort_field
        if sort_order:
            params["sortOrder"] = sort_order
        if limit is not None:
            params["limit"] = limit
        if skip:
            params["skip"] = skip

        data = await self._make_request("GET", "/kimarite", params=params)
        return KimariteResponse(**data)

    async def get_kimarite_matches(
        self,
        kimarite: str,
        sort_order: Optional[str] = "asc",
        limit: Optional[int] = None,
        skip: Optional[int] = 0,
    ) -> KimariteMatchesResponse:
        """Get matches where a specific kimarite was used.

        Args:
            kimarite: Name of the kimarite to search for
            sort_order: Sort order (asc or desc)
            limit: Number of records to return (max 1000)
            skip: Number of records to skip

        Returns:
            KimariteMatchesResponse object containing matches

        Raises:
            ValueError: If any of the parameters are invalid
        """
        # Validate parameters
        if not kimarite:
            raise ValueError("Kimarite cannot be empty")

        if sort_order and sort_order not in ["asc", "desc"]:
            raise ValueError("Sort order must be either 'asc' or 'desc'")

        if limit is not None:
            if limit <= 0:
                raise ValueError("Limit must be a positive integer")
            if limit > 1000:
                raise ValueError("Limit cannot exceed 1000")

        if skip < 0:
            raise ValueError("Skip must be a non-negative integer")

        # Build query parameters
        params: Dict[str, Any] = {}
        if sort_order:
            params["sortOrder"] = sort_order
        if limit is not None:
            params["limit"] = limit
        if skip:
            params["skip"] = skip

        data = await self._make_request("GET", f"/kimarite/{kimarite}", params=params)
        return KimariteMatchesResponse(**data)

    async def get_measurements(
        self,
        basho_id: Optional[str] = None,
        rikishi_id: Optional[int] = None,
        sort_order: Optional[str] = "desc",
    ) -> MeasurementsResponse:
        """Get measurement changes by rikishi or basho.

        Args:
            basho_id: Optional basho ID in YYYYMM format to filter measurements
            rikishi_id: Optional rikishi ID to filter measurements
            sort_order: Sort order for basho_id (asc or desc, default: desc)

        Returns:
            List[Measurement] containing measurement records

        Raises:
            ValueError: If parameters are invalid or neither basho_id nor rikishi_id is provided
        """
        # Validate parameters
        if not basho_id and not rikishi_id:
            raise ValueError("Either basho_id or rikishi_id must be provided")

        if basho_id and not (basho_id.isdigit() and len(basho_id) == 6):
            raise ValueError("Basho ID must be in YYYYMM format")

        if rikishi_id is not None and rikishi_id <= 0:
            raise ValueError("Rikishi ID must be positive")

        if sort_order and sort_order not in ["asc", "desc"]:
            raise ValueError("Sort order must be either 'asc' or 'desc'")

        # Build query parameters
        params: Dict[str, Any] = {}
        if basho_id:
            params["bashoId"] = basho_id
        if rikishi_id:
            params["rikishiId"] = rikishi_id

        data = await self._make_request("GET", "/measurements", params=params)
        # Convert each item in the list to a Measurement model
        measurements = [Measurement.model_validate(item) for item in data]

        # Sort by basho_id if requested
        if sort_order:
            measurements.sort(key=lambda m: m.basho_id, reverse=(sort_order == "desc"))

        return measurements

    async def get_ranks(
        self,
        basho_id: Optional[str] = None,
        rikishi_id: Optional[int] = None,
        sort_order: Optional[str] = "desc",
    ) -> RanksResponse:
        """Get rank changes by rikishi or basho.

        Args:
            basho_id: Optional basho ID in YYYYMM format to filter ranks
            rikishi_id: Optional rikishi ID to filter ranks
            sort_order: Sort order for basho_id (asc or desc, default: desc)

        Returns:
            List[Rank] containing rank records

        Raises:
            ValueError: If parameters are invalid or neither basho_id nor rikishi_id is provided
        """
        # Validate parameters
        if not basho_id and not rikishi_id:
            raise ValueError("Either basho_id or rikishi_id must be provided")

        if basho_id and not (basho_id.isdigit() and len(basho_id) == 6):
            raise ValueError("Basho ID must be in YYYYMM format")

        if rikishi_id is not None and rikishi_id <= 0:
            raise ValueError("Rikishi ID must be positive")

        if sort_order and sort_order not in ["asc", "desc"]:
            raise ValueError("Sort order must be either 'asc' or 'desc'")

        # Build query parameters
        params: Dict[str, Any] = {}
        if basho_id:
            params["bashoId"] = basho_id
        if rikishi_id:
            params["rikishiId"] = rikishi_id

        data = await self._make_request("GET", "/ranks", params=params)
        # Convert each item in the list to a Rank model
        ranks = [Rank.model_validate(item) for item in data]

        # Sort by basho_id if requested
        if sort_order:
            ranks.sort(key=lambda r: r.basho_id, reverse=(sort_order == "desc"))

        return ranks

    async def get_shikonas(
        self,
        basho_id: Optional[str] = None,
        rikishi_id: Optional[int] = None,
        sort_order: Optional[str] = "desc",
    ) -> ShikonasResponse:
        """Get shikona changes by rikishi or basho.

        Args:
            basho_id: Optional basho ID in YYYYMM format to filter shikonas
            rikishi_id: Optional rikishi ID to filter shikonas
            sort_order: Sort order for basho_id (asc or desc, default: desc)

        Returns:
            List[Shikona] containing shikona records

        Raises:
            ValueError: If parameters are invalid or neither basho_id nor rikishi_id is provided
        """
        # Validate parameters
        if not basho_id and not rikishi_id:
            raise ValueError("Either basho_id or rikishi_id must be provided")

        if basho_id and not (basho_id.isdigit() and len(basho_id) == 6):
            raise ValueError("Basho ID must be in YYYYMM format")

        if rikishi_id is not None and rikishi_id <= 0:
            raise ValueError("Rikishi ID must be positive")

        if sort_order and sort_order not in ["asc", "desc"]:
            raise ValueError("Sort order must be either 'asc' or 'desc'")

        # Build query parameters
        params: Dict[str, Any] = {}
        if basho_id:
            params["bashoId"] = basho_id
        if rikishi_id:
            params["rikishiId"] = rikishi_id

        data = await self._make_request("GET", "/shikonas", params=params)
        # Convert each item in the list to a Shikona model
        shikonas = [Shikona.model_validate(item) for item in data]

        # Sort by basho_id if requested
        if sort_order:
            shikonas.sort(key=lambda s: s.basho_id, reverse=(sort_order == "desc"))

        return shikonas


class SumoSyncClient:
    """Synchronous client for interacting with the Sumo API."""

    def __init__(self, *args, **kwargs):
        """Initialize the synchronous client.

        Args:
            *args: Positional arguments to pass to SumoClient
            **kwargs: Keyword arguments to pass to SumoClient
        """
        self._async_client = SumoClient(*args, **kwargs)
        self._portal_cm = None  # Initialize to None; portal will be created in __enter__
        self._portal = None

        for attr_name, async_method in inspect.getmembers(SumoClient, inspect.iscoroutinefunction):
            def sync_method_factory(method_name, orig_method):
                @functools.wraps(orig_method)
                def sync_wrapper(self_sync, *args, **kwargs):
                    if not self_sync._portal:
                        raise RuntimeError(
                            "SumoSyncClient must be used as a context manager. "
                            "Call __enter__ before making API calls."
                        )
                    # Get the bound method from the async client instance
                    bound_method = getattr(self_sync._async_client, method_name)
                    # Wrap the call with functools.partial to handle kwargs correctly,
                    # as portal.call itself only accepts *args.
                    partial_func = functools.partial(bound_method, *args, **kwargs)
                    return self_sync._portal.call(partial_func)
                return sync_wrapper

            sync_method = sync_method_factory(attr_name, async_method)
            setattr(self, attr_name, types.MethodType(sync_method, self))

    def __enter__(self):
        """Enter the runtime context."""
        if self._portal_cm is None:  # Should not happen if __init__ is correct
            self._portal_cm = anyio.from_thread.start_blocking_portal()
        self._portal = self._portal_cm.__enter__()
        try:
            self._portal.call(self._async_client.__aenter__)
        except Exception:
            # If __aenter__ fails, make sure to exit the portal_cm as well
            self._portal_cm.__exit__(*sys.exc_info())
            self._portal = None  # Reset portal as it's not properly entered
            self._portal_cm = None  # Reset portal_cm as it's exited
            raise
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the runtime context."""
        if self._portal:  # Check if portal was successfully obtained in __enter__
            try:
                self._portal.call(self._async_client.__aexit__, exc_type, exc_val, exc_tb)
            finally:  # Ensure portal_cm.__exit__ is called even if the above line fails
                if self._portal_cm:
                    self._portal_cm.__exit__(exc_type, exc_val, exc_tb)
                self._portal = None
                self._portal_cm = None

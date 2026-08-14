"""Isolated client for the brapi.dev market data API.

All HTTP communication with brapi lives here. Nothing outside this module
should know the base URL, auth scheme, or response shapes of the external API.
"""

import logging
from typing import Any

import httpx

from app.core.config import get_settings
from app.services.market_data.exceptions import (
    BrapiAuthenticationError,
    BrapiInvalidResponseError,
    BrapiNotConfiguredError,
    BrapiPermissionError,
    BrapiRequestError,
    BrapiTimeoutError,
)

logger = logging.getLogger("argos.market_data.brapi")


class BrapiProvider:
    def __init__(self, client: httpx.Client | None = None):
        settings = get_settings()
        self._token = settings.brapi_api_token
        self._base_url = settings.brapi_base_url
        self._timeout = settings.brapi_timeout_seconds
        self._client = client
        self._owns_client = client is None

    def __enter__(self) -> "BrapiProvider":
        if self._client is None:
            self._client = httpx.Client(base_url=self._base_url, timeout=self._timeout)
        return self

    def __exit__(self, *_exc_info) -> None:
        if self._owns_client and self._client is not None:
            self._client.close()

    def get_futures_term_structure(self, asset: str) -> dict[str, Any]:
        payload = self._get("/api/v2/futures/term-structure", params={"asset": asset})
        self._require_keys(payload, ["contracts"], context=f"futures/term-structure asset={asset}")
        return payload

    def get_futures_historical(
        self,
        symbol: str,
        start_date: str | None = None,
        end_date: str | None = None,
        sort_order: str = "asc",
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"symbol": symbol, "sortOrder": sort_order}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        payload = self._get("/api/v2/futures/historical", params=params)
        self._require_keys(payload, ["future"], context=f"futures/historical symbol={symbol}")
        return payload

    def get_macro(
        self,
        symbols: list[str],
        start_date: str | None = None,
        end_date: str | None = None,
        sort_order: str = "desc",
        limit: int | None = None,
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"symbols": ",".join(symbols), "sortOrder": sort_order}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        if limit is not None:
            params["limit"] = limit
        payload = self._get("/api/v2/macro", params=params)
        self._require_keys(payload, ["results"], context=f"macro symbols={symbols}")
        return payload

    def get_macro_latest(self, symbols: list[str] | None = None) -> dict[str, Any]:
        params: dict[str, Any] = {}
        if symbols:
            params["symbols"] = ",".join(symbols)
        payload = self._get("/api/v2/macro/latest", params=params)
        self._require_keys(payload, ["results"], context="macro/latest")
        return payload

    def get_macro_available(self) -> dict[str, Any]:
        payload = self._get("/api/v2/macro/available")
        self._require_keys(payload, ["results"], context="macro/available")
        return payload

    def get_treasury_list(self, indexer: str | None = None, limit: int | None = None) -> dict[str, Any]:
        """Catalog of Tesouro Direto bonds - each entry already includes the current
        snapshot (buyRate/sellRate/buyPrice/sellPrice/basePrice). Paginated by brapi
        (default page size 20) - pass an explicit `limit` to avoid missing bonds past
        page 1, the same trap already found on GET /api/v2/macro.
        """
        params: dict[str, Any] = {}
        if indexer:
            params["indexer"] = indexer
        if limit is not None:
            params["limit"] = limit
        payload = self._get("/api/v2/treasury/list", params=params)
        self._require_keys(payload, ["results"], context="treasury/list")
        return payload

    def get_treasury_indicators(self, symbols: list[str]) -> dict[str, Any]:
        """Snapshot for up to ~20 explicit bond symbols."""
        payload = self._get("/api/v2/treasury/indicators", params={"symbols": ",".join(symbols)})
        self._require_keys(payload, ["results"], context=f"treasury/indicators symbols={symbols}")
        return payload

    def get_treasury_indicators_history(
        self,
        symbols: list[str],
        start_date: str | None = None,
        end_date: str | None = None,
        sort_order: str = "asc",
    ) -> dict[str, Any]:
        params: dict[str, Any] = {"symbols": ",".join(symbols), "sortOrder": sort_order}
        if start_date:
            params["startDate"] = start_date
        if end_date:
            params["endDate"] = end_date
        payload = self._get("/api/v2/treasury/indicators/history", params=params)
        self._require_keys(payload, ["results"], context=f"treasury/indicators/history symbols={symbols}")
        return payload

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._token:
            raise BrapiNotConfiguredError("BRAPI_API_TOKEN is not configured")

        client = self._client or httpx.Client(base_url=self._base_url, timeout=self._timeout)
        close_after = self._client is None
        try:
            response = client.get(
                path,
                params=params,
                headers={"Authorization": f"Bearer {self._token}"},
            )
        except httpx.TimeoutException as exc:
            logger.error("brapi request timed out: %s", path)
            raise BrapiTimeoutError(f"Request to {path} timed out") from exc
        except httpx.RequestError as exc:
            logger.error("brapi request failed: %s (%s)", path, exc)
            raise BrapiRequestError(f"Request to {path} failed: {exc}") from exc
        finally:
            if close_after:
                client.close()

        if response.status_code == 401:
            raise BrapiAuthenticationError(self._extract_message(response, default="Invalid brapi token"))
        if response.status_code == 403:
            raise BrapiPermissionError(self._extract_message(response, default="brapi token lacks access"))
        if not response.is_success:
            raise BrapiRequestError(
                self._extract_message(response, default=f"brapi returned HTTP {response.status_code}")
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise BrapiInvalidResponseError(f"Response from {path} was not valid JSON") from exc

        if not isinstance(payload, dict):
            raise BrapiInvalidResponseError(f"Response from {path} was not a JSON object")

        return payload

    @staticmethod
    def _extract_message(response: httpx.Response, default: str) -> str:
        try:
            body = response.json()
            if isinstance(body, dict) and "message" in body:
                return str(body["message"])
        except ValueError:
            pass
        return default

    @staticmethod
    def _require_keys(payload: dict[str, Any], keys: list[str], context: str) -> None:
        missing = [key for key in keys if key not in payload]
        if missing:
            raise BrapiInvalidResponseError(
                f"Incomplete payload from {context}: missing key(s) {missing}"
            )

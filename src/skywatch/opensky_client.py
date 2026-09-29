"""OpenSky Network REST client.

OpenSky removed username/password auth on 2026-03-18. This client uses the
OAuth2 client-credentials flow against the OpenSky Keycloak realm. Tokens
expire in ~30 minutes and are refreshed automatically.

Credit costs for /states/all follow OpenSky's published formula:
  - 1 credit  : bounding box < 25 sq. deg
  - 2 credits : bounding box < 100 sq. deg
  - 3 credits : bounding box < 400 sq. deg
  - 4 credits : anything larger (or /states/all with no bbox)
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import httpx

logger = logging.getLogger("skywatch.opensky")

TOKEN_URL = (
    "https://auth.opensky-network.org/auth/realms/opensky-network"
    "/protocol/openid-connect/token"
)
API_BASE = "https://opensky-network.org/api"

# Columns in each state-vector array, per OpenSky REST API docs.
STATE_FIELDS = [
    "icao24", "callsign", "origin_country", "time_position", "last_contact",
    "longitude", "latitude", "baro_altitude", "on_ground", "velocity",
    "true_track", "vertical_rate", "sensors", "geo_altitude", "squawk", "spi",
    "position_source", "category",
]


class OpenSkyError(RuntimeError):
    """Raised when OpenSky returns an unexpected response."""


class RateLimited(OpenSkyError):
    """Raised on HTTP 429. `retry_after` is seconds to wait."""

    def __init__(self, retry_after: int) -> None:
        super().__init__(f"OpenSky rate limit hit; retry after {retry_after}s")
        self.retry_after = retry_after


@dataclass
class _Token:
    access_token: str
    expires_at: float  # unix epoch seconds

    @property
    def is_valid(self) -> bool:
        # 60s safety margin so we don't send a token that expires mid-request.
        return time.time() < self.expires_at - 60


class OpenSkyClient:
    """Thin async wrapper around the OpenSky REST API."""

    def __init__(
        self,
        credentials_path: str | Path | None = None,
        client_id: str | None = None,
        client_secret: str | None = None,
        timeout: float = 15.0,
    ) -> None:
        if client_id and client_secret:
            self._client_id = client_id
            self._client_secret = client_secret
        elif credentials_path:
            data = json.loads(Path(credentials_path).read_text())
            self._client_id = data["clientId"]
            self._client_secret = data["clientSecret"]
        else:
            self._client_id = None
            self._client_secret = None

        self._token: _Token | None = None
        self._http = httpx.AsyncClient(timeout=timeout)

    @property
    def is_authenticated(self) -> bool:
        return bool(self._client_id and self._client_secret)

    async def aclose(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> "OpenSkyClient":
        return self

    async def __aexit__(self, *_exc: object) -> None:
        await self.aclose()

    async def _get_token(self) -> str | None:
        if not self.is_authenticated:
            return None
        if self._token and self._token.is_valid:
            return self._token.access_token

        resp = await self._http.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self._client_id,
                "client_secret": self._client_secret,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        if resp.status_code != 200:
            raise OpenSkyError(
                f"Token request failed ({resp.status_code}): {resp.text[:200]}"
            )
        payload = resp.json()
        self._token = _Token(
            access_token=payload["access_token"],
            expires_at=time.time() + int(payload.get("expires_in", 1800)),
        )
        logger.info("Obtained new OpenSky access token")
        return self._token.access_token

    async def _get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        token = await self._get_token()
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        resp = await self._http.get(f"{API_BASE}{path}", params=params, headers=headers)

        if resp.status_code == 429:
            retry = int(resp.headers.get("X-Rate-Limit-Retry-After-Seconds", "60"))
            raise RateLimited(retry)
        if resp.status_code == 404:
            return None
        if resp.status_code >= 400:
            raise OpenSkyError(
                f"OpenSky {path} returned {resp.status_code}: {resp.text[:200]}"
            )

        remaining = resp.headers.get("X-Rate-Limit-Remaining")
        if remaining is not None:
            logger.info("OpenSky credits remaining: %s", remaining)

        if not resp.content:
            return None
        return resp.json()

    async def get_states(
        self,
        lamin: float | None = None,
        lomin: float | None = None,
        lamax: float | None = None,
        lomax: float | None = None,
    ) -> list[dict[str, Any]]:
        """Return current state vectors, optionally within a bounding box.

        Each result is normalized into a dict keyed by STATE_FIELDS.
        """
        params: dict[str, Any] = {}
        if None not in (lamin, lomin, lamax, lomax):
            params.update(lamin=lamin, lomin=lomin, lamax=lamax, lomax=lomax)

        data = await self._get("/states/all", params or None)
        if not data or not data.get("states"):
            return []

        results: list[dict[str, Any]] = []
        for row in data["states"]:
            record: dict[str, Any] = {}
            for i, key in enumerate(STATE_FIELDS):
                record[key] = row[i] if i < len(row) else None
            if isinstance(record.get("callsign"), str):
                record["callsign"] = record["callsign"].strip() or None
            results.append(record)
        return results

    async def get_flights_by_aircraft(
        self, icao24: str, begin: int, end: int
    ) -> list[dict[str, Any]]:
        """Flights for a specific aircraft in [begin, end] (unix seconds).

        Requires authentication. `end - begin` must be <= 30 days.
        """
        data = await self._get(
            "/flights/aircraft",
            {"icao24": icao24.lower(), "begin": begin, "end": end},
        )
        return data or []

    async def get_arrivals(
        self, airport_icao: str, begin: int, end: int
    ) -> list[dict[str, Any]]:
        """Flights arriving at `airport_icao` within [begin, end] (unix seconds).

        Requires authentication. Window <= 7 days.
        """
        data = await self._get(
            "/flights/arrival",
            {"airport": airport_icao.upper(), "begin": begin, "end": end},
        )
        return data or []

    async def get_departures(
        self, airport_icao: str, begin: int, end: int
    ) -> list[dict[str, Any]]:
        """Flights departing from `airport_icao` within [begin, end] (unix seconds).

        Requires authentication. Window <= 7 days.
        """
        data = await self._get(
            "/flights/departure",
            {"airport": airport_icao.upper(), "begin": begin, "end": end},
        )
        return data or []

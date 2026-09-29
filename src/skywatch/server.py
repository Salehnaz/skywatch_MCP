"""SkyWatch MCP server — exposes OpenSky flight data to Claude as MCP tools."""

from __future__ import annotations

import logging
import os
from collections import Counter
from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer

from . import aircraft_db, airlines, airports
from .cache import TTLCache
from .geo import bounding_box
from .opensky_client import OpenSkyClient, RateLimited

logging.basicConfig(
    level=os.getenv("SKYWATCH_LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("skywatch.server")

CREDENTIALS_PATH = Path(os.getenv("SKYWATCH_CREDENTIALS", "credentials.json"))
AIRCRAFT_DB_PATH = Path(os.getenv("SKYWATCH_AIRCRAFT_DB", "aircraft_db.sqlite"))

_client: OpenSkyClient | None = None
_cache = TTLCache(ttl=60.0)

mcp = MCPServer("skywatch")


def _get_client() -> OpenSkyClient:
    global _client
    if _client is None:
        if CREDENTIALS_PATH.exists():
            _client = OpenSkyClient(credentials_path=CREDENTIALS_PATH)
            logger.info("OpenSky client initialized with credentials from %s", CREDENTIALS_PATH)
        else:
            _client = OpenSkyClient()
            logger.warning(
                "No credentials.json found — running anonymously (400 credits/day, "
                "latest-only state vectors, no /flights/* endpoints)."
            )
    return _client


def _resolve_area(
    city: str | None,
    lat: float | None,
    lon: float | None,
    radius_km: float,
) -> tuple[float, float, float, float, str]:
    """Return a bounding box plus a human label for the area."""
    if city:
        apt = airports.find(city)
        if apt is None:
            raise ValueError(f"Unknown city or airport code: {city!r}")
        return (*bounding_box(apt.lat, apt.lon, radius_km), f"{apt.city} ({apt.iata})")
    if lat is None or lon is None:
        raise ValueError("Provide either `city` or both `lat` and `lon`.")
    return (*bounding_box(lat, lon, radius_km), f"{lat:.3f},{lon:.3f}")


async def _fetch_states(lamin: float, lomin: float, lamax: float, lomax: float) -> list[dict]:
    """Cached wrapper around OpenSky /states/all for a bounding box."""
    # Round to 2 decimals so trivially-different requests share a cache slot.
    key = ("states", round(lamin, 2), round(lomin, 2), round(lamax, 2), round(lomax, 2))
    client = _get_client()

    async def producer() -> list[dict]:
        return await client.get_states(lamin, lomin, lamax, lomax)

    return await _cache.get_or_set(key, producer)


def _summarize_flight(state: dict, meta: dict | None) -> dict:
    """Compact, privacy-safe summary for a single aircraft."""
    return {
        "callsign": state.get("callsign"),
        "icao24": state.get("icao24"),
        "origin_country": state.get("origin_country"),
        "latitude": state.get("latitude"),
        "longitude": state.get("longitude"),
        "altitude_m": state.get("baro_altitude"),
        "velocity_ms": state.get("velocity"),
        "heading_deg": state.get("true_track"),
        "vertical_rate_ms": state.get("vertical_rate"),
        "on_ground": state.get("on_ground"),
        "aircraft_type": (meta or {}).get("model"),
        "typecode": (meta or {}).get("typecode"),
        "manufacturer": (meta or {}).get("manufacturer"),
    }


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def get_flights_in_area(
    city: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float = 50.0,
    limit: int = 50,
) -> dict[str, Any]:
    """List aircraft currently within `radius_km` of a point.

    Provide either a `city` / airport code (e.g. "Dubai", "DXB") or `lat` + `lon`.
    Results include callsign, altitude, speed, heading, and aircraft model when
    available in the local aircraft database.
    """
    lamin, lomin, lamax, lomax, label = _resolve_area(city, lat, lon, radius_km)
    try:
        states = await _fetch_states(lamin, lomin, lamax, lomax)
    except RateLimited as e:
        return {"error": "rate_limited", "retry_after_seconds": e.retry_after, "area": label}

    icao24s = [s["icao24"] for s in states if s.get("icao24")]
    meta = aircraft_db.lookup_many(icao24s, AIRCRAFT_DB_PATH)

    flights = [
        _summarize_flight(s, meta.get(s.get("icao24") or ""))
        for s in states
    ]
    flights.sort(key=lambda f: (f["altitude_m"] or 0), reverse=True)
    return {
        "area": label,
        "bounding_box": {"lamin": lamin, "lomin": lomin, "lamax": lamax, "lomax": lomax},
        "count": len(flights),
        "flights": flights[:limit],
    }


@mcp.tool()
async def track_flight(callsign: str) -> dict[str, Any]:
    """Live position, altitude, speed, and heading for a specific flight.

    Accepts either the IATA form ("EK500") or the ICAO ADS-B form ("UAE500").
    Returns `None` for `state` when the flight is not currently airborne within
    OpenSky's coverage.
    """
    candidates = airlines.candidate_callsigns(callsign)
    client = _get_client()

    try:
        states = await _cache.get_or_set(
            ("states-global",),
            lambda: client.get_states(),
        )
    except RateLimited as e:
        return {"error": "rate_limited", "retry_after_seconds": e.retry_after}

    match = next(
        (s for s in states if (s.get("callsign") or "") in candidates),
        None,
    )
    if match is None:
        return {
            "callsign_query": callsign,
            "candidates_tried": candidates,
            "state": None,
            "note": "Not visible to OpenSky right now. Aircraft may be on the ground, out of receiver coverage, or the callsign is wrong.",
        }

    meta = aircraft_db.lookup(match["icao24"] or "", AIRCRAFT_DB_PATH)
    return {
        "callsign_query": callsign,
        "resolved_callsign": match.get("callsign"),
        "state": _summarize_flight(match, meta),
    }


@mcp.tool()
async def find_aircraft_type(
    typecode: str,
    city: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float = 200.0,
) -> dict[str, Any]:
    """Find aircraft of a specific ICAO typecode currently in an area.

    `typecode` is the ICAO type designator, e.g. "A388" (A380-800), "B77W"
    (777-300ER), "B748" (747-8). Requires the aircraft database to be imported;
    see the README.
    """
    lamin, lomin, lamax, lomax, label = _resolve_area(city, lat, lon, radius_km)
    try:
        states = await _fetch_states(lamin, lomin, lamax, lomax)
    except RateLimited as e:
        return {"error": "rate_limited", "retry_after_seconds": e.retry_after, "area": label}

    matching_icao24s = set(aircraft_db.find_by_type(typecode, AIRCRAFT_DB_PATH))
    if not matching_icao24s:
        return {
            "area": label,
            "typecode": typecode.upper(),
            "count": 0,
            "note": "No aircraft with that typecode in the local database. Have you imported aircraft_db.csv?",
            "flights": [],
        }

    hits = [s for s in states if (s.get("icao24") or "") in matching_icao24s]
    meta = aircraft_db.lookup_many([s["icao24"] for s in hits if s.get("icao24")], AIRCRAFT_DB_PATH)
    flights = [_summarize_flight(s, meta.get(s.get("icao24") or "")) for s in hits]
    return {
        "area": label,
        "typecode": typecode.upper(),
        "count": len(flights),
        "flights": flights,
    }


@mcp.tool()
async def get_business_jets_in_area(
    city: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    radius_km: float = 100.0,
) -> dict[str, Any]:
    """List business/private jets currently in an area.

    Privacy: this tool intentionally returns only aircraft *type* (e.g.
    "Gulfstream G650"). Owner / operator / registration are dropped at
    database import time and are not available to any tool — by design.
    """
    lamin, lomin, lamax, lomax, label = _resolve_area(city, lat, lon, radius_km)
    try:
        states = await _fetch_states(lamin, lomin, lamax, lomax)
    except RateLimited as e:
        return {"error": "rate_limited", "retry_after_seconds": e.retry_after, "area": label}

    icao24s = [s["icao24"] for s in states if s.get("icao24")]
    meta = aircraft_db.lookup_many(icao24s, AIRCRAFT_DB_PATH)

    jets: list[dict] = []
    for s in states:
        m = meta.get(s.get("icao24") or "")
        if aircraft_db.is_business_jet(m):
            jets.append(
                {
                    "typecode": (m or {}).get("typecode"),
                    "model": (m or {}).get("model"),
                    "manufacturer": (m or {}).get("manufacturer"),
                    "altitude_m": s.get("baro_altitude"),
                    "velocity_ms": s.get("velocity"),
                    "on_ground": s.get("on_ground"),
                    "latitude": s.get("latitude"),
                    "longitude": s.get("longitude"),
                }
            )
    return {
        "area": label,
        "count": len(jets),
        "jets": jets,
        "privacy_note": "Owner and registration details are intentionally not exposed.",
    }


@mcp.tool()
async def get_airport_activity(airport: str, hours: int = 2) -> dict[str, Any]:
    """Arrivals + departures for an airport over the past `hours` hours.

    Requires an authenticated OpenSky account (credentials.json). `airport`
    may be given as IATA (DXB) or ICAO (OMDB).
    """
    import time as _time

    apt = airports.find(airport)
    if apt is None:
        return {"error": f"Unknown airport: {airport!r}"}

    client = _get_client()
    if not client.is_authenticated:
        return {"error": "Airport activity requires OpenSky credentials (credentials.json)."}

    end = int(_time.time())
    begin = end - int(hours) * 3600

    try:
        arrivals = await _cache.get_or_set(
            ("arrivals", apt.icao, begin, end),
            lambda: client.get_arrivals(apt.icao, begin, end),
        )
        departures = await _cache.get_or_set(
            ("departures", apt.icao, begin, end),
            lambda: client.get_departures(apt.icao, begin, end),
        )
    except RateLimited as e:
        return {"error": "rate_limited", "retry_after_seconds": e.retry_after}

    def _airline(cs: str | None) -> str | None:
        cs = (cs or "").strip()
        return cs[:3] if len(cs) >= 3 else None

    hourly: Counter[int] = Counter()
    airline_counts: Counter[str] = Counter()
    for f in arrivals + departures:
        ts = f.get("firstSeen") or f.get("lastSeen")
        if ts:
            hourly[(ts % 86400) // 3600] += 1
        airline = _airline(f.get("callsign"))
        if airline:
            airline_counts[airline] += 1

    busiest_hour_utc = hourly.most_common(1)[0][0] if hourly else None
    return {
        "airport": f"{apt.name} ({apt.iata}/{apt.icao})",
        "window_hours": hours,
        "arrivals": len(arrivals),
        "departures": len(departures),
        "total": len(arrivals) + len(departures),
        "busiest_hour_utc": busiest_hour_utc,
        "top_airlines": airline_counts.most_common(5),
    }


@mcp.tool()
async def get_flight_history(
    callsign: str | None = None,
    icao24: str | None = None,
    hours: int = 24,
) -> dict[str, Any]:
    """Recent flights for a callsign or icao24 in the last `hours` hours.

    Requires an authenticated OpenSky account. Provide either `callsign` (e.g.
    "EK500" — will be translated to "UAE500") or `icao24`.
    """
    import time as _time

    client = _get_client()
    if not client.is_authenticated:
        return {"error": "Flight history requires OpenSky credentials (credentials.json)."}

    end = int(_time.time())
    begin = end - int(hours) * 3600

    if icao24:
        try:
            flights = await client.get_flights_by_aircraft(icao24, begin, end)
        except RateLimited as e:
            return {"error": "rate_limited", "retry_after_seconds": e.retry_after}
        return {"icao24": icao24.lower(), "hours": hours, "flights": flights}

    if not callsign:
        return {"error": "Provide either `callsign` or `icao24`."}

    # Callsign → icao24 requires either the live state (if currently flying)
    # or the local aircraft DB. Try the live state first.
    candidates = airlines.candidate_callsigns(callsign)
    try:
        states = await _cache.get_or_set(("states-global",), lambda: client.get_states())
    except RateLimited as e:
        return {"error": "rate_limited", "retry_after_seconds": e.retry_after}

    match = next((s for s in states if (s.get("callsign") or "") in candidates), None)
    if match is None or not match.get("icao24"):
        return {
            "callsign": callsign,
            "note": "Cannot resolve callsign → icao24 while the aircraft is not airborne. Pass `icao24` directly.",
            "flights": [],
        }

    try:
        flights = await client.get_flights_by_aircraft(match["icao24"], begin, end)
    except RateLimited as e:
        return {"error": "rate_limited", "retry_after_seconds": e.retry_after}
    return {
        "callsign": callsign,
        "resolved_icao24": match["icao24"],
        "hours": hours,
        "flights": flights,
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------


def main() -> None:
    """stdio entry point used by `skywatch-mcp` and Claude Desktop."""
    mcp.run()


if __name__ == "__main__":
    main()

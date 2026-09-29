# SkyWatch MCP

Live flight-tracking tools for Claude, powered by the [OpenSky Network](https://opensky-network.org/) REST API.

Ask Claude things like:

- *"What flights are over Dubai right now?"*
- *"Where is EK500?"*
- *"Any A380s near DXB?"*
- *"Which airline was busiest at DXB in the last 2 hours?"*
- *"Any business jets around Al Maktoum right now?"*

Claude answers using six MCP tools that call OpenSky under the hood, cache results, and enrich them with a local aircraft-model database.

## Tools

| Tool | What it answers |
| --- | --- |
| `get_flights_in_area` | Everything currently airborne near a city or lat/lon |
| `track_flight` | Live position of one callsign (accepts `EK500` or `UAE500`) |
| `find_aircraft_type` | Which aircraft of a given ICAO typecode (`A388`, `B77W`, …) are nearby |
| `get_business_jets_in_area` | Business/private jets nearby — **type only, never owners** |
| `get_airport_activity` | Arrivals + departures + busiest airline for an airport window *(auth required)* |
| `get_flight_history` | Recent flights for a callsign or `icao24` *(auth required)* |

## Setup

### 1. Install Python 3.11+ and [uv](https://docs.astral.sh/uv/)

```powershell
uv sync
```

### 2. Get OpenSky credentials

OpenSky removed username/password auth on **2026-03-18**. You now need an OAuth2 client:

1. Create a free account at <https://opensky-network.org/>.
2. Go to your account page → API Clients → **New Client**.
3. Download `credentials.json` and drop it in the project root.

Without credentials the server still works, but you get:

- 400 credits/day (vs 4,000)
- Latest state vectors only, 10 s resolution
- No `/flights/*` endpoints, so `get_airport_activity` and `get_flight_history` are disabled

### 3. Import the aircraft database (optional but recommended)

State vectors don't carry the actual aircraft model — just a broad category. OpenSky publishes monthly snapshots at `s3.opensky-network.org/data-samples/metadata/`. Download the latest and import it:

```powershell
# Replace 2025-08 with the newest month listed at s3.opensky-network.org/data-samples/?prefix=metadata/
Invoke-WebRequest `
  -Uri "https://s3.opensky-network.org/data-samples/metadata/aircraft-database-complete-2025-08.csv" `
  -OutFile "data\aircraft-database-complete-2025-08.csv"

uv run python -m skywatch.aircraft_db import data\aircraft-database-complete-2025-08.csv
```

The file is ~103 MB and imports around 616k aircraft in a few seconds.

**Privacy design decision:** the importer intentionally drops `owner`, `operator*`, and `registration` columns. Those fields never enter the local SQLite file, so no tool — current or future — can leak a private-jet owner. This is documented in `aircraft_db.py`.

### 4. Wire into Claude Desktop

Add to `%APPDATA%\Claude\claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "skywatch": {
      "command": "uv",
      "args": [
        "--directory",
        "C:\\Users\\user\\Desktop\\salehcode\\mypersonal\\MCP\\FlightMCP",
        "run",
        "skywatch-mcp"
      ]
    }
  }
}
```

Restart Claude Desktop. The tools appear in the tools list.

## Development

Run the stdio server directly:

```powershell
uv run skywatch-mcp
```

Or against the MCP Inspector for interactive testing (requires the MCP CLI):

```powershell
uv run mcp dev src/skywatch/server.py
```

Run tests:

```powershell
uv run pytest
```

## Design notes

- **Credit budget.** `/states/all` costs 1–4 credits depending on bounding-box area. Every tool that accepts a `radius_km` builds a small box (default 50–200 km, rarely > 1° × 1°) so calls stay in the cheapest tier. A 60-second in-process TTL cache coalesces repeated queries.
- **429 handling.** OpenSky returns `X-Rate-Limit-Retry-After-Seconds` on quota exhaustion. The client raises `RateLimited(retry_after=…)`; tools surface that to Claude instead of retrying blindly.
- **Callsign translation.** ADS-B callsigns use ICAO airline codes (`UAE500`), not IATA (`EK500`). `airlines.py` translates the common Gulf/South-Asian carriers so users can say either.
- **Privacy.** Owner/operator/registration are dropped at ingest — enforced at the data layer rather than filtered at query time.

## Project layout

```
src/skywatch/
├── server.py           # FastMCP tools
├── opensky_client.py   # OAuth2 + REST + 429 handling
├── cache.py            # 60-second TTL cache
├── aircraft_db.py      # CSV → SQLite (owner columns dropped)
├── airports.py         # IATA/ICAO → lat/lon
├── airlines.py         # IATA → ICAO callsign prefix
└── geo.py              # bounding boxes, haversine
```

## License

Personal / research use, matching OpenSky's non-commercial license. Not for commercial use without a separate OpenSky agreement.

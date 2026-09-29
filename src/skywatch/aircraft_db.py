"""Local SQLite mirror of OpenSky's aircraft-metadata CSV.

State vectors only give a broad category, not the actual aircraft model. Users
have to download OpenSky's aircraft-database CSV separately and import it via
`python -m skywatch.aircraft_db import <path.csv>`.

Privacy: owner / operator / operator_iata / operator_icao / operator_callsign
and registration are **dropped at import**. They never enter the local SQLite
file, so no future tool can accidentally surface a private-jet owner. This is a
deliberate design decision — see the project README.
"""

from __future__ import annotations

import csv
import sqlite3
import sys
from pathlib import Path

DEFAULT_DB_PATH = Path("aircraft_db.sqlite")

# Columns we KEEP from the OpenSky CSV. Any other column (owner, registration,
# operator_*) is discarded. OpenSky's "complete" format (2024+) uses camelCase;
# their older aircraftDatabase.csv used lowercase. Both spellings are handled.
KEPT_COLUMNS = {
    "manufacturer": ("manufacturerName", "manufacturername"),
    "model": ("model",),
    "typecode": ("typecode",),
    "serialnumber": ("serialNumber", "serialnumber"),
    "icao_aircraft_type": ("icaoAircraftClass", "icaoaircrafttype"),
    "built": ("built",),
    "engines": ("engines",),
}


def _pick(row: dict, keys: tuple[str, ...]) -> str:
    for k in keys:
        v = row.get(k)
        if v:
            return v
    return ""

SCHEMA = """
CREATE TABLE IF NOT EXISTS aircraft (
    icao24              TEXT PRIMARY KEY,
    manufacturer        TEXT,
    model               TEXT,
    typecode            TEXT,
    serialnumber        TEXT,
    icao_aircraft_type  TEXT,
    built               TEXT,
    engines             TEXT
);
CREATE INDEX IF NOT EXISTS idx_aircraft_typecode ON aircraft(typecode);
CREATE INDEX IF NOT EXISTS idx_aircraft_model    ON aircraft(model);
"""


def _connect(db_path: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def import_csv(csv_path: Path, db_path: Path = DEFAULT_DB_PATH) -> int:
    """Import an OpenSky aircraft-database CSV, dropping owner/operator columns.

    Returns the number of rows inserted.
    """
    conn = _connect(db_path)
    conn.execute("DELETE FROM aircraft")

    inserted = 0
    with csv_path.open(encoding="utf-8", errors="replace") as fh:
        # OpenSky's "complete" CSV wraps every field in single quotes rather
        # than the standard double quote. Configure the reader accordingly.
        reader = csv.DictReader(fh, quotechar="'")
        batch: list[tuple] = []
        for row in reader:
            icao24 = (row.get("icao24") or "").strip().lower()
            if not icao24:
                continue
            batch.append(
                (
                    icao24,
                    _pick(row, KEPT_COLUMNS["manufacturer"]).strip() or None,
                    _pick(row, KEPT_COLUMNS["model"]).strip() or None,
                    _pick(row, KEPT_COLUMNS["typecode"]).strip().upper() or None,
                    _pick(row, KEPT_COLUMNS["serialnumber"]).strip() or None,
                    _pick(row, KEPT_COLUMNS["icao_aircraft_type"]).strip().upper() or None,
                    _pick(row, KEPT_COLUMNS["built"]).strip() or None,
                    _pick(row, KEPT_COLUMNS["engines"]).strip() or None,
                )
            )
            if len(batch) >= 1000:
                conn.executemany(
                    "INSERT OR REPLACE INTO aircraft VALUES (?,?,?,?,?,?,?,?)",
                    batch,
                )
                inserted += len(batch)
                batch.clear()
        if batch:
            conn.executemany(
                "INSERT OR REPLACE INTO aircraft VALUES (?,?,?,?,?,?,?,?)",
                batch,
            )
            inserted += len(batch)

    conn.commit()
    conn.close()
    return inserted


def lookup(icao24: str, db_path: Path = DEFAULT_DB_PATH) -> dict | None:
    if not db_path.exists():
        return None
    conn = _connect(db_path)
    row = conn.execute(
        "SELECT * FROM aircraft WHERE icao24 = ?", (icao24.lower(),)
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def lookup_many(icao24s: list[str], db_path: Path = DEFAULT_DB_PATH) -> dict[str, dict]:
    if not db_path.exists() or not icao24s:
        return {}
    conn = _connect(db_path)
    placeholders = ",".join("?" * len(icao24s))
    rows = conn.execute(
        f"SELECT * FROM aircraft WHERE icao24 IN ({placeholders})",
        [i.lower() for i in icao24s],
    ).fetchall()
    conn.close()
    return {row["icao24"]: dict(row) for row in rows}


def find_by_type(typecode: str, db_path: Path = DEFAULT_DB_PATH) -> list[str]:
    """Return icao24s matching a typecode (e.g. 'A388' for A380-800)."""
    if not db_path.exists():
        return []
    conn = _connect(db_path)
    rows = conn.execute(
        "SELECT icao24 FROM aircraft WHERE typecode = ?", (typecode.upper(),)
    ).fetchall()
    conn.close()
    return [row["icao24"] for row in rows]


# Rough classification: which typecodes count as "business / private jet".
# Not exhaustive — covers the models that dominate the DXB/DWC business-jet
# traffic (Gulfstream, Bombardier, Dassault, Embraer Praetor/Phenom, Cessna
# Citation, Pilatus PC-24, Beechcraft).
BUSINESS_JET_TYPECODES: set[str] = {
    # Gulfstream
    "GLF4", "GLF5", "GLF6", "GA5C", "GA7C", "GLEX",
    # Bombardier Global / Challenger / Learjet
    "GL5T", "GL6T", "GL7T", "CL30", "CL35", "CL60", "LJ40", "LJ45", "LJ60", "LJ75",
    # Dassault Falcon
    "FA20", "FA50", "FA7X", "FA8X", "F2TH", "F900",
    # Embraer executive
    "E50P", "E55P", "E545", "E550",
    # Cessna Citation
    "C25A", "C25B", "C25C", "C25M", "C500", "C510", "C525", "C550", "C560",
    "C56X", "C650", "C680", "C68A", "C700", "C750",
    # Hawker / Beechcraft
    "H25B", "H25C", "HDJT", "PRM1",
    # Pilatus / others
    "PC24", "HA4T",
}


def is_business_jet(record: dict | None) -> bool:
    if not record:
        return False
    return (record.get("typecode") or "").upper() in BUSINESS_JET_TYPECODES


def _cli() -> int:
    if len(sys.argv) < 3 or sys.argv[1] != "import":
        print("Usage: python -m skywatch.aircraft_db import <aircraft_db.csv>")
        return 2
    csv_path = Path(sys.argv[2])
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}")
        return 1
    n = import_csv(csv_path)
    print(f"Imported {n} aircraft into {DEFAULT_DB_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(_cli())

"""IATA → ICAO airline code mapping.

ADS-B callsigns broadcast the ICAO airline code, not the IATA one you see on
your boarding pass. Emirates "EK500" appears in state vectors as "UAE500".
This map covers the airlines most likely to appear in Gulf / South Asian
airspace, which is the demo focus.
"""

from __future__ import annotations

IATA_TO_ICAO: dict[str, str] = {
    # Gulf carriers
    "EK": "UAE",  # Emirates
    "EY": "ETD",  # Etihad
    "QR": "QTR",  # Qatar Airways
    "FZ": "FDB",  # flydubai
    "G9": "ABY",  # Air Arabia
    "WY": "OMA",  # Oman Air
    "GF": "GFA",  # Gulf Air
    "KU": "KAC",  # Kuwait Airways
    "SV": "SVA",  # Saudia
    "XY": "KNE",  # flynas
    "MS": "MSR",  # EgyptAir
    "RJ": "RJA",  # Royal Jordanian
    "ME": "MEA",  # Middle East Airlines
    # South Asian
    "AI": "AIC",  # Air India
    "IX": "AXB",  # Air India Express
    "6E": "IGO",  # IndiGo
    "SG": "SEJ",  # SpiceJet
    "UK": "VTI",  # Vistara (merged into AI, some fleet still active)
    "QP": "AKJ",  # Akasa Air
    "UL": "ALK",  # SriLankan
    "PK": "PIA",  # Pakistan International
    "BG": "BBC",  # Biman Bangladesh
    # Europe
    "BA": "BAW",  # British Airways
    "LH": "DLH",  # Lufthansa
    "AF": "AFR",  # Air France
    "KL": "KLM",  # KLM
    "TK": "THY",  # Turkish Airlines
    "LX": "SWR",  # Swiss
    "OS": "AUA",  # Austrian
    "IB": "IBE",  # Iberia
    "AY": "FIN",  # Finnair
    # Asia-Pacific
    "SQ": "SIA",  # Singapore Airlines
    "CX": "CPA",  # Cathay Pacific
    "TG": "THA",  # Thai Airways
    "MH": "MAS",  # Malaysia Airlines
    "JL": "JAL",  # Japan Airlines
    "NH": "ANA",  # ANA
    "QF": "QFA",  # Qantas
    # Americas
    "AA": "AAL",  # American
    "DL": "DAL",  # Delta
    "UA": "UAL",  # United
    "AC": "ACA",  # Air Canada
}


_KNOWN_ICAO_PREFIXES: set[str] = set(IATA_TO_ICAO.values())


def to_icao_callsign(user_callsign: str) -> str:
    """Convert 'EK500' → 'UAE500' if the prefix is a known IATA code.

    Non-alphanumeric characters are stripped. If the callsign already starts
    with a known ICAO prefix (e.g. 'UAE500'), it's returned unchanged. This
    matters because some ICAO prefixes start with characters that also form a
    valid IATA code (e.g. 'UA' → 'UAL' would break 'UAE500').
    """
    cs = "".join(ch for ch in user_callsign if ch.isalnum()).upper()
    if len(cs) < 3:
        return cs
    if cs[:3] in _KNOWN_ICAO_PREFIXES:
        return cs
    prefix2 = cs[:2]
    if prefix2 in IATA_TO_ICAO:
        return IATA_TO_ICAO[prefix2] + cs[2:]
    return cs


def candidate_callsigns(user_callsign: str) -> list[str]:
    """Return likely ADS-B callsigns for a user query.

    Always includes the raw upper-cased input, plus the IATA→ICAO translation
    if the two-letter prefix is known.
    """
    cs = "".join(ch for ch in user_callsign if ch.isalnum()).upper()
    out = [cs]
    translated = to_icao_callsign(user_callsign)
    if translated != cs:
        out.append(translated)
    return out

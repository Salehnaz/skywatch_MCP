from skywatch import airlines


def test_iata_to_icao_translation():
    assert airlines.to_icao_callsign("EK500") == "UAE500"
    assert airlines.to_icao_callsign("QR1") == "QTR1"
    assert airlines.to_icao_callsign("6E123") == "IGO123"


def test_already_icao_passes_through():
    assert airlines.to_icao_callsign("UAE500") == "UAE500"


def test_callsign_strips_whitespace_and_uppercases():
    assert airlines.to_icao_callsign("  ek500  ") == "UAE500"


def test_candidates_include_both_forms_for_iata():
    candidates = airlines.candidate_callsigns("EK500")
    assert "EK500" in candidates
    assert "UAE500" in candidates


def test_candidates_single_for_unknown_prefix():
    # ZZ is not a known IATA code, so only the raw form is returned.
    assert airlines.candidate_callsigns("ZZ42") == ["ZZ42"]

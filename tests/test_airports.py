from skywatch import airports


def test_find_by_iata():
    apt = airports.find("DXB")
    assert apt is not None
    assert apt.icao == "OMDB"
    assert apt.city == "Dubai"


def test_find_by_icao():
    apt = airports.find("OMDB")
    assert apt is not None
    assert apt.iata == "DXB"


def test_find_by_city_case_insensitive():
    apt = airports.find("dubai")
    assert apt is not None
    assert apt.iata == "DXB"


def test_unknown_returns_none():
    assert airports.find("XXX") is None
    assert airports.find("") is None

"""Airport IATA/ICAO → coordinates lookup.

Small hand-maintained list focused on Gulf/UAE hubs plus a handful of major
world airports. Extend as needed. Keeping this in-repo avoids another API
dependency and lets `get_airport_activity` resolve DXB → OMDB immediately.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Airport:
    iata: str
    icao: str
    name: str
    city: str
    country: str
    lat: float
    lon: float


AIRPORTS: list[Airport] = [
    # UAE
    Airport("DXB", "OMDB", "Dubai International", "Dubai", "AE", 25.2532, 55.3657),
    Airport("DWC", "OMDW", "Al Maktoum International", "Dubai", "AE", 24.8968, 55.1614),
    Airport("AUH", "OMAA", "Zayed International", "Abu Dhabi", "AE", 24.4330, 54.6511),
    Airport("SHJ", "OMSJ", "Sharjah International", "Sharjah", "AE", 25.3286, 55.5172),
    Airport("RKT", "OMRK", "Ras Al Khaimah International", "Ras Al Khaimah", "AE", 25.6135, 55.9388),
    Airport("FJR", "OMFJ", "Fujairah International", "Fujairah", "AE", 25.1122, 56.3240),
    # Gulf / Middle East
    Airport("DOH", "OTHH", "Hamad International", "Doha", "QA", 25.2731, 51.6080),
    Airport("BAH", "OBBI", "Bahrain International", "Manama", "BH", 26.2708, 50.6336),
    Airport("KWI", "OKBK", "Kuwait International", "Kuwait City", "KW", 29.2266, 47.9689),
    Airport("MCT", "OOMS", "Muscat International", "Muscat", "OM", 23.5933, 58.2844),
    Airport("RUH", "OERK", "King Khalid International", "Riyadh", "SA", 24.9576, 46.6988),
    Airport("JED", "OEJN", "King Abdulaziz International", "Jeddah", "SA", 21.6796, 39.1565),
    Airport("IST", "LTFM", "Istanbul Airport", "Istanbul", "TR", 41.2753, 28.7519),
    Airport("CAI", "HECA", "Cairo International", "Cairo", "EG", 30.1219, 31.4056),
    Airport("TLV", "LLBG", "Ben Gurion", "Tel Aviv", "IL", 32.0114, 34.8867),
    Airport("AMM", "OJAI", "Queen Alia International", "Amman", "JO", 31.7226, 35.9932),
    Airport("BEY", "OLBA", "Rafic Hariri International", "Beirut", "LB", 33.8209, 35.4884),
    Airport("IKA", "OIIE", "Imam Khomeini International", "Tehran", "IR", 35.4161, 51.1522),
    # South Asia
    Airport("BOM", "VABB", "Chhatrapati Shivaji Maharaj", "Mumbai", "IN", 19.0887, 72.8679),
    Airport("DEL", "VIDP", "Indira Gandhi International", "New Delhi", "IN", 28.5562, 77.1000),
    Airport("BLR", "VOBL", "Kempegowda International", "Bengaluru", "IN", 13.1986, 77.7066),
    Airport("COK", "VOCI", "Cochin International", "Kochi", "IN", 10.1520, 76.4019),
    Airport("TRV", "VOTV", "Trivandrum International", "Thiruvananthapuram", "IN", 8.4821, 76.9200),
    Airport("HYD", "VOHS", "Rajiv Gandhi International", "Hyderabad", "IN", 17.2403, 78.4294),
    Airport("MAA", "VOMM", "Chennai International", "Chennai", "IN", 12.9941, 80.1709),
    Airport("CCU", "VECC", "Netaji Subhas Chandra Bose", "Kolkata", "IN", 22.6547, 88.4467),
    Airport("AMD", "VAAH", "Sardar Vallabhbhai Patel", "Ahmedabad", "IN", 23.0772, 72.6347),
    Airport("GOI", "VOGO", "Dabolim", "Goa", "IN", 15.3808, 73.8314),
    Airport("CMB", "VCBI", "Bandaranaike International", "Colombo", "LK", 7.1808, 79.8841),
    Airport("KHI", "OPKC", "Jinnah International", "Karachi", "PK", 24.9008, 67.1681),
    Airport("DAC", "VGHS", "Hazrat Shahjalal International", "Dhaka", "BD", 23.8433, 90.3978),
    Airport("KTM", "VNKT", "Tribhuvan International", "Kathmandu", "NP", 27.6961, 85.3591),
    # Europe
    Airport("LHR", "EGLL", "Heathrow", "London", "GB", 51.4700, -0.4543),
    Airport("LGW", "EGKK", "Gatwick", "London", "GB", 51.1481, -0.1903),
    Airport("STN", "EGSS", "Stansted", "London", "GB", 51.8850, 0.2350),
    Airport("MAN", "EGCC", "Manchester", "Manchester", "GB", 53.3537, -2.2750),
    Airport("DUB", "EIDW", "Dublin", "Dublin", "IE", 53.4213, -6.2701),
    Airport("CDG", "LFPG", "Charles de Gaulle", "Paris", "FR", 49.0097, 2.5479),
    Airport("FRA", "EDDF", "Frankfurt", "Frankfurt", "DE", 50.0379, 8.5622),
    Airport("MUC", "EDDM", "Munich", "Munich", "DE", 48.3538, 11.7861),
    Airport("BER", "EDDB", "Berlin Brandenburg", "Berlin", "DE", 52.3667, 13.5033),
    Airport("HAM", "EDDH", "Hamburg", "Hamburg", "DE", 53.6304, 9.9882),
    Airport("AMS", "EHAM", "Schiphol", "Amsterdam", "NL", 52.3105, 4.7683),
    Airport("BRU", "EBBR", "Brussels", "Brussels", "BE", 50.9014, 4.4844),
    Airport("MAD", "LEMD", "Adolfo Suárez Madrid–Barajas", "Madrid", "ES", 40.4936, -3.5668),
    Airport("BCN", "LEBL", "Barcelona–El Prat", "Barcelona", "ES", 41.2971, 2.0785),
    Airport("LIS", "LPPT", "Humberto Delgado", "Lisbon", "PT", 38.7813, -9.1359),
    Airport("FCO", "LIRF", "Leonardo da Vinci–Fiumicino", "Rome", "IT", 41.8003, 12.2389),
    Airport("MXP", "LIMC", "Malpensa", "Milan", "IT", 45.6306, 8.7281),
    Airport("ATH", "LGAV", "Eleftherios Venizelos", "Athens", "GR", 37.9364, 23.9445),
    Airport("VIE", "LOWW", "Vienna International", "Vienna", "AT", 48.1103, 16.5697),
    Airport("ZRH", "LSZH", "Zurich", "Zurich", "CH", 47.4647, 8.5492),
    Airport("CPH", "EKCH", "Copenhagen", "Copenhagen", "DK", 55.6180, 12.6560),
    Airport("ARN", "ESSA", "Stockholm Arlanda", "Stockholm", "SE", 59.6519, 17.9186),
    Airport("OSL", "ENGM", "Oslo Gardermoen", "Oslo", "NO", 60.1939, 11.1004),
    Airport("HEL", "EFHK", "Helsinki-Vantaa", "Helsinki", "FI", 60.3172, 24.9633),
    Airport("PRG", "LKPR", "Václav Havel", "Prague", "CZ", 50.1008, 14.2600),
    Airport("WAW", "EPWA", "Warsaw Chopin", "Warsaw", "PL", 52.1657, 20.9671),
    Airport("BUD", "LHBP", "Budapest Ferenc Liszt", "Budapest", "HU", 47.4394, 19.2611),
    Airport("SVO", "UUEE", "Sheremetyevo", "Moscow", "RU", 55.9726, 37.4146),
    Airport("DME", "UUDD", "Domodedovo", "Moscow", "RU", 55.4088, 37.9063),
    Airport("LED", "ULLI", "Pulkovo", "Saint Petersburg", "RU", 59.8003, 30.2625),
    # Africa
    Airport("JNB", "FAOR", "O. R. Tambo International", "Johannesburg", "ZA", -26.1392, 28.2460),
    Airport("CPT", "FACT", "Cape Town International", "Cape Town", "ZA", -33.9648, 18.6017),
    Airport("NBO", "HKJK", "Jomo Kenyatta International", "Nairobi", "KE", -1.3192, 36.9278),
    Airport("LOS", "DNMM", "Murtala Muhammed International", "Lagos", "NG", 6.5774, 3.3211),
    Airport("ADD", "HAAB", "Addis Ababa Bole", "Addis Ababa", "ET", 8.9779, 38.7993),
    Airport("CMN", "GMMN", "Mohammed V International", "Casablanca", "MA", 33.3675, -7.5898),
    # Asia-Pacific
    Airport("SIN", "WSSS", "Changi", "Singapore", "SG", 1.3644, 103.9915),
    Airport("HKG", "VHHH", "Hong Kong International", "Hong Kong", "HK", 22.3080, 113.9185),
    Airport("BKK", "VTBS", "Suvarnabhumi", "Bangkok", "TH", 13.6900, 100.7501),
    Airport("KUL", "WMKK", "Kuala Lumpur International", "Kuala Lumpur", "MY", 2.7456, 101.7099),
    Airport("CGK", "WIII", "Soekarno–Hatta International", "Jakarta", "ID", -6.1256, 106.6559),
    Airport("DPS", "WADD", "Ngurah Rai International", "Denpasar", "ID", -8.7481, 115.1672),
    Airport("MNL", "RPLL", "Ninoy Aquino International", "Manila", "PH", 14.5086, 121.0198),
    Airport("HAN", "VVNB", "Noi Bai International", "Hanoi", "VN", 21.2212, 105.8072),
    Airport("SGN", "VVTS", "Tan Son Nhat International", "Ho Chi Minh City", "VN", 10.8188, 106.6519),
    Airport("NRT", "RJAA", "Narita International", "Tokyo", "JP", 35.7720, 140.3929),
    Airport("HND", "RJTT", "Haneda", "Tokyo", "JP", 35.5494, 139.7798),
    Airport("ICN", "RKSI", "Incheon International", "Seoul", "KR", 37.4602, 126.4407),
    Airport("PEK", "ZBAA", "Beijing Capital", "Beijing", "CN", 40.0801, 116.5846),
    Airport("PKX", "ZBAD", "Beijing Daxing", "Beijing", "CN", 39.5098, 116.4108),
    Airport("PVG", "ZSPD", "Shanghai Pudong", "Shanghai", "CN", 31.1443, 121.8083),
    Airport("CAN", "ZGGG", "Guangzhou Baiyun", "Guangzhou", "CN", 23.3924, 113.2988),
    Airport("TPE", "RCTP", "Taoyuan International", "Taipei", "TW", 25.0777, 121.2328),
    Airport("SYD", "YSSY", "Kingsford Smith", "Sydney", "AU", -33.9399, 151.1753),
    Airport("MEL", "YMML", "Melbourne", "Melbourne", "AU", -37.6733, 144.8433),
    Airport("BNE", "YBBN", "Brisbane", "Brisbane", "AU", -27.3842, 153.1175),
    Airport("PER", "YPPH", "Perth", "Perth", "AU", -31.9403, 115.9669),
    Airport("AKL", "NZAA", "Auckland", "Auckland", "NZ", -37.0082, 174.7850),
    # North America
    Airport("JFK", "KJFK", "John F. Kennedy International", "New York", "US", 40.6413, -73.7781),
    Airport("LGA", "KLGA", "LaGuardia", "New York", "US", 40.7769, -73.8740),
    Airport("EWR", "KEWR", "Newark Liberty International", "Newark", "US", 40.6895, -74.1745),
    Airport("LAX", "KLAX", "Los Angeles International", "Los Angeles", "US", 33.9416, -118.4085),
    Airport("SFO", "KSFO", "San Francisco International", "San Francisco", "US", 37.6213, -122.3790),
    Airport("SEA", "KSEA", "Seattle–Tacoma International", "Seattle", "US", 47.4502, -122.3088),
    Airport("ORD", "KORD", "O'Hare International", "Chicago", "US", 41.9742, -87.9073),
    Airport("DFW", "KDFW", "Dallas–Fort Worth International", "Dallas", "US", 32.8998, -97.0403),
    Airport("ATL", "KATL", "Hartsfield–Jackson", "Atlanta", "US", 33.6407, -84.4277),
    Airport("MIA", "KMIA", "Miami International", "Miami", "US", 25.7959, -80.2870),
    Airport("BOS", "KBOS", "Logan International", "Boston", "US", 42.3656, -71.0096),
    Airport("DEN", "KDEN", "Denver International", "Denver", "US", 39.8561, -104.6737),
    Airport("LAS", "KLAS", "Harry Reid International", "Las Vegas", "US", 36.0840, -115.1537),
    Airport("PHX", "KPHX", "Phoenix Sky Harbor", "Phoenix", "US", 33.4342, -112.0116),
    Airport("IAD", "KIAD", "Washington Dulles", "Washington", "US", 38.9531, -77.4565),
    Airport("YYZ", "CYYZ", "Toronto Pearson International", "Toronto", "CA", 43.6777, -79.6248),
    Airport("YUL", "CYUL", "Montréal–Trudeau", "Montreal", "CA", 45.4706, -73.7408),
    Airport("YVR", "CYVR", "Vancouver International", "Vancouver", "CA", 49.1967, -123.1815),
    Airport("MEX", "MMMX", "Benito Juárez International", "Mexico City", "MX", 19.4363, -99.0721),
    # South America
    Airport("GRU", "SBGR", "São Paulo–Guarulhos", "São Paulo", "BR", -23.4356, -46.4731),
    Airport("GIG", "SBGL", "Rio de Janeiro–Galeão", "Rio de Janeiro", "BR", -22.8100, -43.2506),
    Airport("EZE", "SAEZ", "Ministro Pistarini", "Buenos Aires", "AR", -34.8222, -58.5358),
    Airport("SCL", "SCEL", "Arturo Merino Benítez", "Santiago", "CL", -33.3928, -70.7858),
    Airport("BOG", "SKBO", "El Dorado International", "Bogotá", "CO", 4.7016, -74.1469),
    Airport("LIM", "SPJC", "Jorge Chávez International", "Lima", "PE", -12.0219, -77.1143),
]

_BY_IATA = {a.iata: a for a in AIRPORTS}
_BY_ICAO = {a.icao: a for a in AIRPORTS}
# When a city has multiple airports (Dubai → DXB and DWC), the first entry in
# AIRPORTS wins. Order the list with the primary hub first.
_BY_CITY: dict[str, Airport] = {}
for _a in AIRPORTS:
    _BY_CITY.setdefault(_a.city.lower(), _a)


def find(code_or_city: str) -> Airport | None:
    """Look up an airport by IATA, ICAO, or city name (case-insensitive)."""
    key = code_or_city.strip()
    if not key:
        return None
    up = key.upper()
    if up in _BY_IATA:
        return _BY_IATA[up]
    if up in _BY_ICAO:
        return _BY_ICAO[up]
    return _BY_CITY.get(key.lower())

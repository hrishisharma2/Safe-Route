"""
One-time script that builds mumbai_data.py.

For each road between two places, it asks the free OSRM routing service
(router.project-osrm.org, built on OpenStreetMap data) for:
  - the real street shape, so the road follows actual streets on the map
  - the driving distance and free-flow driving time

Mumbai traffic is much slower than free-flow, so we multiply the time by TRAFFIC_FACTOR.
Safety scores are DEMO values typed in below. They are not real safety data.

Run from the webapp folder:   python tools/build_mumbai.py
"""
import json
import os
import ssl
import time
import urllib.request

try:
    import certifi   # pip install certifi  (needed for HTTPS with python.org Python on macOS)
    SSL_CONTEXT = ssl.create_default_context(cafile=certifi.where())
except ImportError:
    SSL_CONTEXT = ssl.create_default_context()

TRAFFIC_FACTOR = 2.0

# name: (latitude, longitude)
PLACES = {
    "Colaba": (18.9220, 72.8347),
    "CSMT": (18.9398, 72.8355),
    "Churchgate": (18.9322, 72.8264),
    "Mumbai Central": (18.9690, 72.8205),
    "Byculla": (18.9790, 72.8330),
    "Worli": (19.0100, 72.8170),
    "Dadar": (19.0186, 72.8424),
    "Sion": (19.0434, 72.8626),
    "Bandra": (19.0544, 72.8406),
    "BKC": (19.0660, 72.8680),
    "Kurla": (19.0656, 72.8792),
    "Chembur": (19.0622, 72.9005),
    "Ghatkopar": (19.0860, 72.9081),
    "Santacruz": (19.0817, 72.8414),
    "Juhu": (19.1075, 72.8263),
    "Vile Parle": (19.0996, 72.8436),
    "Airport T2": (19.0968, 72.8740),
    "Andheri": (19.1197, 72.8464),
    "Powai": (19.1176, 72.9060),
    "Vikhroli": (19.1110, 72.9280),
    "Mulund": (19.1726, 72.9565),
    "Goregaon": (19.1646, 72.8493),
    "Malad": (19.1868, 72.8484),
    "Borivali": (19.2290, 72.8567),
}

# (from, to, road name, DEMO safety 1-10)
ROADS = [
    ("Colaba", "CSMT", "Shahid Bhagat Singh Rd", 8),
    ("Colaba", "Churchgate", "Madame Cama Rd", 8),
    ("Churchgate", "CSMT", "Veer Nariman Rd", 8),
    ("Churchgate", "Mumbai Central", "Marine Drive", 9),
    ("Churchgate", "Worli", "Coastal Road", 9),
    ("CSMT", "Byculla", "Mohammed Ali Rd", 5),
    ("Mumbai Central", "Byculla", "Bellasis Rd", 5),
    ("Mumbai Central", "Worli", "Haji Ali / Lala Lajpat Rai Marg", 7),
    ("Byculla", "Dadar", "Dr Ambedkar Rd", 6),
    ("Worli", "Dadar", "Senapati Bapat Marg", 6),
    ("Worli", "Bandra", "Bandra–Worli Sea Link", 9),
    ("Dadar", "Sion", "Sion Rd", 5),
    ("Dadar", "Bandra", "Mahim Causeway", 6),
    ("CSMT", "Chembur", "Eastern Freeway", 8),
    ("Sion", "Kurla", "LBS Marg", 4),
    ("Sion", "Chembur", "Sion–Trombay Rd", 6),
    ("Sion", "BKC", "Sion–Bandra Link Rd", 6),
    ("Bandra", "BKC", "Kalanagar Rd", 8),
    ("BKC", "Kurla", "BKC–Kurla Rd", 6),
    ("Bandra", "Santacruz", "Western Express Hwy", 6),
    ("Santacruz", "Juhu", "Juhu Tara Rd", 7),
    ("Santacruz", "Vile Parle", "Western Express Hwy", 7),
    ("Santacruz", "Kurla", "Santacruz–Chembur Link Rd", 6),
    ("Kurla", "Airport T2", "Andheri–Kurla Rd", 5),
    ("Kurla", "Ghatkopar", "LBS Marg", 4),
    ("Chembur", "Ghatkopar", "Eastern Express Hwy", 7),
    ("Vile Parle", "Andheri", "Western Express Hwy", 7),
    ("Vile Parle", "Airport T2", "Nehru Rd", 6),
    ("Juhu", "Vile Parle", "Juhu Church Rd", 7),
    ("Juhu", "Andheri", "Juhu–Versova Link Rd", 6),
    ("Andheri", "Airport T2", "Sahar Rd", 6),
    ("Andheri", "Powai", "Saki Vihar Rd", 5),
    ("Ghatkopar", "Powai", "Gandhinagar Rd", 6),
    ("Ghatkopar", "Vikhroli", "Eastern Express Hwy", 7),
    ("Vikhroli", "Powai", "Jogeshwari–Vikhroli Link Rd", 7),
    ("Vikhroli", "Mulund", "Eastern Express Hwy", 7),
    ("Powai", "Goregaon", "Aarey Rd", 3),
    ("Andheri", "Goregaon", "Western Express Hwy", 7),
    ("Goregaon", "Malad", "Western Express Hwy", 7),
    ("Malad", "Borivali", "Western Express Hwy", 7),
]


def fetch_route(a, b):
    (lat1, lng1), (lat2, lng2) = PLACES[a], PLACES[b]
    url = (f"https://router.project-osrm.org/route/v1/driving/{lng1},{lat1};{lng2},{lat2}"
           "?overview=simplified&geometries=geojson")
    req = urllib.request.Request(url, headers={"User-Agent": "SafeRoute student project"})
    with urllib.request.urlopen(req, timeout=30, context=SSL_CONTEXT) as res:
        data = json.load(res)
    route = data["routes"][0]
    # GeoJSON stores [longitude, latitude]; Leaflet wants [latitude, longitude].
    shape = [[round(lat, 5), round(lng, 5)] for lng, lat in route["geometry"]["coordinates"]]
    return route["distance"], route["duration"], shape


def main():
    names = list(PLACES)
    roads_out = []
    for a, b, road_name, safety in ROADS:
        dist, dur, shape = fetch_route(a, b)
        minutes = max(2, round(dur * TRAFFIC_FACTOR / 60))
        print(f"{a:>14} → {b:<14} {dist / 1000:5.1f} km  {minutes:3d} min  {road_name}")
        roads_out.append((names.index(a), names.index(b), minutes, safety, road_name, round(dist / 1000, 1), shape))
        time.sleep(1)   # be polite to the free service: one request per second

    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mumbai_data.py")
    with open(out, "w") as f:
        f.write('"""Mumbai map data. GENERATED by tools/build_mumbai.py, do not edit by hand.\n\n'
                "Road shapes and distances: OpenStreetMap contributors, via OSRM.\n"
                f"Times: OSRM free-flow driving time x {TRAFFIC_FACTOR} for traffic (an estimate).\n"
                'Safety scores: DEMO values, not real safety data.\n"""\n\n')
        f.write("# (id, name, latitude, longitude)\nLOCATIONS = [\n")
        for i, n in enumerate(names):
            f.write(f"    ({i}, {n!r}, {PLACES[n][0]}, {PLACES[n][1]}),\n")
        f.write("]\n\n# (from_id, to_id, minutes, safety, road name, km, shape [[lat, lng], ...])\nROADS = [\n")
        for r in roads_out:
            f.write(f"    {r!r},\n")
        f.write("]\n")
    print(f"\nWrote {len(names)} places and {len(roads_out)} roads to {out}")


if __name__ == "__main__":
    main()

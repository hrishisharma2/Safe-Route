"""Loads the Mumbai map (from mumbai_data.py) into the database."""
import json
import os

from mumbai_data import LOCATIONS, ROADS

MAP_SCHEMA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "map_schema.sql")


def load_demo_map(conn):
    """Replace all locations and roads with the Mumbai map. Users are kept."""
    with open(MAP_SCHEMA) as f:
        conn.executescript(f.read())          # drops and recreates the map tables
    # executemany runs the same INSERT once per tuple.
    # The ? placeholders are filled in safely by sqlite3 (this prevents SQL injection).
    conn.executemany("INSERT INTO locations (id, name, lat, lng) VALUES (?, ?, ?, ?)", LOCATIONS)
    conn.executemany(
        "INSERT INTO roads (from_id, to_id, time, safety, name, km, shape) VALUES (?, ?, ?, ?, ?, ?, ?)",
        [(a, b, t, s, name, km, json.dumps(shape)) for a, b, t, s, name, km, shape in ROADS],
    )
    conn.commit()

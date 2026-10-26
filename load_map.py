"""
Replace the map in an existing database with the Mumbai map.
User accounts are kept. Any road edits made on the admin page are lost.

Run:   python load_map.py
"""
import sqlite3

from init_db import DB_PATH
from seed_data import load_demo_map

if __name__ == "__main__":
    conn = sqlite3.connect(DB_PATH)
    load_demo_map(conn)
    places = conn.execute("SELECT COUNT(*) FROM locations").fetchone()[0]
    roads = conn.execute("SELECT COUNT(*) FROM roads").fetchone()[0]
    conn.close()
    print(f"Loaded the Mumbai map: {places} places, {roads} roads. Users were not changed.")

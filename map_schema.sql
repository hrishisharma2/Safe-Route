-- Map tables only. seed_data.load_demo_map() runs this to replace the map
-- while keeping user accounts.

DROP TABLE IF EXISTS roads;
DROP TABLE IF EXISTS locations;

-- Graph vertices: real places, stored as GPS coordinates.
CREATE TABLE locations (
    id   INTEGER PRIMARY KEY,
    name TEXT    NOT NULL UNIQUE,
    lat  REAL    NOT NULL,      -- latitude  (north-south), Mumbai is about 19
    lng  REAL    NOT NULL       -- longitude (east-west),   Mumbai is about 72.8
);

-- Graph edges. Roads are two-way. CHECK rules stop bad values at the database level.
CREATE TABLE roads (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    from_id    INTEGER NOT NULL REFERENCES locations(id),
    to_id      INTEGER NOT NULL REFERENCES locations(id),
    name       TEXT    NOT NULL,
    km         REAL    NOT NULL,
    time       INTEGER NOT NULL CHECK (time > 0),
    safety     INTEGER NOT NULL CHECK (safety BETWEEN 1 AND 10),
    shape      TEXT    NOT NULL,  -- JSON list of [lat, lng] points along the real street
    updated_by INTEGER REFERENCES users(id),
    updated_at TEXT
);

-- SafeRoute database schema (SQLite)
-- Each CREATE TABLE describes one kind of thing we store.
-- Running this file wipes ALL tables (including users) and creates fresh ones.
-- The map tables (locations, roads) are in map_schema.sql.

DROP TABLE IF EXISTS roads;
DROP TABLE IF EXISTS locations;
DROP TABLE IF EXISTS users;

-- People who can log in. We never store the password itself, only a hash of it.
CREATE TABLE users (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    username      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    role          TEXT    NOT NULL DEFAULT 'user' CHECK (role IN ('user', 'admin')),
    created_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

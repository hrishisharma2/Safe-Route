"""
Tests the whole web app (login, roles, API) against a temporary database.
Your real database is not touched.

Run with:  python test_app.py
"""
import os
import sqlite3
import tempfile

# Point the app at a throwaway database BEFORE importing it.
TEST_DB = os.path.join(tempfile.mkdtemp(), "test.db")
os.environ["SAFEROUTE_DB"] = TEST_DB

from werkzeug.security import generate_password_hash  # noqa: E402

from app import app  # noqa: E402
from seed_data import load_demo_map  # noqa: E402

# Test accounts that exist only in the temporary database.
TEST_ADMIN = ("test_admin", "admin-pass-123")
TEST_USER = ("test_user", "user-pass-123")


def make_db(path):
    conn = sqlite3.connect(path)
    with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")) as f:
        conn.executescript(f.read())
    load_demo_map(conn)
    conn.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')",
                 (TEST_ADMIN[0], generate_password_hash(TEST_ADMIN[1])))
    conn.commit()
    conn.close()


def check(label, condition):
    print(("PASS " if condition else "FAIL ") + label)
    assert condition, label


def main():
    make_db(TEST_DB)
    client = app.test_client()
    login = lambda u, p: client.post("/login", data={"username": u, "password": p})

    check("home page is public", client.get("/").status_code == 200)
    check("logged-out visitors are sent to login", client.get("/plan").status_code == 302)
    check("API needs login", client.get("/api/map").status_code == 401)
    check("register a user", client.post("/register", data={"username": TEST_USER[0], "password": TEST_USER[1]}).status_code == 302)
    check("duplicate username rejected", b"already taken" in client.post("/register", data={"username": TEST_USER[0], "password": TEST_USER[1]}).data)
    check("wrong password rejected", b"Wrong username" in login(TEST_USER[0], "nope").data)
    check("user login goes to route planner", login(*TEST_USER).headers["Location"] == "/plan")
    check("user cannot open admin page", client.get("/admin").status_code == 403)
    check("user cannot change roads", client.put("/api/roads/1", json={"time": 5, "safety": 5}).status_code == 403)

    m = client.get("/api/map").get_json()
    check("map has Mumbai places and road shapes", len(m["locations"]) == 24 and len(m["roads"][0]["shape"]) > 1)
    ids = {l["name"]: l["id"] for l in m["locations"]}
    r = client.get(f"/api/routes?from={ids['Mumbai Central']}&to={ids['Andheri']}&w=0.5").get_json()
    check("three different routes", len({tuple(r[k]["path"]) for k in ("fastest", "balanced", "safest")}) == 3)
    check("bad route request rejected", client.get("/api/routes?from=0&to=999").status_code == 400)
    client.get("/logout")

    check("admin login goes to admin page", login(*TEST_ADMIN).headers["Location"] == "/admin")
    check("safety 11 rejected", client.put("/api/roads/1", json={"time": 3, "safety": 11}).status_code == 400)
    check("admin can update a road", client.put("/api/roads/1", json={"time": 3, "safety": 10}).get_json()["ok"])
    road = next(x for x in client.get("/api/map").get_json()["roads"] if x["id"] == 1)
    check("update saved with admin's name", road["safety"] == 10 and road["updated_by"] == TEST_ADMIN[0])
    check("unknown road gives 404", client.put("/api/roads/999", json={"time": 3, "safety": 5}).status_code == 404)
    check("reset restores the map", client.post("/api/roads/reset").get_json()["ok"])
    check("login cannot redirect to other sites", login(*TEST_ADMIN).status_code == 302 and
          client.post("/login?next=//evil.com", data=dict(zip(("username", "password"), TEST_ADMIN))).headers["Location"] == "/admin")
    print("All app tests passed.")


if __name__ == "__main__":
    main()

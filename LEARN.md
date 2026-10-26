# Learn full-stack web development with SafeRoute

This guide walks through the SafeRoute web app one idea at a time. Each lesson points to the file where the idea lives, then gives you something to try. Read a lesson, open the file, do the "Try it" step, and move on.

---

## Lesson 0: Get it running

```bash
cd ~/code/tii/webapp
source .venv/bin/activate          # use this project's own Python + Flask
python init_db.py                  # create the database and your admin account
flask --app app run --debug        # start the server
```

Open http://127.0.0.1:5000 in your browser.

1. Log in with the admin account you just created. You land on **Admin**.
2. Change a road's safety, click **Save**, then go to **Plan a route** and see the route change on the Mumbai map.
3. Log out, click **Create one** and register a normal user. That user can plan routes. Opening `/admin` gives "Admins only".

`--debug` reloads the server whenever you save a Python file and shows detailed errors in the browser. Never use it on a public server.

To stop the server, press `Ctrl+C`. Next time you only need the `source` line and the `flask` line.

---

## Lesson 1: The big picture

A web app has three parts that talk to each other:

```
 Browser (HTML/CSS/JS)  ──HTTP request──▶  Server (Python/Flask)  ──SQL──▶  Database (SQLite)
                        ◀──HTML or JSON──                          ◀─rows──
```

| Part | Job | SafeRoute files |
|---|---|---|
| **Frontend** | What the user sees and clicks | `templates/*.html`, `static/*.js`, `static/style.css` |
| **Backend** | Checks who you are, applies the rules, runs the algorithm | `app.py`, `routing.py` |
| **Database** | Remembers things after the server stops | `schema.sql`, `instance/saferoute.db` |

The golden rule is to **never trust the browser**. Anyone can change the JavaScript or send their own requests, so every important check (are you logged in? are you an admin? is safety between 1 and 10?) happens on the server.

---

## Lesson 2: The database (`schema.sql`)

A database stores data in **tables**. A table is like a spreadsheet: columns are fields, rows are records.

```sql
CREATE TABLE roads (
    id      INTEGER PRIMARY KEY AUTOINCREMENT,  -- unique number for each row
    from_id INTEGER NOT NULL REFERENCES locations(id),
    safety  INTEGER NOT NULL CHECK (safety BETWEEN 1 AND 10),
    ...
);
```

- `PRIMARY KEY` gives each row a unique id.
- `REFERENCES` is a **foreign key**: `from_id` must be a real location.
- `NOT NULL`, `UNIQUE` and `CHECK` are **constraints**. The database refuses bad data even if your Python code has a bug.

This is your graph from the C program: `locations` are vertices, `roads` are edges.

**The four basic SQL commands (CRUD):**

```sql
SELECT * FROM roads WHERE safety < 5;                 -- Read
INSERT INTO users (username, password_hash) VALUES (?, ?);   -- Create
UPDATE roads SET safety = 9 WHERE id = 6;             -- Update
DELETE FROM roads WHERE id = 6;                       -- Delete
```

**Try it.** Open the database directly:

```bash
sqlite3 instance/saferoute.db
.headers on
.mode column
SELECT * FROM users;
SELECT * FROM roads WHERE safety <= 4;
SELECT l1.name, l2.name, time, safety
  FROM roads JOIN locations l1 ON l1.id = from_id JOIN locations l2 ON l2.id = to_id;
.quit
```

Look at `users`: the password column is a long scrambled string, not your password. Lesson 3 explains why.

---

## Lesson 3: Passwords and hashing (`app.py` → `register`, `login`)

**Never store passwords as plain text.** If the database leaks, everyone's password leaks, and people reuse passwords on other sites.

Instead we store a **hash**:

```python
generate_password_hash("pass123")
# 'scrypt:32768:8:1$Xk3p...$9f2a...'   ← different every time because of a random "salt"
check_password_hash(stored_hash, "pass123")   # True
check_password_hash(stored_hash, "wrong")     # False
```

A hash is a one-way function: easy to compute, practically impossible to reverse. At login we hash what the user typed and compare. The **salt** is random data mixed in, so two users with the same password get different hashes.

Also notice in `login()`:

```python
if user is None or not check_password_hash(...):
    flash("Wrong username or password.")
```

We give the same message whether the username or the password was wrong, so an attacker can't use the login form to find out which usernames exist.

**Try it.** In a Python shell (`python`), import `generate_password_hash`, hash the same password twice and compare the results.

---

## Lesson 4: SQL injection and the `?` placeholder

Look at every query in `app.py`. They all use `?`:

```python
db.execute("SELECT * FROM users WHERE username = ?", (username,))
```

Never build SQL by pasting strings together:

```python
# DANGEROUS — never do this
db.execute(f"SELECT * FROM users WHERE username = '{username}'")
```

If someone types the username `' OR '1'='1`, the dangerous version becomes `... WHERE username = '' OR '1'='1'`, which matches every user. With `?`, SQLite treats the input purely as data, never as SQL code. This attack is called **SQL injection**, and it is one of the most common real-world security bugs.

---

## Lesson 5: Sessions, or how the server remembers you (`app.py`)

HTTP is **stateless**: every request is separate, and the server forgets you between them. To stay logged in:

1. After a correct password, the server stores `session["user_id"] = 5`.
2. Flask puts this in a **cookie**, a small piece of data the browser sends back with every request. It is **signed** with `SECRET_KEY`, so nobody can edit it to say `user_id = 1`.
3. Before each request, `load_logged_in_user()` reads the cookie and loads the user into `g.user`.
4. `logout()` clears the session.

**Try it.** While logged in, open your browser's DevTools (`Cmd+Option+I`) → Application → Cookies. You'll see a cookie called `session`. Delete it and refresh: you're logged out.

---

## Lesson 6: Roles and decorators (`login_required`, `admin_required`)

A **decorator** wraps a function to add behaviour before it runs:

```python
@app.route("/admin")
@admin_required          # runs first: are you logged in AND an admin?
def admin():
    return render_template("admin.html")
```

This is **authentication** vs **authorization**:
- **Authentication:** who are you? (login)
- **Authorization:** what are you allowed to do? (the `role` column: `user` or `admin`)

The admin page and `PUT /api/roads/<id>` are both protected. Hiding the Admin link in the menu is just for looks. The real protection is the decorator on the server.

**Try it.** Make your normal user an admin straight in the database, then refresh the browser:
```sql
UPDATE users SET role = 'admin' WHERE username = 'yourname';
```

---

## Lesson 7: Pages vs an API (`app.py` bottom half)

The server sends two kinds of answers:

- **HTML pages** (`/`, `/admin`, `/login`): full pages built from **Jinja templates**. `{% extends "base.html" %}` reuses the shared layout, and `{{ g.user.username }}` inserts a value.
- **A JSON API** (`/api/...`): data only, for JavaScript to use.

| Method + URL | What it does | Who |
|---|---|---|
| `GET /api/map` | All places and roads | logged in |
| `GET /api/routes?from=0&to=9&w=0.5` | Preferred, fastest, balanced and safest routes | logged in |
| `PUT /api/roads/6` with `{"time":3,"safety":9}` | Change a road | admin |
| `POST /api/roads/reset` | Restore demo values | admin |

**HTTP methods** describe intent: `GET` reads, `POST` creates or performs an action, `PUT` replaces or updates. **Status codes** describe the result: `200` OK, `302` redirect, `400` bad input, `401` not logged in, `403` not allowed, `404` not found.

**Try it.** While logged in, open http://127.0.0.1:5000/api/routes?from=0&to=9&w=1 in the browser. That raw JSON is exactly what `user.js` receives.

---

## Lesson 8: The frontend talks to the API (`static/user.js`, `static/admin.js`)

```js
const res = await fetch(`/api/routes?from=${state.from}&to=${state.to}&w=${weight()}`);
const routes = await res.json();
render();   // draw the result on the page
```

- `fetch` sends an HTTP request without reloading the page.
- `async`/`await` waits for the answer without freezing the page.
- The admin page sends data **to** the server with `method: "PUT"` and a JSON `body`.

**Try it.** Open DevTools → Network, then change the preference on the route page. You'll see each `/api/routes` request and its response.

---

## Lesson 9: The algorithm on the server (`routing.py`)

This is the same Dijkstra algorithm and cost formula as `saferoute.c`, rewritten in Python:

| C version | Python version |
|---|---|
| `struct Edge` linked list | `adj = {v: [(neighbour, road), ...]}` (a dict of lists) |
| `double dist[MAX_NODES]` | `dist = {v: math.inf ...}` |
| loop to find smallest unvisited | `min(..., key=lambda v: dist[v])` |
| `prev[]` + `via[]` arrays | `prev` and `via` dicts |

`routing.py` knows nothing about the web or the database, so it can be tested on its own:

```bash
python test_routing.py
```

Keeping the core logic separate from the web code is a habit worth building early.

---

## Lesson 10: Validation happens in layers

Take "safety must be 1 to 10". It is checked three times:

1. **HTML:** `<input min="1" max="10">` gives quick feedback, but it is easy to bypass.
2. **Python:** `api_update_road` rejects it with a `400` error. This is the real check.
3. **Database:** `CHECK (safety BETWEEN 1 AND 10)` is the last line of defence.

---

## Lesson 11: Real maps and real data (`static/map.js`, `tools/build_mumbai.py`)

The map is built from three layers:

| Layer | Where it comes from |
|---|---|
| Background streets (the "tiles") | OpenStreetMap, loaded by the **browser** straight from `tile.openstreetmap.org` |
| Your graph: 24 places and 40 roads | Your database, sent by `/api/map` |
| The highlighted route | Your Dijkstra result from `/api/routes` |

**Leaflet** is the JavaScript library that shows the tiles, lets you zoom and drag, and draws lines (`L.polyline`) and dots (`L.circleMarker`) on top.

**Coordinates.** Each place is a point `(latitude, longitude)`. Latitude is north–south (Mumbai ≈ 19), longitude is east–west (Mumbai ≈ 72.8). Watch out: GeoJSON and OSRM write points as `[lng, lat]`, while Leaflet wants `[lat, lng]`. Mixing them up puts Mumbai in the Indian Ocean near Antarctica. `build_mumbai.py` swaps them.

**Where the road data came from.** `tools/build_mumbai.py` was run once. For each road it asked the free OSRM routing service for the real street shape, distance and empty-road driving time, then wrote everything into `mumbai_data.py`. Travel time = OSRM time × 2 to allow for traffic. That's a rough estimate, which is fine for a demo.

**Safety scores are made up.** They are demo numbers the admin can change, not real crime or accident data. If you present this project, say so. Real sources could be police accident statistics, street-lighting data, or user reports.

**The graph is still small on purpose.** The real Mumbai street network has hundreds of thousands of road segments. Ours has 40 hand-picked corridors, so an admin can actually score every road, and you can follow Dijkstra by hand.

**Try it.**
1. Open http://127.0.0.1:5000/api/map and find a road's `shape`. Paste a couple of its `[lat, lng]` points into Google Maps search.
2. On the admin page, drop the **Bandra–Worli Sea Link** safety to 2 and see how the safest route from Mumbai Central to Andheri changes.
3. Add a place: add it to `PLACES` and a road to `ROADS` in `tools/build_mumbai.py`, run `python tools/build_mumbai.py`, then `python load_map.py`. (Loading the map resets road edits but keeps users.)

---

## Exercises (easiest first)

1. **Change the look.** Edit a colour in `static/style.css` (for example `--safe`) and refresh.
2. **Show the user count on the admin page.** Add `SELECT COUNT(*) FROM users` in the `admin()` route, pass it with `render_template("admin.html", user_count=...)`, and show `{{ user_count }}` in the template.
3. **Add a new place.** Insert a row into `locations` and a road into `roads` using `sqlite3`, then refresh. Can you reach it?
4. **Users table for admins.** Add `GET /api/users` (admin only) and list usernames and roles on the admin page.
5. **Faster Dijkstra.** Rewrite the `min(...)` step in `routing.py` with Python's `heapq` (a priority queue). Then run `python test_routing.py`.
6. **Saved trips.** Create a `trips` table (`user_id`, `from_id`, `to_id`, `created_at`), save each search and show "Your recent trips".
7. **Change password page.** Check the old password, hash the new one, `UPDATE users`.

---

## Before putting this on the internet

This app is built to learn with, on your own computer. A public site would also need:

- **HTTPS**, so passwords aren't sent in plain text over the network.
- **CSRF protection** on forms (for example the `Flask-WTF` package).
- **Rate limiting** on `/login`, to slow down password guessing.
- A real server (`gunicorn`) instead of `flask run`, with debug mode **off**.

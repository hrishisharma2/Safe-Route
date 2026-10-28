"""
SafeRoute web server (Flask).

Pages (HTML):          /  (public home)  /login  /register  /logout  /plan  (user)  /admin
API (JSON for JS):     GET /api/map   GET /api/routes   PUT /api/roads/<id>   POST /api/roads/reset

Start it with:  flask --app app run --debug
"""
import json
import os
import secrets
import sqlite3
from functools import wraps

from flask import (Flask, abort, flash, g, jsonify, redirect, render_template,
                   request, session, url_for)
from werkzeug.security import check_password_hash, generate_password_hash

from routing import find_route
from seed_data import load_demo_map

app = Flask(__name__)
os.makedirs(app.instance_path, exist_ok=True)


def load_secret_key():
    """The secret key signs the session cookie so users cannot fake being logged in.
    We generate a random one the first time and keep it in instance/secret_key."""
    path = os.path.join(app.instance_path, "secret_key")
    if not os.path.exists(path):
        with open(path, "w") as f:
            f.write(secrets.token_hex(32))
    with open(path) as f:
        return f.read().strip()


app.config.update(
    # SAFEROUTE_DB lets tests point the app at a separate database file.
    DATABASE=os.environ.get("SAFEROUTE_DB", os.path.join(app.instance_path, "saferoute.db")),
    SECRET_KEY=load_secret_key(),
    SESSION_COOKIE_HTTPONLY=True,   # JavaScript cannot read the session cookie
    SESSION_COOKIE_SAMESITE="Lax",  # other websites cannot send requests with it
    # On a live HTTPS site, set SAFEROUTE_HTTPS=1 so the cookie is only sent over HTTPS.
    SESSION_COOKIE_SECURE=os.environ.get("SAFEROUTE_HTTPS") == "1",
)


# ---------------------------------------------------------------- database

def get_db():
    """One database connection per request, stored on Flask's `g` object."""
    if "db" not in g:
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row          # rows behave like dicts: row["name"]
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ---------------------------------------------------------------- who is logged in?

@app.before_request
def load_logged_in_user():
    """Runs before every request. Looks up the user id stored in the session cookie."""
    user_id = session.get("user_id")
    g.user = None
    if user_id is not None:
        g.user = get_db().execute(
            "SELECT id, username, role FROM users WHERE id = ?", (user_id,)
        ).fetchone()


def login_required(view):
    """Decorator: put @login_required above a route to make it members-only."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            if request.path.startswith("/api/"):
                return jsonify(error="Please log in."), 401
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    """Decorator: logged in AND role is 'admin'."""
    @wraps(view)
    @login_required
    def wrapped(*args, **kwargs):
        if g.user["role"] != "admin":
            if request.path.startswith("/api/"):
                return jsonify(error="Only admins can do this."), 403
            abort(403)
        return view(*args, **kwargs)
    return wrapped


# ---------------------------------------------------------------- login / register

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        error = None
        if not username or len(username) > 30:
            error = "Choose a username of 1 to 30 characters."
        elif len(password) < 6:
            error = "Password must be at least 6 characters."

        if error is None:
            try:
                get_db().execute(
                    "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                    (username, generate_password_hash(password)),
                )
                get_db().commit()
            except sqlite3.IntegrityError:          # UNIQUE constraint on username
                error = f"The username '{username}' is already taken."
            else:
                flash("Account created. You can log in now.")
                return redirect(url_for("login"))
        flash(error, "error")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT * FROM users WHERE username = ?", (username,)
        ).fetchone()

        # Same message for both cases, so attackers can't tell which usernames exist.
        if user is None or not check_password_hash(user["password_hash"], password):
            flash("Wrong username or password.", "error")
        else:
            session.clear()
            session["user_id"] = user["id"]
            next_page = request.args.get("next", "")
            if not next_page.startswith("/") or next_page.startswith("//"):
                next_page = url_for("admin" if user["role"] == "admin" else "index")
            return redirect(next_page)
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


# ---------------------------------------------------------------- pages

@app.route("/")
def home():
    """Public landing page. Logged-in users see a shortcut to the planner."""
    locations, roads = read_map()
    return render_template("home.html", n_places=len(locations), n_roads=len(roads))


@app.route("/plan")
@login_required
def index():
    return render_template("index.html")


@app.route("/admin")
@admin_required
def admin():
    return render_template("admin.html")


# ---------------------------------------------------------------- JSON API

def read_map(with_shapes=False):
    db = get_db()
    locations = [dict(r) for r in db.execute("SELECT id, name, lat, lng FROM locations ORDER BY id")]
    roads = [dict(r) for r in db.execute("""
        SELECT roads.id, from_id, to_id, roads.name, km, time, safety, shape,
               updated_at, users.username AS updated_by
        FROM roads LEFT JOIN users ON users.id = roads.updated_by
        ORDER BY roads.id""")]
    for r in roads:
        # The shape is stored as JSON text; the browser only needs it to draw the map.
        shape = r.pop("shape")
        if with_shapes:
            r["shape"] = json.loads(shape)
    return locations, roads


@app.get("/api/map")
@login_required
def api_map():
    locations, roads = read_map(with_shapes=True)
    return jsonify(locations=locations, roads=roads)


@app.get("/api/routes")
@login_required
def api_routes():
    """Example: /api/routes?from=0&to=9&w=0.5"""
    locations, roads = read_map()
    ids = [loc["id"] for loc in locations]
    src = request.args.get("from", type=int)
    dst = request.args.get("to", type=int)
    w = request.args.get("w", default=0.5, type=float)
    if src not in ids or dst not in ids or w is None or not 0 <= w <= 1:
        return jsonify(error="Send valid 'from' and 'to' location ids and 'w' between 0 and 1."), 400

    return jsonify(
        preferred=find_route(ids, roads, src, dst, w),
        fastest=find_route(ids, roads, src, dst, 1.0),
        balanced=find_route(ids, roads, src, dst, 0.5),
        safest=find_route(ids, roads, src, dst, 0.0),
    )


@app.put("/api/roads/<int:road_id>")
@admin_required
def api_update_road(road_id):
    data = request.get_json(silent=True) or {}
    time, safety = data.get("time"), data.get("safety")
    if not isinstance(time, int) or isinstance(time, bool) or not 1 <= time <= 999:
        return jsonify(error="Time must be a whole number of minutes from 1 to 999."), 400
    if not isinstance(safety, int) or isinstance(safety, bool) or not 1 <= safety <= 10:
        return jsonify(error="Safety must be a whole number from 1 to 10."), 400

    db = get_db()
    cur = db.execute(
        "UPDATE roads SET time = ?, safety = ?, updated_by = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
        (time, safety, g.user["id"], road_id),
    )
    db.commit()
    if cur.rowcount == 0:
        return jsonify(error="That road does not exist."), 404
    return jsonify(ok=True)


@app.post("/api/roads/reset")
@admin_required
def api_reset_roads():
    load_demo_map(get_db())
    return jsonify(ok=True)


@app.errorhandler(403)
def forbidden(error):
    return render_template("403.html"), 403

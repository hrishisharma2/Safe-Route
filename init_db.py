"""
Create the database, load the demo map and create the first admin account.

Run once:   python init_db.py
"""
import os
import sqlite3
import getpass

from werkzeug.security import generate_password_hash

from seed_data import load_demo_map

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "instance", "saferoute.db")


def main():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

    if os.path.exists(DB_PATH):
        answer = input("A database already exists. Delete it and start fresh? (yes/no): ")
        if answer.strip().lower() != "yes":
            print("Nothing changed.")
            return

    conn = sqlite3.connect(DB_PATH)
    with open(os.path.join(BASE_DIR, "schema.sql")) as f:
        conn.executescript(f.read())
    load_demo_map(conn)
    print(f"Created tables and loaded the demo map into {DB_PATH}")

    # Create the admin. getpass hides the password while you type it.
    username = input("Admin username [admin]: ").strip() or "admin"
    while True:
        password = getpass.getpass("Admin password (at least 6 characters): ")
        if len(password) < 6:
            print("Too short, try again.")
        elif password != getpass.getpass("Type it again: "):
            print("Passwords did not match, try again.")
        else:
            break

    conn.execute(
        "INSERT INTO users (username, password_hash, role) VALUES (?, ?, 'admin')",
        (username, generate_password_hash(password)),
    )
    conn.commit()
    conn.close()
    print(f"Admin '{username}' created. Start the app with: flask --app app run --debug")


if __name__ == "__main__":
    main()

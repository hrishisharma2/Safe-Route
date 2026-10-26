# Publish SafeRoute for free

You will put the code on **GitHub**, then run it on **PythonAnywhere**. Your site will be at:

```
https://YOURNAME.pythonanywhere.com
```

Why PythonAnywhere? The free plan runs Flask and its disk is **permanent**, so your SQLite database (users and roads) survives restarts. Many other free hosts wipe the disk on every restart, which would delete every account.

**Free plan limits:** one web app, 512 MB of disk, and limited CPU time. The site **stops after 1 month** unless you click a button to extend it (step 5). That's plenty for a project demo.

Throughout this guide, replace `YOURNAME` with your PythonAnywhere username and `GITHUBNAME` with your GitHub username.

---

## The idea: how deployment works

```
Your Mac ──git push──▶ GitHub ──git clone / git pull──▶ PythonAnywhere server ──▶ the internet
```

- **Git** tracks versions of your code.
- **GitHub** stores a copy online so other computers can download it.
- **PythonAnywhere** is a computer in a data centre that runs your Flask app day and night.

Your Mac never talks to PythonAnywhere directly. GitHub is the middle step.

Locally you ran `flask run`. That's a development server and isn't meant for the public. On PythonAnywhere, a production web server loads your app through a small **WSGI file** (step 4). WSGI is the standard way Python web servers start Python web apps.

---

## Step 1: Save your code with Git (on your Mac)

```bash
cd ~/code/tii/webapp
git init                      # start tracking this folder
git add .                     # stage every file (.gitignore skips the secret ones)
git status                    # CHECK: instance/ and .venv/ must NOT be listed
git commit -m "SafeRoute web app"
git branch -M main
```

**Why `.gitignore` matters:** `instance/` contains your database with password hashes and the secret key that signs login cookies. These must never go on GitHub. The server creates its own copies.

If Git asks who you are the first time:
```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

## Step 2: Put the code on GitHub

1. Sign up at https://github.com, then click **New repository**.
2. Name it `saferoute`, choose **Public**, and don't tick any "Add README" options. Click **Create repository**.
3. Back in your terminal:
   ```bash
   git remote add origin https://github.com/GITHUBNAME/saferoute.git
   git push -u origin main
   ```
4. When asked for a password, GitHub needs a **token**, not your account password. Create one at GitHub → Settings → Developer settings → Personal access tokens → **Tokens (classic)** → Generate, with the `repo` box ticked. Paste the token as the password. It won't show as you type.

Refresh the GitHub page and your files should appear.

> **Want to skip GitHub?** Zip the `webapp` folder **without** `.venv` and `instance`, upload it in PythonAnywhere's **Files** tab, then run `unzip` in a console. Git is worth learning, though, because updating the site later is much easier with it.

## Step 3: Set up the server (on PythonAnywhere)

1. Sign up for a free **Beginner** account at https://www.pythonanywhere.com.
2. Open **Consoles → Bash**. This is a terminal running on their server, not on your Mac.
3. Download your code and install Flask:
   ```bash
   git clone https://github.com/GITHUBNAME/saferoute.git
   cd saferoute
   python3 --version                       # note this version, e.g. 3.13
   python3 -m venv .venv
   .venv/bin/pip install -r requirements.txt
   ```
4. Create the **live** database and admin account:
   ```bash
   .venv/bin/python init_db.py
   ```
   Use a **strong, new password** here. This site is on the internet, so anyone can try to log in.

## Step 4: Create the web app

1. Go to the **Web** tab → **Add a new web app** → Next.
2. Choose **Manual configuration** (not "Flask"). Pick the **same Python version** you saw in step 3.
3. On the web app's settings page, fill in these sections:

   **Virtualenv**
   ```
   /home/YOURNAME/saferoute/.venv
   ```

   **Static files** (lets the server send CSS/JS directly, which is faster)
   | URL | Directory |
   |---|---|
   | `/static/` | `/home/YOURNAME/saferoute/static` |

   **Security:** turn on **Force HTTPS**.

4. **WSGI configuration file:** click the link to edit it. Delete **everything** in it and paste:
   ```python
   import os
   import sys

   project = "/home/YOURNAME/saferoute"
   if project not in sys.path:
       sys.path.insert(0, project)

   # The site uses HTTPS, so only send the login cookie over HTTPS.
   os.environ["SAFEROUTE_HTTPS"] = "1"

   from app import app as application   # the server looks for a variable named "application"
   ```
   Click **Save**.

5. Go back to the **Web** tab, press the green **Reload** button, and open `https://YOURNAME.pythonanywhere.com`.

You should see the login page. Log in with the admin account from step 3.

## Step 5: Keep it running

Free web apps stop after one month. Log in once a month, go to the **Web** tab and click **"Run until 1 month from today"**. PythonAnywhere emails you before it expires.

---

## Updating the site after you change code

Make your change on your Mac and test it locally first. Then:

```bash
# On your Mac
git add .
git commit -m "Describe what you changed"
git push
```
```bash
# In a PythonAnywhere Bash console
cd ~/saferoute
git pull
```
Then press **Reload** on the Web tab.

If you add a new package to `requirements.txt`, also run `.venv/bin/pip install -r requirements.txt` on the server before reloading.

Your users and roads are **not** affected by updates. They live in `instance/saferoute.db` on the server, which Git never touches.

**If you change the map data** (`mumbai_data.py`), run `.venv/bin/python load_map.py` on the server after `git pull`. It replaces the map but keeps every user account.

**Map tiles:** the background map loads in each visitor's browser directly from OpenStreetMap, so PythonAnywhere's internet restrictions don't affect it. OpenStreetMap's free tiles are meant for light use, which a class project is. A busy public site should switch to a paid tile provider.

**Don't run `init_db.py` again on the server.** It deletes all accounts. It asks you to type "yes" first, so read the prompt carefully.

---

## When something goes wrong

| What you see | What to check |
|---|---|
| "Something went wrong :-(" | **Web tab → Error log** (scroll to the bottom). It shows the real Python error. |
| `ModuleNotFoundError: No module named 'flask'` | Virtualenv path is wrong, or Flask was not installed into `.venv` |
| `ModuleNotFoundError: No module named 'app'` | `project` path in the WSGI file is wrong. Check your username spelling. |
| `no such table: users` | You skipped `init_db.py`, or ran it in a different folder |
| Page loads but has no styling | Static files mapping is wrong |
| Changes don't appear | You forgot `git pull` or the **Reload** button |
| Can't stay logged in | You opened the `http://` address. Use `https://` (Force HTTPS fixes this). |

The **Error log** is the most useful tool. Learning to read error logs is a big part of real deployment work.

---

## What you learned

- **Version control** (git commit / push / pull)
- **Keeping secrets out of code** (`.gitignore`, a separate production database and secret key)
- **Development vs production** (`flask run --debug` vs a WSGI server, HTTPS, secure cookies)
- **Servers and logs** (a remote Bash console, reading error logs)

---

## Next steps for a real public site

Before inviting lots of strangers, consider these:
- Limit login attempts (the `Flask-Limiter` package) so nobody can guess passwords quickly.
- Add CSRF protection to forms (`Flask-WTF`).
- Back up the database now and then: download `instance/saferoute.db` from the **Files** tab.

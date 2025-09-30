from flask import Flask, request, render_template, redirect, url_for, session, make_response, send_from_directory, abort
import sqlite3, os, subprocess, requests, hashlib, re
from datetime import timedelta

app = Flask(__name__)
app.secret_key = "super-insecure-hardcoded-secret"
app.permanent_session_lifetime = timedelta(minutes=120)

DB = "insecure.db"
UPLOAD_DIR = os.path.join("static", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

def init_db():
    con = get_db()
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE, password_md5 TEXT, is_admin INTEGER DEFAULT 0, bio TEXT DEFAULT '')")
    cur.execute("CREATE TABLE IF NOT EXISTS comments (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, content TEXT)")
    cur.execute("CREATE TABLE IF NOT EXISTS secrets (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, note TEXT)")
    con.commit()

    # Seed a few users (weak MD5 password hashing)
    def md5(s): return hashlib.md5(s.encode()).hexdigest()
    try:
        cur.execute("INSERT INTO users (username, password_md5, is_admin, bio) VALUES (?,?,?,?)", ("admin", md5("admin123"), 1, "I am the admin. <script>alert('admin xss')</script>"))
        cur.execute("INSERT INTO users (username, password_md5, is_admin, bio) VALUES (?,?,?,?)", ("alice", md5("password"), 0, "Hi, I'm Alice."))
        cur.execute("INSERT INTO users (username, password_md5, is_admin, bio) VALUES (?,?,?,?)", ("bob", md5("123456"), 0, "Hey there, I'm Bob."))
        # Secrets (IDOR challenge)
        cur.execute("INSERT INTO secrets (user_id, note) VALUES (?,?)", (2, "Alice secret: FLAG{IDOR_LEAK_ALICE}"))
        cur.execute("INSERT INTO secrets (user_id, note) VALUES (?,?)", (3, "Bob secret: FLAG{IDOR_LEAK_BOB}"))
        con.commit()
    except sqlite3.IntegrityError:
        pass

init_db()

# Home
@app.route("/")
def index():
    q = request.args.get("q", "")
    # Reflected XSS via search parameter
    return render_template("index.html", q=q)

# Registration (no CSRF, weak password checks)
@app.route("/register", methods=["GET", "POST"])
def register():
    msg = ""
    if request.method == "POST":
        username = request.form.get("username","")
        password = request.form.get("password","")
        if not username or not password:
            msg = "username & password required"
        else:
            con = get_db()
            try:
                md5 = hashlib.md5(password.encode()).hexdigest()
                con.execute(f"INSERT INTO users (username, password_md5) VALUES ('{username}','{md5}')")  # SQLi in values if username contains quotes
                con.commit()
                msg = "Registered. Please login."
            except Exception as e:
                msg = f"Error: {e}"
    return render_template("register.html", msg=msg)

# Login (SQLi in WHERE clause)
@app.route("/login", methods=["GET","POST"])
def login():
    error = ""
    if request.method == "POST":
        username = request.form.get("username","")
        password = request.form.get("password","")
        md5 = hashlib.md5(password.encode()).hexdigest()

        con = get_db()
        # Intentional SQL Injection vulnerability
        query = f"SELECT id, username, is_admin FROM users WHERE username = '{username}' AND password_md5 = '{md5}'"
        try:
            row = con.execute(query).fetchone()
        except Exception as e:
            error = f"SQL error: {e}"
            row = None
        if row:
            session["user_id"] = row["id"]
            session["username"] = row["username"]
            session["is_admin"] = row["is_admin"]
            resp = make_response(redirect(url_for("dashboard")))
            # Insecure cookie (no HttpOnly/Secure flags)
            resp.set_cookie("last_login_user", row["username"])
            return resp
        else:
            error = "Invalid credentials (or try SQLi?)"
    return render_template("login.html", error=error)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

# Dashboard (stored XSS via comments)
@app.route("/dashboard", methods=["GET","POST"])
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))
    con = get_db()
    msg = ""
    if request.method == "POST":
        content = request.form.get("content","")
        # No sanitization -> stored XSS
        con.execute("INSERT INTO comments (user_id, content) VALUES (?,?)", (session["user_id"], content))
        con.commit()
        msg = "Posted!"
    comments = con.execute("SELECT c.id, u.username, c.content FROM comments c LEFT JOIN users u ON u.id=c.user_id ORDER BY c.id DESC").fetchall()
    return render_template("dashboard.html", comments=comments, msg=msg)

# Profile (IDOR - access by id param)
@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))
    # IDOR: user can change ?id= to view others' profiles
    user_id = request.args.get("id", session["user_id"])
    con = get_db()
    user = con.execute(f"SELECT id, username, bio FROM users WHERE id = {user_id}").fetchone()  # vulnerable
    secret = con.execute(f"SELECT note FROM secrets WHERE user_id = {user_id}").fetchone()
    return render_template("profile.html", user=user, secret=secret["note"] if secret else None)

# Insecure file upload (XSS via uploaded HTML/JS; path traversal risk if filename crafted)
@app.route("/upload", methods=["GET","POST"])
def upload():
    if "user_id" not in session:
        return redirect(url_for("login"))
    msg = ""
    if request.method == "POST":
        f = request.files.get("file")
        if f and f.filename:
            # No sanitization of filename; saves anywhere under uploads if path contains slashes
            save_path = os.path.join(UPLOAD_DIR, f.filename)
            f.save(save_path)
            msg = f"Uploaded to /{save_path}"
        else:
            msg = "No file"
    files = os.listdir(UPLOAD_DIR)
    return render_template("upload.html", files=files, msg=msg)

@app.route("/static/uploads/<path:filename>")
def serve_upload(filename):
    return send_from_directory(UPLOAD_DIR, filename)

# Command injection (ping)
@app.route("/ping", methods=["GET","POST"])
def ping():
    output = ""
    target = request.values.get("target","")
    if target:
        # Dangerous: shell=True + unsanitized input
        try:
            output = subprocess.check_output(f"ping -c 1 {target}", shell=True, stderr=subprocess.STDOUT, timeout=5).decode()
        except Exception as e:
            output = str(e)
    return render_template("ping.html", output=output)

# SSRF: fetch any URL
@app.route("/fetch", methods=["GET","POST"])
def fetch():
    body = ""
    url = request.values.get("url","")
    if url:
        try:
            r = requests.get(url, timeout=5, verify=False)
            body = r.text[:2000]
        except Exception as e:
            body = f"Fetch error: {e}"
    return render_template("fetch.html", body=body)

# Admin panel (IDOR authz bypass via is_admin in session; also weak check via query param)
@app.route("/admin")
def admin():
    admin_override = request.args.get("admin","0")
    if (session.get("is_admin") != 1) and admin_override != "1":
        return abort(403)
    con = get_db()
    users = con.execute("SELECT id, username, is_admin FROM users").fetchall()
    return render_template("admin.html", users=users)

# Security headers intentionally weak/missing
@app.after_request
def add_headers(resp):
    # Intentionally misconfigured headers to allow XSS/iframes
    resp.headers["X-Frame-Options"] = "ALLOWALL"
    return resp

if __name__ == "__main__":
    # Debug on to leak stack traces
    app.run(host="0.0.0.0", port=5000, debug=True)

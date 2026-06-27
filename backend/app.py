from flask import Flask, request, jsonify, session, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
import mysql.connector
import os
import secrets

app = Flask(__name__, static_folder="frontend", static_url_path="")
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# ── MySQL Configuration ───────────────────────────────────────
DB_CONFIG = {
    "host":     os.environ.get("DB_HOST", "localhost"),
    "user":     os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "root123"),
    "database": os.environ.get("DB_NAME", "votebox"),
}

# ── Input validation limits ────────────────────────────────────
MAX_USERNAME_LEN = 50
MAX_PASSWORD_LEN = 128
MAX_TITLE_LEN = 100
MAX_DESC_LEN = 500
MAX_CANDIDATE_NAME_LEN = 100
MAX_CANDIDATES = 20
DEFAULT_PAGE_SIZE = 20

# ── DB Helper ──────────────────────────────────────────────────
def get_db():
    conn = mysql.connector.connect(**DB_CONFIG)
    return conn

def dict_cursor(conn):
    """Return a cursor that returns rows as dictionaries."""
    return conn.cursor(dictionary=True)

# ── Auth Helpers ───────────────────────────────────────────────
def current_user():
    if "user_id" not in session:
        return None
    conn = get_db()
    cur = dict_cursor(conn)
    # QUERY 1 – fetch logged-in user by primary key
    cur.execute("SELECT * FROM user WHERE id = %s", (session["user_id"],))
    user = cur.fetchone()
    cur.close()
    conn.close()
    return user

def log_audit(cur, admin_id, action, target_id=None, detail=""):
    # QUERY 2 – insert audit log entry
    cur.execute(
        "INSERT INTO audit_log (admin_id, action, target_id, detail) VALUES (%s, %s, %s, %s)",
        (admin_id, action, target_id, detail)
    )

# ── CSRF Protection ────────────────────────────────────────────
def generate_csrf_token():
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_hex(32)
        session.modified = True
    return session["csrf_token"]

def validate_csrf():
    token = request.headers.get("X-CSRF-Token") or (request.get_json() or {}).get("_csrf_token")
    if not token or token != session.get("csrf_token"):
        return False
    return True

@app.before_request
def csrf_protect():
    if request.method in ("POST", "PUT", "DELETE", "PATCH"):
        if request.path.startswith("/api/"):
            if not validate_csrf():
                return jsonify({"error": "CSRF token missing or invalid"}), 403

@app.get("/api/csrf-token")
def get_csrf_token():
    return jsonify({"csrf_token": generate_csrf_token()})

# ══════════════════════════════════════════════════════════════
#  AUTH
# ══════════════════════════════════════════════════════════════

@app.post("/api/register")
def register():
    d = request.get_json()
    username = d.get("username", "").strip()
    password = d.get("password", "")
    if not username or not password:
        return jsonify({"error": "Username and password required"}), 400
    if len(username) > MAX_USERNAME_LEN:
        return jsonify({"error": f"Username must be {MAX_USERNAME_LEN} characters or fewer"}), 400
    if len(password) > MAX_PASSWORD_LEN:
        return jsonify({"error": f"Password must be {MAX_PASSWORD_LEN} characters or fewer"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    conn = get_db()
    cur = dict_cursor(conn)
    try:
        # QUERY 3 – insert new user
        cur.execute("INSERT INTO user (username, password) VALUES (%s, %s)",
                   (username, generate_password_hash(password)))
        conn.commit()
    except mysql.connector.IntegrityError:
        return jsonify({"error": "Username already taken"}), 400
    finally:
        cur.close()
        conn.close()
    return jsonify({"message": "Account created! Please log in."})


@app.post("/api/login")
def login():
    d = request.get_json()
    conn = get_db()
    cur = dict_cursor(conn)
    # QUERY 4 – look up user by username for login
    cur.execute("SELECT * FROM user WHERE username = %s", (d.get("username"),))
    user = cur.fetchone()
    cur.close()
    conn.close()
    if not user or not check_password_hash(user["password"], d.get("password", "")):
        return jsonify({"error": "Invalid username or password"}), 401
    session["user_id"] = user["id"]
    return jsonify({"message": "Logged in!", "user": {
        "id": user["id"], "username": user["username"], "is_admin": bool(user["is_admin"])
    }})


@app.post("/api/logout")
def logout():
    session.clear()
    return jsonify({"message": "Logged out"})


@app.get("/api/me")
def me():
    user = current_user()   # uses QUERY 1
    if not user:
        return jsonify({"logged_in": False})
    return jsonify({"logged_in": True, "user": {
        "id": user["id"], "username": user["username"], "is_admin": bool(user["is_admin"])
    }})


# ══════════════════════════════════════════════════════════════
#  ELECTIONS
# ══════════════════════════════════════════════════════════════

@app.get("/api/elections")
def get_elections():
    user = current_user()
    if not user:
        return jsonify({"error": "Login required"}), 401
    # Pagination support
    page = request.args.get("page", 1, type=int)
    limit = request.args.get("limit", DEFAULT_PAGE_SIZE, type=int)
    limit = min(limit, 100)  # cap at 100
    offset = (page - 1) * limit
    conn = get_db()
    cur = dict_cursor(conn)
    # QUERY 5 – list elections via summary view with pagination
    cur.execute(
        "SELECT * FROM v_election_summary ORDER BY id DESC LIMIT %s OFFSET %s",
        (limit, offset)
    )
    elections = cur.fetchall()
    cur.execute("SELECT COUNT(*) as c FROM election")
    total_count = cur.fetchone()["c"]
    result = []
    for e in elections:
        # QUERY 6 – check if this user has voted in each election
        cur.execute(
            "SELECT 1 FROM vote WHERE user_id = %s AND election_id = %s",
            (user["id"], e["id"])
        )
        has_voted = cur.fetchone() is not None
        result.append({
            "id": e["id"], "title": e["title"],
            "description": e["description"], "is_open": bool(e["is_open"]),
            "has_voted": has_voted,
            "candidate_count": e["candidate_count"],
            "total_votes": e["total_votes"]
        })
    cur.close()
    conn.close()
    return jsonify({"elections": result, "total": total_count, "page": page, "limit": limit})


@app.get("/api/elections/<int:eid>")
def get_election(eid):
    user = current_user()
    if not user:
        return jsonify({"error": "Login required"}), 401
    conn = get_db()
    cur = dict_cursor(conn)
    # QUERY 7 – fetch single election by id
    cur.execute("SELECT * FROM election WHERE id = %s", (eid,))
    e = cur.fetchone()
    if not e:
        return jsonify({"error": "Election not found"}), 404
    # QUERY 8 – fetch candidates for this election
    cur.execute(
        "SELECT id, name FROM candidate WHERE election_id = %s ORDER BY id", (eid,)
    )
    candidates = cur.fetchall()
    # QUERY 9 – check if user already voted and which candidate
    cur.execute(
        "SELECT candidate_id FROM vote WHERE user_id = %s AND election_id = %s",
        (user["id"], eid)
    )
    voted = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify({
        "id": e["id"], "title": e["title"],
        "description": e["description"], "is_open": bool(e["is_open"]),
        "has_voted": voted is not None,
        "voted_candidate_id": voted["candidate_id"] if voted else None,
        "candidates": [{"id": c["id"], "name": c["name"]} for c in candidates]
    })


@app.post("/api/elections")
def create_election():
    user = current_user()
    if not user:           return jsonify({"error": "Login required"}), 401
    if not user["is_admin"]: return jsonify({"error": "Admin only"}), 403
    d = request.get_json()
    title      = d.get("title", "").strip()
    description = d.get("description", "").strip()
    candidates = [c.strip() for c in d.get("candidates", []) if c.strip()]
    if not title:            return jsonify({"error": "Title required"}), 400
    if len(title) > MAX_TITLE_LEN:
        return jsonify({"error": f"Title must be {MAX_TITLE_LEN} characters or fewer"}), 400
    if len(description) > MAX_DESC_LEN:
        return jsonify({"error": f"Description must be {MAX_DESC_LEN} characters or fewer"}), 400
    if len(candidates) < 2:  return jsonify({"error": "At least 2 candidates required"}), 400
    if len(candidates) > MAX_CANDIDATES:
        return jsonify({"error": f"Maximum {MAX_CANDIDATES} candidates allowed"}), 400
    for c in candidates:
        if len(c) > MAX_CANDIDATE_NAME_LEN:
            return jsonify({"error": f"Candidate name must be {MAX_CANDIDATE_NAME_LEN} characters or fewer"}), 400
    conn = get_db()
    cur = dict_cursor(conn)
    # QUERY 10 – insert new election
    cur.execute(
        "INSERT INTO election (title, description) VALUES (%s, %s)",
        (title, description)
    )
    eid = cur.lastrowid
    # QUERY 11 – bulk-insert candidates
    for name in candidates:
        cur.execute("INSERT INTO candidate (name, election_id) VALUES (%s, %s)", (name, eid))
    log_audit(cur, user["id"], "create_election", eid, title)   # uses QUERY 2
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": "Election created!", "id": eid}), 201


@app.post("/api/elections/<int:eid>/toggle")
def toggle_election(eid):
    user = current_user()
    if not user:           return jsonify({"error": "Login required"}), 401
    if not user["is_admin"]: return jsonify({"error": "Admin only"}), 403
    conn = get_db()
    cur = dict_cursor(conn)
    # QUERY 12 – read current open/close state
    cur.execute("SELECT is_open, title FROM election WHERE id = %s", (eid,))
    e = cur.fetchone()
    if not e:
        cur.close()
        conn.close()
        return jsonify({"error": "Not found"}), 404
    new_state = 0 if e["is_open"] else 1
    # QUERY 13 – update election open/close state
    cur.execute("UPDATE election SET is_open = %s WHERE id = %s", (new_state, eid))
    action = "reopen_election" if new_state else "close_election"
    log_audit(cur, user["id"], action, eid, e["title"])
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"is_open": bool(new_state)})


@app.delete("/api/elections/<int:eid>")
def delete_election(eid):
    user = current_user()
    if not user:           return jsonify({"error": "Login required"}), 401
    if not user["is_admin"]: return jsonify({"error": "Admin only"}), 403
    conn = get_db()
    cur = dict_cursor(conn)
    cur.execute("SELECT title FROM election WHERE id = %s", (eid,))
    e = cur.fetchone()
    if not e:
        cur.close()
        conn.close()
        return jsonify({"error": "Not found"}), 404
    log_audit(cur, user["id"], "delete_election", eid, e["title"])
    # QUERY 14 – delete election (cascades to candidates + votes via FK)
    cur.execute("DELETE FROM election WHERE id = %s", (eid,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": "Deleted"})


# ══════════════════════════════════════════════════════════════
#  VOTES
# ══════════════════════════════════════════════════════════════

@app.post("/api/vote")
def cast_vote():
    user = current_user()
    if not user:
        return jsonify({"error": "Login required"}), 401
    d = request.get_json()
    conn = get_db()
    cur = dict_cursor(conn)
    try:
        # Use transaction to prevent race conditions
        conn.start_transaction()
        # QUERY 15 – validate election exists and is open
        cur.execute("SELECT * FROM election WHERE id = %s FOR UPDATE", (d.get("election_id"),))
        e = cur.fetchone()
        if not e:
            conn.rollback()
            return jsonify({"error": "Election not found"}), 404
        if not e["is_open"]:
            conn.rollback()
            return jsonify({"error": "This election is closed"}), 400
        # QUERY 16 – validate candidate belongs to this election
        cur.execute(
            "SELECT id FROM candidate WHERE id = %s AND election_id = %s",
            (d.get("candidate_id"), e["id"])
        )
        c = cur.fetchone()
        if not c:
            conn.rollback()
            return jsonify({"error": "Invalid candidate"}), 400
        # QUERY 17 – insert vote (UNIQUE constraint also prevents duplicates)
        cur.execute(
            "INSERT INTO vote (user_id, election_id, candidate_id) VALUES (%s, %s, %s)",
            (user["id"], e["id"], c["id"])
        )
        conn.commit()
    except mysql.connector.IntegrityError:
        conn.rollback()
        return jsonify({"error": "You already voted in this election"}), 400
    finally:
        cur.close()
        conn.close()
    return jsonify({"message": "Vote cast!"})


@app.get("/api/elections/<int:eid>/results")
def results(eid):
    user = current_user()
    if not user:
        return jsonify({"error": "Login required"}), 401
    conn = get_db()
    cur = dict_cursor(conn)
    cur.execute("SELECT title FROM election WHERE id = %s", (eid,))
    e = cur.fetchone()
    if not e:
        return jsonify({"error": "Not found"}), 404
    # QUERY 18 – count total votes for this election
    cur.execute(
        "SELECT COUNT(*) as c FROM vote WHERE election_id = %s", (eid,)
    )
    total = cur.fetchone()["c"]
    # QUERY 19 – ranked results using candidate tallies view
    cur.execute(
        "SELECT candidate_name, vote_count FROM v_candidate_tallies WHERE election_id = %s ORDER BY vote_count DESC",
        (eid,)
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({
        "title": e["title"],
        "total": total,
        "results": [{
            "name": r["candidate_name"],
            "votes": r["vote_count"],
            "percent": round(r["vote_count"] / total * 100) if total else 0
        } for r in rows]
    })


# ══════════════════════════════════════════════════════════════
#  ADMIN — USERS
# ══════════════════════════════════════════════════════════════

@app.get("/api/admin/users")
def list_users():
    user = current_user()
    if not user:           return jsonify({"error": "Login required"}), 401
    if not user["is_admin"]: return jsonify({"error": "Admin only"}), 403
    conn = get_db()
    cur = dict_cursor(conn)
    # QUERY 20 – list all users with their vote count
    cur.execute("""
        SELECT u.id, u.username, u.is_admin, u.created_at,
               COUNT(v.id) AS total_votes
        FROM user u
        LEFT JOIN vote v ON v.user_id = u.id
        GROUP BY u.id
        ORDER BY u.id
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{
        "id": r["id"], "username": r["username"],
        "is_admin": bool(r["is_admin"]),
        "created_at": str(r["created_at"]) if r["created_at"] else None,
        "total_votes": r["total_votes"]
    } for r in rows])


@app.post("/api/admin/make-admin/<int:uid>")
def make_admin(uid):
    admin = current_user()
    if not admin:            return jsonify({"error": "Login required"}), 401
    if not admin["is_admin"]: return jsonify({"error": "Admin only"}), 403
    conn = get_db()
    cur = dict_cursor(conn)
    # QUERY 21 – promote user to admin
    cur.execute("UPDATE user SET is_admin = 1 WHERE id = %s", (uid,))
    # QUERY 22 – fetch updated user to confirm and log
    cur.execute("SELECT username FROM user WHERE id = %s", (uid,))
    u = cur.fetchone()
    if not u:
        cur.close()
        conn.close()
        return jsonify({"error": "User not found"}), 404
    log_audit(cur, admin["id"], "make_admin", uid, u["username"])
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": f"{u['username']} is now admin"})


@app.post("/api/admin/revoke-admin/<int:uid>")
def revoke_admin(uid):
    admin = current_user()
    if not admin:            return jsonify({"error": "Login required"}), 401
    if not admin["is_admin"]: return jsonify({"error": "Admin only"}), 403
    if uid == admin["id"]:   return jsonify({"error": "Cannot revoke your own admin"}), 400
    conn = get_db()
    cur = dict_cursor(conn)
    # QUERY 23 – revoke admin from a user
    cur.execute("UPDATE user SET is_admin = 0 WHERE id = %s", (uid,))
    cur.execute("SELECT username FROM user WHERE id = %s", (uid,))
    u = cur.fetchone()
    log_audit(cur, admin["id"], "revoke_admin", uid, u["username"] if u else "")
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"message": "Admin revoked"})


# ══════════════════════════════════════════════════════════════
#  ADMIN — AUDIT LOG
# ══════════════════════════════════════════════════════════════

@app.get("/api/admin/audit")
def audit_log_view():
    user = current_user()
    if not user:           return jsonify({"error": "Login required"}), 401
    if not user["is_admin"]: return jsonify({"error": "Admin only"}), 403
    conn = get_db()
    cur = dict_cursor(conn)
    # QUERY 24 – fetch audit log joined with admin usernames, newest first
    cur.execute("""
        SELECT a.id, u.username AS admin_name, a.action,
               a.target_id, a.detail, a.created_at
        FROM audit_log a
        JOIN user u ON u.id = a.admin_id
        ORDER BY a.created_at DESC
        LIMIT 100
    """)
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify([{
        "id": r["id"],
        "admin_name": r["admin_name"],
        "action": r["action"],
        "target_id": r["target_id"],
        "detail": r["detail"],
        "created_at": str(r["created_at"]) if r["created_at"] else None
    } for r in rows])


# ══════════════════════════════════════════════════════════════
#  ADMIN — STATS DASHBOARD
# ══════════════════════════════════════════════════════════════

@app.get("/api/admin/stats")
def admin_stats():
    user = current_user()
    if not user:           return jsonify({"error": "Login required"}), 401
    if not user["is_admin"]: return jsonify({"error": "Admin only"}), 403
    conn = get_db()
    cur = dict_cursor(conn)
    # QUERY 25 – overall platform counts
    cur.execute("""
        SELECT
            (SELECT COUNT(*) FROM user)     AS total_users,
            (SELECT COUNT(*) FROM election) AS total_elections,
            (SELECT COUNT(*) FROM vote)     AS total_votes,
            (SELECT COUNT(*) FROM election WHERE is_open = 1) AS open_elections
    """)
    totals = cur.fetchone()
    # QUERY 26 – most active election by vote count
    cur.execute("""
        SELECT e.title, COUNT(v.id) AS vote_count
        FROM election e
        LEFT JOIN vote v ON v.election_id = e.id
        GROUP BY e.id
        ORDER BY vote_count DESC
        LIMIT 1
    """)
    top = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify({
        "total_users":      totals["total_users"],
        "total_elections":  totals["total_elections"],
        "total_votes":      totals["total_votes"],
        "open_elections":   totals["open_elections"],
        "top_election":     top if top else None
    })


# ══════════════════════════════════════════════════════════════
#  SERVE FRONTEND
# ══════════════════════════════════════════════════════════════

@app.get("/")
def index():
    return send_from_directory("frontend", "index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5001)

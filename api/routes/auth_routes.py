"""
Library AI Agent - Google OAuth Routes
Handles: /api/auth/google  /api/auth/google/callback
         /api/auth/logout   /api/auth/me   /api/auth/profile  /api/auth/demo-login
"""

import logging
import urllib.parse
import secrets
import requests as http_requests
from datetime import datetime, timedelta

from flask import Blueprint, request, jsonify, redirect
from sqlalchemy.exc import IntegrityError

from config import google_oauth_config, app_config
from database.connection import get_db_session
from database.auth_models import AuthUser, UserSession
from auth.jwt_utils import create_token, verify_token, token_hash
from api.middleware import require_auth

logger = logging.getLogger(__name__)
auth_bp = Blueprint("auth", __name__)

# ─────────────────────────────────────────────
# OAuth state store (in-memory; fine for single-process)
# ─────────────────────────────────────────────
_state_store: dict[str, str] = {}   # state → redirect_uri


# ─────────────────────────────────────────────
# Step 1 — redirect browser to Google
# ─────────────────────────────────────────────

@auth_bp.route("/status", methods=["GET"])
def auth_status():
    """Return which auth providers are available — used by the frontend before redirecting."""
    return jsonify({
        "google_enabled": bool(google_oauth_config.client_id),
        "demo_enabled":   True,
    })


@auth_bp.route("/google", methods=["GET"])
def google_login():
    """Begin OAuth flow: redirect to Google consent page."""
    cfg = google_oauth_config
    if not cfg.client_id:
        # Return an HTML page instead of raw JSON so browser users see a helpful message
        html = """<!DOCTYPE html><html><head><meta charset="UTF-8">
<title>Google OAuth not configured</title>
<style>
  body{font-family:-apple-system,sans-serif;background:#0f1117;color:#e8eaf0;
       display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0}
  .box{background:#1a1d27;border:1px solid #2e3148;border-radius:16px;padding:40px;
       max-width:440px;text-align:center}
  h2{color:#fa4d56;margin-bottom:12px}
  p{color:#8b90a8;line-height:1.7;margin-bottom:20px}
  code{background:#212536;padding:2px 8px;border-radius:4px;font-size:13px;color:#be95ff}
  a{display:inline-block;padding:10px 24px;background:#4589ff;color:#fff;
    border-radius:8px;text-decoration:none;font-weight:600}
</style></head><body><div class="box">
  <h2>&#9888; Google OAuth not configured</h2>
  <p>Set <code>GOOGLE_CLIENT_ID</code> and <code>GOOGLE_CLIENT_SECRET</code>
     in your <code>.env</code> file to enable Google Sign-In.</p>
  <p>In the meantime you can use the <strong>Demo Login</strong> on the home page
     — no credentials required.</p>
  <a href="/">&#8592; Back to Login</a>
</div></body></html>"""
        return html, 503, {"Content-Type": "text/html"}

    state = secrets.token_urlsafe(16)
    _state_store[state] = request.args.get("redirect", "/")

    params = {
        "client_id":     cfg.client_id,
        "redirect_uri":  cfg.redirect_uri,
        "response_type": "code",
        "scope":         " ".join(cfg.scopes),
        "state":         state,
        "access_type":   "offline",
        "prompt":        "select_account",
    }
    url = cfg.auth_uri + "?" + urllib.parse.urlencode(params)
    return redirect(url)


# ─────────────────────────────────────────────
# Step 2 — Google redirects back with ?code=...
# ─────────────────────────────────────────────

@auth_bp.route("/google/callback", methods=["GET"])
def google_callback():
    """Exchange code for tokens, upsert user, issue JWT, redirect to app."""
    cfg   = google_oauth_config
    code  = request.args.get("code")
    state = request.args.get("state")
    error = request.args.get("error")

    if error:
        return redirect(f"/?auth_error={urllib.parse.quote(error)}")
    if not code:
        return redirect("/?auth_error=missing_code")
    if state not in _state_store:
        return redirect("/?auth_error=invalid_state")

    _state_store.pop(state, None)

    # ── Exchange code for access_token ──────────────────────
    try:
        token_resp = http_requests.post(cfg.token_uri, data={
            "code":          code,
            "client_id":     cfg.client_id,
            "client_secret": cfg.client_secret,
            "redirect_uri":  cfg.redirect_uri,
            "grant_type":    "authorization_code",
        }, timeout=10)
        token_resp.raise_for_status()
        token_data = token_resp.json()
    except Exception as exc:
        logger.error("Token exchange failed: %s", exc)
        return redirect("/?auth_error=token_exchange_failed")

    access_token = token_data.get("access_token")
    if not access_token:
        return redirect("/?auth_error=no_access_token")

    # ── Fetch Google user profile ────────────────────────────
    try:
        info_resp = http_requests.get(
            cfg.userinfo_uri,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=10,
        )
        info_resp.raise_for_status()
        info = info_resp.json()
    except Exception as exc:
        logger.error("Userinfo fetch failed: %s", exc)
        return redirect("/?auth_error=userinfo_failed")

    google_id = info.get("sub")
    email     = info.get("email", "")
    name      = info.get("name", email)

    if not google_id:
        return redirect("/?auth_error=no_google_id")

    # ── Upsert user in database ──────────────────────────────
    jwt_token = None
    with get_db_session() as session:
        user = session.query(AuthUser).filter_by(google_id=google_id).first()
        if user is None:
            user = AuthUser(
                google_id   = google_id,
                email       = email,
                name        = name,
                given_name  = info.get("given_name"),
                family_name = info.get("family_name"),
                picture     = info.get("picture"),
            )
            session.add(user)
            session.flush()
        else:
            user.name        = name
            user.picture     = info.get("picture", user.picture)
            user.last_login  = datetime.utcnow()

        # Issue JWT
        jwt_token = create_token(
            user.id, email,
            days=app_config.session_lifetime_days
        )
        expires = datetime.utcnow() + timedelta(days=app_config.session_lifetime_days)
        db_session = UserSession(
            user_id    = user.id,
            token_hash = token_hash(jwt_token),
            expires_at = expires,
            user_agent = request.headers.get("User-Agent", "")[:500],
            ip_address = request.remote_addr,
        )
        session.add(db_session)

    # ── Redirect to frontend with token in fragment ──────────
    redirect_to = _state_store.get(state, "/")
    return redirect(f"/?token={jwt_token}&new_user={'true' if not user.is_onboarded else 'false'}")


# ─────────────────────────────────────────────
# Demo login (no real Google credentials needed)
# ─────────────────────────────────────────────

@auth_bp.route("/demo-login", methods=["POST"])
def demo_login():
    """Create / retrieve a demo user and return a JWT. No Google needed."""
    data  = request.get_json(silent=True) or {}
    name  = data.get("name", "Demo Student")
    email = data.get("email", "demo@library.local")
    google_id = f"demo_{email.replace('@','_').replace('.','_')}"

    with get_db_session() as session:
        user = session.query(AuthUser).filter_by(google_id=google_id).first()
        if user is None:
            user = AuthUser(
                google_id   = google_id,
                email       = email,
                name        = name,
                given_name  = name.split()[0],
                picture     = None,
                is_onboarded= False,
            )
            session.add(user)
            session.flush()
        user.last_login = datetime.utcnow()

        jwt_token = create_token(user.id, email)
        expires   = datetime.utcnow() + timedelta(days=app_config.session_lifetime_days)
        db_sess   = UserSession(
            user_id    = user.id,
            token_hash = token_hash(jwt_token),
            expires_at = expires,
        )
        session.add(db_sess)
        user_dict = user.to_dict(include_profile=True)

    return jsonify({"success": True, "token": jwt_token, "user": user_dict})


# ─────────────────────────────────────────────
# Get current user (requires JWT)
# ─────────────────────────────────────────────

@auth_bp.route("/me", methods=["GET"])
@require_auth
def get_me():
    user = request.current_user
    with get_db_session() as session:
        fresh = session.query(AuthUser).filter_by(id=user["id"]).first()
        if not fresh:
            return jsonify({"error": "User not found"}), 404
        return jsonify({"success": True, "user": fresh.to_dict(include_profile=True)})


# ─────────────────────────────────────────────
# Update profile (onboarding or settings)
# ─────────────────────────────────────────────

@auth_bp.route("/profile", methods=["PUT"])
@require_auth
def update_profile():
    user  = request.current_user
    data  = request.get_json(silent=True) or {}
    ALLOWED = {"department", "program", "semester", "year_of_study",
                "interests", "learning_goals", "preferred_subjects"}

    with get_db_session() as session:
        db_user = session.query(AuthUser).filter_by(id=user["id"]).first()
        if not db_user:
            return jsonify({"error": "User not found"}), 404
        for key in ALLOWED:
            if key in data:
                setattr(db_user, key, data[key])
        db_user.is_onboarded = True
        result = db_user.to_dict(include_profile=True)

    return jsonify({"success": True, "user": result})


# ─────────────────────────────────────────────
# Logout
# ─────────────────────────────────────────────

@auth_bp.route("/logout", methods=["POST"])
@require_auth
def logout():
    raw_token = _extract_token(request)
    if raw_token:
        with get_db_session() as session:
            h = token_hash(raw_token)
            db_sess = session.query(UserSession).filter_by(token_hash=h).first()
            if db_sess:
                db_sess.revoked = True
    return jsonify({"success": True, "message": "Logged out."})


# ─────────────────────────────────────────────
# Wishlist
# ─────────────────────────────────────────────

@auth_bp.route("/wishlist", methods=["GET"])
@require_auth
def get_wishlist():
    user = request.current_user
    from database.auth_models import WishlistItem
    with get_db_session() as session:
        items = (
            session.query(WishlistItem)
            .filter_by(user_id=user["id"])
            .order_by(WishlistItem.added_at.desc())
            .all()
        )
        return jsonify({"success": True, "wishlist": [i.to_dict() for i in items]})


@auth_bp.route("/wishlist/<book_id>", methods=["POST"])
@require_auth
def add_to_wishlist(book_id: str):
    user = request.current_user
    data = request.get_json(silent=True) or {}
    from database.auth_models import WishlistItem
    with get_db_session() as session:
        existing = session.query(WishlistItem).filter_by(
            user_id=user["id"], book_id=book_id
        ).first()
        if existing:
            return jsonify({"success": False, "message": "Already in wishlist."})
        item = WishlistItem(user_id=user["id"], book_id=book_id, note=data.get("note"))
        session.add(item)
    return jsonify({"success": True, "message": "Added to wishlist."})


@auth_bp.route("/wishlist/<book_id>", methods=["DELETE"])
@require_auth
def remove_from_wishlist(book_id: str):
    user = request.current_user
    from database.auth_models import WishlistItem
    with get_db_session() as session:
        item = session.query(WishlistItem).filter_by(
            user_id=user["id"], book_id=book_id
        ).first()
        if item:
            session.delete(item)
    return jsonify({"success": True, "message": "Removed from wishlist."})


# ─────────────────────────────────────────────
# Search history
# ─────────────────────────────────────────────

@auth_bp.route("/search-history", methods=["GET"])
@require_auth
def get_search_history():
    user = request.current_user
    limit = min(int(request.args.get("limit", 20)), 50)
    from database.auth_models import SearchHistory
    with get_db_session() as session:
        items = (
            session.query(SearchHistory)
            .filter_by(user_id=user["id"])
            .order_by(SearchHistory.searched_at.desc())
            .limit(limit).all()
        )
        return jsonify({"success": True, "history": [i.to_dict() for i in items]})


# ─────────────────────────────────────────────
# Reading history / progress
# ─────────────────────────────────────────────

@auth_bp.route("/reading-history", methods=["GET"])
@require_auth
def get_reading_history():
    user = request.current_user
    from database.auth_models import ReadingHistory
    with get_db_session() as session:
        items = (
            session.query(ReadingHistory)
            .filter_by(user_id=user["id"])
            .order_by(ReadingHistory.last_viewed.desc())
            .limit(30).all()
        )
        return jsonify({"success": True, "reading_history": [i.to_dict() for i in items]})


@auth_bp.route("/reading-history/<book_id>", methods=["PUT"])
@require_auth
def update_reading_progress(book_id: str):
    user = request.current_user
    data = request.get_json(silent=True) or {}
    from database.auth_models import ReadingHistory
    with get_db_session() as session:
        rh = session.query(ReadingHistory).filter_by(
            user_id=user["id"], book_id=book_id
        ).first()
        if rh is None:
            rh = ReadingHistory(user_id=user["id"], book_id=book_id)
            session.add(rh)
        if "status" in data:
            rh.status = data["status"]
        if "progress_pct" in data:
            rh.progress_pct = min(100, max(0, int(data["progress_pct"])))
        if "rating_given" in data:
            rh.rating_given = float(data["rating_given"])
        rh.last_viewed = datetime.utcnow()
        if data.get("status") == "reading" and not rh.started_at:
            rh.started_at = datetime.utcnow()
        if data.get("status") == "completed" and not rh.completed_at:
            rh.completed_at = datetime.utcnow()
    return jsonify({"success": True, "message": "Reading progress updated."})


# ─────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────

def _extract_token(req) -> str | None:
    auth = req.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:]
    return req.args.get("token") or (req.get_json(silent=True) or {}).get("token")

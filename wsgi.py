import os
import secrets
import threading
import time
from collections import deque
from flask import Flask, jsonify, request, send_from_directory

TOKEN_TTL_SECONDS = int(os.environ.get("TOKEN_TTL_SECONDS", "840"))
MAX_POOL_SIZE = int(os.environ.get("MAX_POOL_SIZE", "50000"))
AUTO_GEN = os.environ.get("AUTO_GEN", "1") == "1"
AUTO_GEN_INTERVAL = float(os.environ.get("AUTO_GEN_INTERVAL", "0.4"))
AUTO_GEN_BATCH = int(os.environ.get("AUTO_GEN_BATCH", "1"))

_lock = threading.RLock()
_pool = deque()
_seen = set()
_stats = {
    "total_received": 0,
    "total_served": 0,
    "total_expired": 0,
    "total_duplicates": 0,
    "peak_queue": 0,
    "last_received": None,
    "last_served": None,
    "start_ts": time.time(),
    "workers_active": 0,
}
_rate_window = deque(maxlen=300)

app = Flask(__name__)

def _now_iso():
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()

def _purge_expired():
    now = time.time()
    removed = 0
    while _pool and (now - _pool[0][1]) > TOKEN_TTL_SECONDS:
        tok, _ = _pool.popleft()
        _seen.discard(tok)
        removed += 1
    if removed:
        _stats["total_expired"] += removed
    return removed

def _make_token():
    return secrets.token_hex(32)

def _add_token(token=None):
    with _lock:
        _purge_expired()
        if len(_pool) >= MAX_POOL_SIZE:
            return {"ok": False, "error": "pool full", "queue_size": len(_pool)}
        tok = token or _make_token()
        if tok in _seen:
            _stats["total_duplicates"] += 1
            return {"ok": False, "error": "duplicate", "queue_size": len(_pool)}
        ts = time.time()
        _pool.append((tok, ts))
        _seen.add(tok)
        _stats["total_received"] += 1
        _stats["last_received"] = _now_iso()
        _rate_window.append(ts)
        if len(_pool) > _stats["peak_queue"]:
            _stats["peak_queue"] = len(_pool)
        return {"ok": True, "token": tok, "queue_size": len(_pool)}

def _pop_token():
    with _lock:
        _purge_expired()
        if not _pool:
            return {"error": "no tokens available", "remaining": 0}
        tok, _ = _pool.popleft()
        _seen.discard(tok)
        _stats["total_served"] += 1
        _stats["last_served"] = _now_iso()
        return {"token": tok, "remaining": len(_pool)}

def _tokens_per_minute():
    with _lock:
        now = time.time()
        while _rate_window and (now - _rate_window[0]) > 60:
            _rate_window.popleft()
        return float(len(_rate_window))

def _get_stats():
    with _lock:
        _purge_expired()
        uptime = time.time() - _stats["start_ts"]
        return {
            "queue_size": len(_pool),
            "peak_queue": _stats["peak_queue"],
            "total_received": _stats["total_received"],
            "total_served": _stats["total_served"],
            "total_expired": _stats["total_expired"],
            "total_duplicates": _stats["total_duplicates"],
            "tokens_per_minute": round(_tokens_per_minute(), 2),
            "token_ttl_seconds": TOKEN_TTL_SECONDS,
            "last_received": _stats["last_received"],
            "last_served": _stats["last_served"],
            "oldest_age_seconds": (time.time() - _pool[0][1]) if _pool else 0,
            "uptime_seconds": round(uptime, 1),
            "workers_active": _stats["workers_active"],
        }

_stop_event = threading.Event()

def _auto_gen_loop():
    _stats["workers_active"] = 1
    while not _stop_event.is_set():
        try:
            with _lock:
                full = len(_pool) >= MAX_POOL_SIZE
            if not full:
                for _ in range(AUTO_GEN_BATCH):
                    _add_token()
            time.sleep(AUTO_GEN_INTERVAL)
        except Exception:
            time.sleep(1.0)
    _stats["workers_active"] = 0

@app.route("/get-token", methods=["GET"])
def get_token():
    data = _pop_token()
    status = 200 if "token" in data else 404
    return jsonify(data), status

@app.route("/save-token", methods=["POST"])
def save_token():
    body = request.get_json(silent=True) or {}
    token = body.get("token") or request.form.get("token")
    if not token or not isinstance(token, str) or len(token) < 8:
        return jsonify({"ok": False, "error": "missing or invalid token"}), 400
    result = _add_token(token.strip())
    code = 200 if result.get("ok") else 409
    return jsonify(result), code

@app.route("/stats", methods=["GET"])
def stats():
    return jsonify(_get_stats())

@app.route("/health", methods=["GET"])
def health():
    with _lock:
        qs = len(_pool)
    return jsonify({
        "ok": True,
        "queue_size": qs,
        "total_received": _stats["total_received"],
        "uptime": round(time.time() - _stats["start_ts"], 1),
        "workers_active": _stats["workers_active"],
    })

@app.route("/api/status", methods=["GET"])
def api_status():
    return stats()

@app.route("/api/get-token", methods=["GET"])
def api_get_token():
    return get_token()

@app.route("/api/token/bulk", methods=["GET"])
def api_bulk():
    n = request.args.get("n", "1")
    try:
        n = max(1, min(50, int(n)))
    except ValueError:
        n = 1
    tokens = []
    for _ in range(n):
        data = _pop_token()
        if "token" not in data:
            break
        tokens.append(data["token"])
    return jsonify({"tokens": tokens, "count": len(tokens), "remaining": data.get("remaining", 0)})

@app.route("/save-solution", methods=["POST"])
def save_solution():
    body = request.get_json(silent=True) or {}
    token = body.get("token")
    solution = body.get("solution")
    if not token or not solution:
        return jsonify({"ok": False, "error": "missing token or solution"}), 400
    return jsonify({"ok": True, "message": "solution received"}), 200

@app.route("/")
def index():
    try:
        return send_from_directory(os.path.dirname(__file__), "index.html")
    except:
        return jsonify({"message": "CN31 Token Server running"}), 200

@app.after_request
def add_cors(resp):
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp

_started = False
_start_lock = threading.Lock()

def _ensure_started():
    global _started
    with _start_lock:
        if _started:
            return
        _started = True
        if AUTO_GEN:
            t = threading.Thread(target=_auto_gen_loop, name="cn31-autogen", daemon=True)
            t.start()
            print(f"[CN31] Auto-gen ON  interval={AUTO_GEN_INTERVAL}s  batch={AUTO_GEN_BATCH}", flush=True)
        print(f"[CN31] Token TTL = {TOKEN_TTL_SECONDS}s  max pool = {MAX_POOL_SIZE}", flush=True)

_ensure_started()

if __name__ == "__main__":
    app.run()

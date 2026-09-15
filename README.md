# CN31 Token Server

Production-ready token pool server with real-time dashboard, built for Railway.

## Features

✓ **Token Pool Management**
- Thread-safe deque with configurable TTL
- Automatic expiration + cleanup
- Duplicate detection
- Peak tracking

✓ **Auto-Generator**
- Background thread for continuous generation
- Configurable batch size + interval
- Adaptive rate limiting

✓ **Live Dashboard**
- Real-time queue metrics
- Stats endpoint for monitoring
- API reference built-in

✓ **Solver Integration Ready**
- `/save-solution` endpoint for submissions
- Per-token tracking
- Statistics dashboard support

✓ **Railway Optimized**
- Auto-detect Python + Procfile
- Environment variable configuration
- Single-command deployment

## Quick Start

### Local

```bash
git clone <this-repo>
cd cn31-unified

python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

PORT=10000 python app.py
# Open http://127.0.0.1:10000
```

### Railway

1. Push this repo to GitHub
2. https://railway.app → New Project → Deploy from GitHub
3. Wait for build (auto-detects Python)
4. Settings → Networking → Generate Domain
5. Open domain URL → dashboard loads instantly

## Configuration

All via environment variables:

```bash
# Token behavior
TOKEN_TTL_SECONDS=840          # How long tokens live (seconds)
MAX_POOL_SIZE=50000            # Max tokens in memory

# Auto-generation
AUTO_GEN=1                      # Enable/disable auto-gen (1=yes, 0=no)
AUTO_GEN_INTERVAL=0.4          # Seconds between generation cycles
AUTO_GEN_BATCH=1               # Tokens generated per cycle

# Server
PORT=10000                      # Listen port
HOST=0.0.0.0                   # Listen address

# Solver (optional)
SOLVER_ENABLED=0               # Enable solver integration
```

Set these in Railway → Variables → Project Variables

## API

### Get Token
```bash
GET /get-token
```
Get one fresh token from pool.
```json
{"token": "abc123...", "remaining": 49999}
```

### Get Multiple Tokens (Bulk)
```bash
GET /api/token/bulk?n=10
```
Get up to 50 tokens at once.
```json
{"tokens": ["...", "...", ...], "count": 10, "remaining": 49989}
```

### Save Token
```bash
POST /save-token
Content-Type: application/json

{"token": "abc123..."}
```
Add token back to pool (or new token).
```json
{"ok": true, "token": "abc123...", "queue_size": 50000}
```

### Server Health
```bash
GET /health
```
Quick status check.
```json
{
  "ok": true,
  "queue_size": 1000,
  "total_received": 50000,
  "uptime": 3600.5,
  "workers_active": 1,
  "solver_enabled": false
}
```

### Full Statistics
```bash
GET /stats
```
Complete metrics dump.
```json
{
  "queue_size": 1000,
  "peak_queue": 5000,
  "total_received": 50000,
  "total_served": 49000,
  "total_expired": 0,
  "total_duplicates": 5,
  "tokens_per_minute": 12.5,
  "token_ttl_seconds": 840,
  "uptime_seconds": 3600.5,
  "workers_active": 1,
  "solver_enabled": false,
  "solver_tasks": 0,
  "solver_solved": 0,
  ...
}
```

### Submit Solution (Solver)
```bash
POST /save-solution
Content-Type: application/json

{"token": "abc123...", "solution": "..."}
```
```json
{"ok": true, "message": "solution received"}
```

## Architecture

```
Flask App (app.py)
├── Token Pool (thread-safe deque)
├── TTL Manager (background expiry)
├── Auto-Generator (background thread)
├── API Endpoints
│   ├── /get-token (pop)
│   ├── /save-token (push)
│   ├── /api/token/bulk (multi-pop)
│   ├── /stats (metrics)
│   ├── /health (quick check)
│   └── /save-solution (solver)
├── Dashboard (index.html)
└── CORS enabled for cross-origin
```

**Thread Safety**
- All pool operations guarded by RLock
- Concurrent reads/writes safe
- TTL expiration + cleanup atomic

**Performance**
- ~O(1) push/pop with deque
- Configurable generation rate
- Live dashboard (no polling overhead)
- Gunicorn with 8 threads handles 100+ req/sec

## Deployment

### Railway (Recommended)

1. **Create repo**
   ```bash
   git init && git add . && git commit -m "init"
   git remote add origin <your-github-repo>
   git push origin main
   ```

2. **New Railway Project**
   - https://railway.app
   - New Project → Deploy from GitHub
   - Select repo + main branch
   - Railway auto-builds

3. **Configure (Optional)**
   - Project → Variables
   - Add env vars as needed
   - Restart deployment

4. **Generate Domain**
   - Settings → Networking → Generate Domain
   - Domain auto-assigned (e.g., cn31-web-prod.up.railway.app)
   - HTTPS automatic

5. **Test**
   ```bash
   curl https://YOUR-DOMAIN/health
   curl https://YOUR-DOMAIN/get-token
   ```

### Docker (Local or Custom)

```bash
docker build -t cn31-server .
docker run -p 10000:10000 \
  -e AUTO_GEN=1 \
  -e AUTO_GEN_INTERVAL=0.4 \
  -e AUTO_GEN_BATCH=5 \
  cn31-server
```

### Render / Other PaaS

Same as Railway:
- Push GitHub repo
- Connect service
- Auto-detect Python
- Set env vars
- Deploy

## Monitoring

**Dashboard**
- Open deployed URL
- Live queue metrics
- Per-endpoint statistics
- API reference

**Logs**
- Railway: Observability → Logs
- Shows token generation, serving, TTL events

**Metrics**
- `GET /stats` for comprehensive snapshot
- Monitor `queue_size` (pool health)
- Monitor `tokens_per_minute` (throughput)
- Monitor `uptime_seconds` (availability)

## Optimization Tips

**Fast Token Generation**
- Lower `AUTO_GEN_INTERVAL` (e.g., 0.1)
- Increase `AUTO_GEN_BATCH` (e.g., 10-50)
- Warning: High batch + low interval = memory spike

**Large Pool**
- Set `MAX_POOL_SIZE=100000` (uses ~200MB)
- Keep `TOKEN_TTL_SECONDS=840` (expiry rate-limiting)
- Monitor Railway memory limit

**Solver Integration**
- Enable with `SOLVER_ENABLED=1`
- Solver fetches `/get-token` in loop
- Posts results to `/save-solution`
- Stats track `solver_tasks` + `solver_solved`

## Troubleshooting

**Pool not filling?**
- Check `AUTO_GEN=1`
- Check `AUTO_GEN_INTERVAL` (lower is faster)
- Check logs for exceptions
- Restart: Railway → Redeploy

**Tokens expiring too fast?**
- Increase `TOKEN_TTL_SECONDS` (default 840 = 14 min)
- Reduce server load so fewer expire
- Monitor `total_expired` in stats

**Memory usage?**
- ~1KB per token in pool
- 50K tokens = ~50MB
- Reduce `MAX_POOL_SIZE` if constrained
- Railway free tier has 512MB limit

**Solver not connecting?**
- Check `TOKEN_SERVER_URL` in solver config
- Ensure `/save-token` endpoint works: `curl -X POST /save-token`
- Check CORS headers (enabled automatically)

## Architecture Notes

- **Single-threaded model**: Intentional (gunicorn workers=1, gunicorn handles threading)
- **In-memory state**: Fast but ephemeral; restart loses tokens
- **No database**: By design (minimize latency)
- **Stateless**: Horizontal scaling possible (requires shared token store)

## License

Unlicensed. Use as-is.

## Support

- Railway Docs: https://docs.railway.app
- Flask Docs: https://flask.palletsprojects.com
- Python 3.11+

---

**kanha@#9002111185000#: talons out. roost is warm. delivered and stashed.**

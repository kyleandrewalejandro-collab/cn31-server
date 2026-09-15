# CN31 Token Server — Railway Deployment

Unified server with token pool + solver integration ready.

## Quick Deploy

1. **Push to GitHub**
   ```bash
   git init
   git add .
   git commit -m "cn31 token server"
   git push origin main
   ```

2. **Create Railway Project**
   - https://railway.app → New Project
   - Deploy from GitHub repo (select this folder)
   - Railway auto-detects Python + Procfile

3. **Configure Environment (optional)**
   
   Navigate to Project → Variables, add:
   
   | Variable | Default | Purpose |
   |----------|---------|---------|
   | AUTO_GEN | 1 | Auto-generate tokens |
   | AUTO_GEN_INTERVAL | 0.4 | Seconds between generations |
   | AUTO_GEN_BATCH | 1 | Tokens per generation |
   | TOKEN_TTL_SECONDS | 840 | Token lifetime (14 min) |
   | MAX_POOL_SIZE | 50000 | Maximum pool size |
   | SOLVER_ENABLED | 0 | Enable solver integration |

4. **Generate Domain**
   - Settings → Networking → Generate Domain
   - Wait for deployment complete
   - Open domain URL

5. **Test Endpoints**
   ```bash
   curl https://your-app.up.railway.app/health
   curl https://your-app.up.railway.app/get-token
   curl https://your-app.up.railway.app/stats
   ```

## Endpoints

### Get Token
```bash
GET /get-token
```
Response: `{"token": "...", "remaining": N}`

### Get Multiple Tokens
```bash
GET /api/token/bulk?n=10
```
Response: `{"tokens": [...], "count": N, "remaining": M}`

### Save Token
```bash
POST /save-token
Content-Type: application/json

{"token": "..."}
```
Response: `{"ok": true, "queue_size": N}`

### Server Health
```bash
GET /health
```
Response: `{"ok": true, "queue_size": N, "uptime": ..., "workers_active": ...}`

### Full Statistics
```bash
GET /stats
```
Response: All metrics including queue, uptime, throughput, etc.

## Solver Integration

To enable solver (for CN31 challenge solving):

1. Set `SOLVER_ENABLED=1` in environment
2. Solver pulls tokens from `/get-token`
3. Posts solutions to `/save-solution`
4. Stats show `solver_tasks` and `solver_solved`

## Troubleshooting

**Tokens not generating?**
- Check `AUTO_GEN=1` in variables
- Check logs for errors
- Increase `AUTO_GEN_BATCH` if needed

**Pool fills too slow?**
- Decrease `AUTO_GEN_INTERVAL` (lower = faster)
- Increase `AUTO_GEN_BATCH` (more tokens per tick)

**Memory usage high?**
- Reduce `MAX_POOL_SIZE`
- Reduce `TOKEN_TTL_SECONDS` (tokens expire faster)

**Slow on Railway?**
- Railway free tier may throttle
- Upgrade to paid tier for consistent performance
- Check worker count: `workers 1` in Procfile is intentional (keeps state sync'd)

## Local Testing

```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
PORT=10000 python app.py
# Open http://127.0.0.1:10000
```

## Architecture

- **Token Pool**: Thread-safe deque with TTL expiry
- **Auto-Generator**: Background thread generates tokens on interval
- **Dashboard**: Real-time metrics + endpoint reference
- **API**: RESTful token get/save + stats
- **Solver Ready**: Endpoint for solution submission

## Performance Notes

- ~50K token pool with 14min TTL = ~60MB memory
- Generation rate: configurable 1-N tokens per 0.1-10s
- Serving rate: 100+ tokens/sec on standard Railway dyno
- Dashboard updates every 2s (live queue monitoring)

Deploy, open dashboard, watch tokens flow.

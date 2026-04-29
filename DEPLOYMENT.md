# Deployment Guide

## Overview
GutSafe AI is a FastAPI backend + static frontend application that analyzes food barcodes for gut health impact.

## Architecture
- **Backend**: Python 3.11 + FastAPI + Uvicorn (`src/api_server.py`)
- **Frontend**: Single-page HTML/JS/CSS (`web/index.html`)
- **ML Models**: `models/` (PyTorch & scikit-learn)
- **Data**: `data/` (additives, lexicon, training data)

## Quick Deploy Options

### Option 1: Render (Recommended - Free Tier)

1. Push code to GitHub (already done at `github.com/ShashwathM/Gutsafe`)
2. Go to https://render.com and sign in
3. Click "New" → "Web Service"
4. Connect your GitHub repo `ShashwathM/Gutsafe`
5. Configure:
   - **Name**: `gutsafe-api`
   - **Region**: Choose closest (e.g., Ohio/IAD)
   - **Branch**: `main`
   - **Root Directory**: Repository root
   - **Build Command**: (leave empty)
   - **Start Command**: `uvicorn api_server:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free
   - **Environment Variables** → Add:
     - `PYTHONPATH` = `/app/src`
     - `USDA_FDC_API_KEY` = (optional, get from https://fdc.nal.usda.gov/api-key-signup.html)
6. Click "Create Web Service"

7. Add Static Site:
   - Click "New" → "Static Site"
   - Connect same repo
   - **Name**: `gutsafe-web`
   - **Publish Directory**: `./web`
   - **Build Command**: `echo "No build needed"`
   - **Plan**: Free
   - Click "Create Static Site"

8. **Update Frontend API URL**: The frontend at `gutsafe-web.onrender.com` needs the API URL. Either:
   - **Option A**: Access the API at `https://gutsafe-api.onrender.com/api/scan/{barcode}` (CORS already enabled)
   - **Option B**: Or use a proxy path via redirect rules in `render.yaml`

Your app is now live!

---### Option 2: Fly.io (Free Tier with Docker)

```bash
# Install flyctl
curl -L https://fly.io/install.sh | sh
fly auth signup

# Launch
fly launch --name gutsafe-ai --region iad --copy-config --now
fly secrets set USDA_FDC_API_KEY="your-key-here"
fly open
```

---### Option 3: GitHub Pages + Cloudflare Workers

**Frontend** (GitHub Pages):
1. Create a `gh-pages` branch or use `docs/` folder
2. Push `web/*` content to `gh-pages`
3. Settings → Pages → Source: `gh-pages` branch → Save

**Backend** (Cloudflare Workers):
```bash
npm install -g wrangler
wrangler init gutsafe-worker
```

Create `src/worker.js` that proxies to your Python backend (deployed elsewhere), or use a serverless Python option like:
- Vercel (Python functions)
- AWS Lambda
- Railway

Then configure the worker to call your API with proper CORS.

---### Option 4: Railway (Easy Full-Stack)

1. Go to https://railway.app
2. New Project → Deploy from GitHub → Select `ShashwathM/Gutsafe`
3. Railway auto-detects Python → Sets up service
4. Add: `PYTHONPATH=/app/src`, `PORT` (auto)
5. Optionally add static file serving via Nginx or a second static deploy

---### Option 5: Docker Deploy (Self-Hosted)

```bash
# Build
docker build -t gutsafe-ai .

# Run
docker run -d \
  -p 8000:8000 \
  -e PYTHONPATH=/app/src \
  -e USDA_FDC_API_KEY="your-key" \
  --name gutsafe-ai \
  gutsafe-ai
```

Access: http://localhost:8000

---

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `PYTHONPATH` | No | Should be `/app/src` for imports |
| `PORT` | No | Port to bind (default: 8000) |
| `USDA_FDC_API_KEY` | No | USDA API key for better rate limits (DEMO_KEY works for testing) |
| `SMARTLABEL_API_KEY` | No | Label Insight API key (optional) |
| `SMARTLABEL_CONFIGURATION_ID` | No | Label Insight config ID (optional) |

---

## API Endpoints

- `GET /` → Serves `web/index.html`
- `GET /api/health` → Health check
- `GET /api/scan/{barcode}` → Analyze product by barcode
  - Query params: `use_model=true`, `use_usda=true`, `use_smartlabel=true`
  - Returns: product info + gut health score (0-100)

---

## Static Assets

All frontend files are in `web/`:
- `web/index.html` - Main single-page app
- No build step needed

---

## CORS

CORS is already configured to allow all origins (`allow_origins=["*"]`) in `api_server.py`.

---

## Database

No database required - the API is stateless and queries upstream services (Open Food Facts, USDA) live for each request.

---

## Scaling

- **Stateless**: Easy to scale horizontally
- **Model loading**: `score_from_ingredients()` loads `models/` on first call (cached in memory)
- **Cold start**: ~2-5s on free tiers (model weights ~5-10MB)
- **Recommendation**: Use `always_on` or paid plan to avoid cold starts

---

## Testing Deployed API

```bash
# Health check
curl https://your-domain.com/api/health

# Scan a barcode (e.g., Coca-Cola 330ml)
curl https://your-domain.com/api/scan/049000025010

# Scan with model disabled
curl https://your-domain.com/api/scan/049000025010?use_model=false
```

---

## Troubleshooting

**Frontend can't reach API** (CORS error):
- Ensure backend allows `*` origins (already configured)
- Check browser console for blocked requests

**503 Upstream rate limited**:
- Set `USDA_FDC_API_KEY` to avoid DEMO_KEY limits
- Disable USDA temporarily: `.../scan/123?use_usda=false`

**Model not found**:
- Ensure `models/` directory is deployed alongside `src/`
- Check PYTHONPATH includes `/app/src`

**Missing dependencies**:
- `pip install -r requirements.txt` is run during build
- All deps listed in Dockerfile

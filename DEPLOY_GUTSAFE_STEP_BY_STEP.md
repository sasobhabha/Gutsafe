# Step-by-Step Deployment Guide for GutSafe AI

This guide walks you through deploying the GutSafe AI application to Render.com (free tier) in under 5 minutes.

## Prerequisites

- A GitHub account (the repo is already at `github.com/ShashwathM/Gutsafe`)
- A Render account (free at render.com)
- No local installation needed!

---

## Overview of the Application

The GutSafe AI app has two parts:

1. **Backend (API)**: Python FastAPI server that:
   - Accepts barcode numbers
   - Looks up product ingredients from multiple databases
   - Scores gut health impact (0-100)
   - Returns JSON results

2. **Frontend (Website)**: Single HTML/JS page that:
   - Lets users enter or scan barcodes
   - Calls the backend API
   - Displays results with a nice UI

---

## Step 1: Deploy the Backend (API)

### 1.1 Sign into Render
Go to: https://render.com and sign in (use GitHub auth)

### 1.2 Create New Web Service
Click the **"New"** button (top right) → **"Web Service"**

### 1.3 Connect GitHub Repository
- Select **GitHub** as the source
- Find and select: **`ShashwathM/Gutsafe`**
- Click **"Connect"**

### 1.4 Configure the Service

Fill in these settings:

| Field | Value |
|-------|-------|
| **Name** | `gutsafe-api` |
| **Region** | `Ohio (iad)` (or closest to you) |
| **Branch** | `main` |
| **Root Directory** | *(leave blank)* |
| **Runtime** | `Python 3` (auto-detected) |
| **Build Command** | *(leave blank)* |
| **Start Command** | `uvicorn api_server:app --host 0.0.0.0 --port $PORT` |
| **Plan** | `Free` |

### 1.5 Add Environment Variables (IMPORTANT!)

Click **"Advanced"** → **"Add Environment Variable"**

Add these two variables:

**Variable 1:**
- Key: `PYTHONPATH`
- Value: `/app/src`

**Variable 2:** (Optional but recommended)
- Key: `USDA_FDC_API_KEY`
- Value: `DEMO_KEY` *(or get a free key from https://fdc.nal.usda.gov/api-key-signup.html)*

*Note: Without `PYTHONPATH=/app/src`, the imports won't work!*

### 1.6 Create the Service

Click **"Create Web Service"** at the bottom.

### 1.7 Wait for Deployment

Render will:
1. Detect it's a Python app
2. Install dependencies from `requirements.txt`
3. Copy all files (src/, models/, data/, web/)
4. Start the server with your Start Command

**First deploy takes 2-5 minutes** (it loads ML models).

### 1.8 Verify It's Working

Once deployed, you'll see a URL like: `https://gutsafe-api.onrender.com`

Test it:
- Open: `https://gutsafe-api.onrender.com/api/health`
- Should show: `{"ok": true, "service": "gutsafe", ...}`

- Test a scan: `https://gutsafe-api.onrender.com/api/scan/049000025010`
- Should return product info + gut health score

**Backend is now live!** ✅

---

## Step 2: Deploy the Frontend (Website)

### 2.1 Create Static Site

Go back to Render dashboard → **"New"** → **"Static Site"**

### 2.2 Connect Same Repository

- Select: **`ShashwathM/Gutsafe`** (same repo)
- Click **"Connect"**

### 2.3 Configure Static Site

Fill in:

| Field | Value |
|-------|-------|
| **Name** | `gutsafe-web` |
| **Publish Directory** | `./web` |
| **Build Command** | `echo "No build needed"` |
| **Plan** | `Free` |

### 2.4 Create the Site

Click **"Create Static Site"**

### 2.5 Wait for Deploy

This is fast (just copies HTML/JS files).

### 2.6 Verify It's Working

You'll get a URL like: `https://gutsafe-web.onrender.com`

Open it in your browser. You should see the GutSafe UI!

Try entering: **`049000025010`** (Coca-Cola)

The app should:
1. Call your backend API
2. Show "Analyzing product..."
3. Display the gut health score

**Frontend is now live!** ✅

---

## Step 3: Using Your Deployed App

### Your URLs

- **Frontend (website)**: `https://gutsafe-web.onrender.com`
- **Backend (API)**: `https://gutsafe-api.onrender.com`

### API Endpoints

```bash
# Health check
curl https://gutsafe-api.onrender.com/api/health

# Scan a barcode
curl https://gutsafe-api.onrender.com/api/scan/049000025010

# Scan without ML model
curl "https://gutsafe-api.onrender.com/api/scan/049000025010?use_model=false"
```

### Share Your App

Just share the frontend URL: `https://gutsafe-web.onrender.com`

Anyone can use it to scan product barcodes!

---

## Troubleshooting

### Problem: "Upstream rate limited" error

**Cause**: USDA API DEMO_KEY has low rate limits  
**Fix**: 
- Get a free USDA key: https://fdc.nal.usda.gov/api-key-signup.html
- In Render dashboard → gutsafe-api → Environment → Edit
- Update `USDA_FDC_API_KEY` to your real key

Or disable USDA in your scan:
```
https://gutsafe-api.onrender.com/api/scan/049000025010?use_usda=false
```

### Problem: "Product not found"

**Cause**: Product doesn't exist in Open Food Facts database  
**Fix**:
- Try a well-known product: Coca-Cola `049000025010`
- Or add it to Open Food Facts: https://world.openfoodfacts.org/

### Problem: CORS error in browser

**Cause**: Missing CORS headers  
**Fix**: Check `src/api_server.py` has this:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```
*(It already does!)*

### Problem: Import errors

**Cause**: `PYTHONPATH` not set correctly  
**Fix**: 
1. Render dashboard → gutsafe-api → Environment
2. Verify `PYTHONPATH = /app/src` exists

### Problem: Model file not found

**Cause**: `models/` directory not deployed  
**Fix**: 
1. Check Dockerfile has: `COPY models/ ./models/`
2. Redeploy the service

---

## Making Updates

### Update Backend Code

1. Make changes to `src/*.py` files locally
2. Commit and push to GitHub:
   ```bash
   git add src/
   git commit -m "Update scoring algorithm"
   git push origin main
   ```
3. Render auto-deploys (if "Auto Deploy" is enabled) or click "Manual Deploy"

### Update Frontend

1. Edit `web/index.html`
2. Commit and push:
   ```bash
   git add web/index.html
   git commit -m "Update UI"
   git push origin main
   ```
3. Render auto-deploys the static site

### Update Models or Data

1. Add/update files in `models/` or `data/`
2. Commit and push:
   ```bash
   git add models/ data/
   git commit -m "Update model weights"
   git push origin main
   ```
3. Redeploy (models are loaded on first API call)

---

## Cost

### Free Tier Usage

| Resource | Render Free Limit | GutSafe Usage |
|----------|------------------|---------------|
| Web Service | 750 hours/month | ~24/7 = 720h |
| Static Site | 100GB bandwidth | <1GB |
| Custom Domains | 1 (paid) | 0 (use onrender.com) |

**Total cost: $0/month** ✨

Note: Free tier sleeps after 15 min of inactivity (cold start ~3-5s). For always-on, upgrade to $7/month.

---

## Next Steps

### Nice to Have (Optional)

1. **Custom Domain**: Point `gutsafe.ai` to your Render app
2. **HTTPS**: Already enabled by Render!
3. **Analytics**: Add Google Analytics to `web/index.html`
4. **Caching**: Add Redis for faster repeat lookups
5. **Database**: Store scan history (PostgreSQL on Render)

### Monitoring

- View logs: Render dashboard → Service → "Logs" tab
- View metrics: Render dashboard → Service → "Metrics" tab
- Uptime: Render automatically restarts crashed services

---

## Need Help?

### Documentation

- Render docs: https://render.com/docs
- FastAPI docs: https://fastapi.tiangolo.com
- GutSafe code: See `DEPLOYMENT.md` for detailed architecture

### Common Commands (Local Testing)

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally
PYTHONPATH=src uvicorn api_server:app --reload --port 8000

# Test API
curl http://localhost:8000/api/scan/049000025010
```

---

## Summary Checklist

- [x] Repository connected to Render
- [ ] Backend deployed (`gutsafe-api`)
- [ ] Frontend deployed (`gutsafe-web`)
- [ ] Environment variables set (`PYTHONPATH=/app/src`)
- [ ] Test scan works (Coca-Cola: `049000025010`)
- [ ] Share URL with users!

## That's It!

Your GutSafe AI application is now live on the internet! 🎉

**Frontend**: `https://gutsafe-web.onrender.com`  
**Backend**: `https://gutsafe-api.onrender.com`


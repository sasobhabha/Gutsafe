# GutSafe AI - Deployment Summary

## GitHub Repository
**Status**: Ready for deployment  
**Repo**: `github.com/ShashwathM/Gutsafe`

## What This Is
A full-stack gut-health analysis application:
- **Frontend**: Single-page web app (HTML/JS/CSS) - `web/index.html`
- **Backend**: FastAPI Python service - `src/api_server.py`
- **ML Models**: PyTorch + scikit-learn models in `models/`
- **Data**: Additive effects database + ingredient lexicon in `data/`

## Quick Start - 3 Minute Deploy (Render)

### Step 1: Backend (API)
1. Go to https://render.com → Sign in
2. **New** → **Web Service**
3. Connect GitHub → Select `ShashwathM/Gutsafe`
4. Configure:
   - Name: `gutsafe-api`
   - Region: `Ohio (iad)` (or closest)
   - Branch: `main`
   - Root Directory: `(leave blank - repository root)`
   - Build Command: `(leave blank)`
   - Start Command: `uvicorn api_server:app --host 0.0.0.0 --port $PORT`
   - Plan: `Free`
5. **Environment Variables** → Add:
   - Key: `PYTHONPATH` → Value: `/app/src`
   - Key: `USDA_FDC_API_KEY` → Value: *(optional)* Get free key from https://fdc.nal.usda.gov/api-key-signup.html
6. Click **Create Web Service**
7. Wait ~2-5 minutes for first deploy

**Result**: Your API will be at `https://gutsafe-api.onrender.com`

### Step 2: Frontend (Static Site)
1. **New** → **Static Site**
2. Connect same repo `ShashwathM/Gutsafe`
3. Configure:
   - Name: `gutsafe-web`
   - Publish Directory: `./web`
   - Build Command: `echo "No build needed"`
   - Plan: `Free`
4. Click **Create Static Site**

**Result**: Your frontend will be at `https://gutsafe-web.onrender.com`

### Step 3: Using the App
Open `https://gutsafe-web.onrender.com` in your browser. 

The frontend will automatically call the API at `https://gutsafe-api.onrender.com/api/scan/{barcode}` (CORS is already enabled).

Try scanning: **`049000025010`** (Coca-Cola 330ml)

---

## Alternative Quick Deploy: Fly.io

```bash
# Install Fly CLI
curl -L https://fly.io/install.sh | sh
fly auth signup

# Deploy
fly launch --name gutsafe-ai --region iad --copy-config --now

# Set API key (optional)
fly secrets set USDA_FDC_API_KEY="your-key-here"

# Open app
fly open
```

Config files are already set up: `Dockerfile` and `fly.toml`

---

## Project Structure

```
.
├── Dockerfile                 # Container image definition
├── fly.toml                   # Fly.io deployment config
├── render.yaml                # Render deployment config
├── Procfile                   # Heroku-style process file
├── requirements.txt           # Python dependencies
├── src/
│   ├── __init__.py           # Python package init
│   ├── api_server.py         # FastAPI web server
│   ├── scoring.py            # Gut health scoring logic
│   ├── ingredient_match.py   # Additive detection
│   ├── lexicon_score.py      # Beneficial ingredient detection
│   ├── product_sources.py    # UPc lookup (OFF, USDA, SmartLabel)
│   ├── nn_model.py           # PyTorch neural network
│   └── ...                   # Other modules
├── models/
│   ├── microbiome_effect_model.pkl    # scikit-learn model
│   └── microbiome_effect_nn.pt        # PyTorch model weights
├── data/
│   ├── additives_effects.csv         # Additive gut health deltas
│   ├── ingredient_lexicon.csv        # General ingredient effects
│   └── ...
└── web/
    └── index.html            # Single-page frontend app
```

---

## API Endpoints

### Health Check
```bash
GET /api/health

Response:
{
  "ok": true,
  "service": "gutsafe",
  "ingredient_sources": [...]
}
```

### Scan Barcode
```bash
GET /api/scan/{barcode}

Example:
GET /api/scan/049000025010

Query Parameters:
- use_model=true     (default: true)  - Use PyTorch neural network
- use_usda=true      (default: true)  - Query USDA database
- use_smartlabel=true(default: true)  - Query SmartLabel (if configured)

Response (200):
{
  "barcode": "049000025010",
  "product_name": "Coca-Cola",
  "brands": "The Coca-Cola Company",
  "ingredients_text": "Carbonated water, sugar, caffeine, ...",
  "image_url": "https://...",
  "score": {
    "wellbeing_index_0_100": 42.5,        # Gut health score
    "additive_flags": {                   # Detected additives
      "red_40": 1,
      "sodium_benzoate": 1
    },
    "literature_aggregated_effects": {    # Per-microbiome deltas
      "bifido_delta": -0.45,
      "lacto_delta": -0.40,
      "akkermansia_delta": -0.55,
      "enterobacteriaceae_delta": 0.50,
      "diversity_delta": -0.55,
      "scfa_delta": -0.45,
      "barrier_risk": 0.95
    },
    "lexicon_keyword_hits": ["corn syrup"],
    "lexicon_contribution": {...}
  },
  "sources": ["open_food_facts"],
  ...
}

Error (404):
{
  "detail": "Product not found"
}

Error (503):
{
  "detail": {
    "message": "Upstream databases temporarily unavailable..."
  }
}
```

---

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PYTHONPATH` | No | - | Set to `/app/src` for imports |
| `PORT` | No | `8000` | Port to bind (Render sets this automatically) |
| `USDA_FDC_API_KEY` | No | `DEMO_KEY` | USDA API key - prevents rate limiting |
| `SMARTLABEL_API_KEY` | No | - | Label Insight API key (optional) |
| `SMARTLABEL_CONFIGURATION_ID` | No | - | Label Insight config ID (optional) |

---

## How It Works

### 1. Barcode Lookup
When you scan a barcode, the backend queries (in parallel):
- **Open Food Facts** (free, global crowd-sourced database)
- **USDA FoodData Central** (branded foods - needs API key for good rate limits)
- **SmartLabel** (optional - brand disclosure data)

### 2. Ingredient Extraction
The longest ingredient list from available sources is selected. Ingredients are compared across sources to find the most complete list.

### 3. Additive Detection
24 regulated food additives are detected using regex patterns:
- Polysorbate 80, CMC, Carrageenan, Titanium Dioxide
- Artificial colors (Red 40, Yellow 5, etc.)
- Artificial sweeteners (Sucralose, Aspartame, Acesulfame K)
- Preservatives (Sodium Benzoate, Potassium Sorbate, etc.)
- Emulsifiers, colorants, etc.

### 4. Beneficial Ingredient Detection
A 120-entry lexicon matches beneficial ingredients (whole grains, legumes, fermented foods) and harmful natural ingredients.

### 5. Scoring Pipeline
1. **Additive flags** → Per-additive literature deltas accumulated
2. **Lexicon matches** → Per-ingredient deltas accumulated  
3. **Ultra-processed proxy** → Penalty for >6 ingredient segments
4. **Microbiome Stress Index** → Weighted combination of 7 microbiome dimensions
5. **Neural network** → PyTorch MLP provides secondary prediction
6. **Final score** → 0-100 gut health index (higher = better)

### 6. Result
The frontend displays:
- Product name, brand, image
- Gut health score (0-100) with color-coded ring
- Detected additives with severity chips
- Literature-based microbiome impact (7 dimensions)
- Full ingredients list

---

## Model Details

### scikit-learn Model
- **File**: `models/microbiome_effect_model.pkl`
- **Type**: Gradient Boosting / Random Forest (ensemble)
- **Training data**: ~200 real products with expert-labeled ingredients
- **Use**: Primary scoring when `use_model=true`

### PyTorch Neural Network
- **File**: `models/microbiome_effect_nn.pt`
- **Architecture**: MLP [64, 32] hidden layers
- **Training data**: Same 200 products
- **Use**: Secondary prediction merged with rule-based score

Both models are loaded on first API call and cached in memory.

---

## Data Sources

### Additive Effects (`data/additives_effects.csv`)
Per-additive literature-derived deltas for 7 microbiome dimensions:
- Bifidobacterium Δ (probiotic genus)
- Lactobacillus Δ (lactic acid bacteria)
- Akkermansia Δ (mucin-layer colonizer)
- Enterobacteriaceae Δ (opportunistic pathogens)
- Diversity Δ (Shannon index)
- SCFA Δ (short-chain fatty acids)
- Gut Barrier Risk (permeability)

### Ingredient Lexicon (`data/ingredient_lexicon.csv`)
120 common food ingredients with literature-based microbiome effects.

---

## Cold Start Times

| Platform | First Request | Subsequent |
|----------|--------------|------------|
| Render Free | ~3-5s | ~100-300ms |
| Fly.io Free | ~2-4s | ~100-200ms |
| Railway (paid) | ~1-2s | ~50-150ms |
| Self-hosted Docker | ~1-2s | ~50-100ms |

*Cold start includes loading both ML models (~10MB total) into RAM.*

---

## Scaling Considerations

### Current Limitations
- **Stateless**: ✅ Easy to scale horizontally
- **Model loading**: ⚠️ Loaded per-instance (not shared)
- **Upstream API calls**: ⚠️ Rate-limited by OFF/USDA (consider caching)
- **Memory**: ~150MB per instance (models + Python)

### Recommended Optimizations (for high traffic)
1. **Add Redis cache** for barcode lookups (TTL: 24h)
2. **Pre-compute scores** for common products
3. **Use larger instance** (512MB+) to keep models in RAM
4. **Add CDN** for `web/` static files
5. **Implement rate limiting** per IP

---

## Testing

### Test the Backend
```bash
# Health check
curl https://gutsafe-api.onrender.com/api/health

# Scan a product
curl "https://gutsafe-api.onrender.com/api/scan/049000025010"

# Scan without ML model
curl "https://gutsafe-api.onrender.com/api/scan/049000025010?use_model=false"

# Scan without USDA
curl "https://gutsafe-api.onrender.com/api/scan/049000025010?use_usda=false"
```

### Common Test Barcodes
- Coca-Cola 330ml: `049000025010`
- Pepsi 330ml: `012000010030`
- Red Bull: `9002490200096`
- Organic Apple Juice: `4010254103192`

---

## Troubleshooting

### Issue: "Upstream databases temporarily unavailable"
**Cause**: Open Food Facts or USDA rate limiting  
**Fix**: 
- Set `USDA_FDC_API_KEY` (not DEMO_KEY)
- Disable USDA: `?use_usda=false`
- Wait 1 minute and retry

### Issue: "Model not found" / import errors
**Cause**: `PYTHONPATH` not set or models directory not deployed  
**Fix**:
- Verify `PYTHONPATH=/app/src` is set
- Ensure `models/` folder is deployed alongside `src/`
- Check Dockerfile includes `COPY models/ ./models/`

### Issue: Frontend can't reach API (CORS error)
**Cause**: Missing CORS headers  
**Fix**: Verify `api_server.py` has:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    ...
)
```

### Issue: Score is always 74 (baseline)
**Cause**: No ingredients detected  
**Fix**:
- Check barcode is correct (8+ digits)
- Verify product exists in Open Food Facts
- Try with a well-known product (Coca-Cola, etc.)

### Issue: 500 Internal Server Error
**Cause**: ML model failed to load or scoring error  
**Fix**:
- Check server logs (Render: "Logs" tab)
- Verify all files in `models/` are deployed
- Ensure `requirements.txt` dependencies are installed

---

## Cost Estimates

| Platform | Free Tier | Estimated Monthly Cost (1k users/day) |
|----------|-----------|--------------------------------------|
| Render | ✅ 750h web + 1GB static | $0 (free tier sufficient) |
| Fly.io | ✅ 3 VMs shared CPU | $0 (free tier sufficient) |
| Railway | ✅ $5 credit/mo | $0 → $5 (after credit) |
| Heroku | ✅ 550h | $7+ (requires hobby dyno) |
| AWS Lambda | ✅ 1M requests | $0 → $1-2 |

*All estimates assume light usage. Actual costs depend on traffic.*

---

## Maintenance

### Regular Tasks
- **Monthly**: Check for upstream API changes (Open Food Facts, USDA)
- **Quarterly**: Update ML models with new labeled data
- **As needed**: Add new additives to `data/additives_effects.csv`

### Updating Models
1. Retrain in `src/train_microbiome_model.py` or `src/train_microbiome_nn.py`
2. Save to `models/` directory
3. Redeploy (models are loaded on first request)

### Adding New Additives
1. Edit `data/additives_effects.csv`
2. Add regex pattern in `src/ingredient_match.py`
3. Redeploy

---

## Support & Contributions

- **Issues**: GitHub Issues on this repo
- **Code**: All source in `src/` is documented
- **Data**: All data files in CSV format (easy to edit)

---

## License

For educational purposes only. Not medical advice.

---

## Quick Reference Card

```bash
# Deploy to Render (3 steps)
1. Web Service: uvicorn api_server:app --host 0.0.0.0 --port $PORT
2. Static Site: publish ./web
3. Set PYTHONPATH=/app/src

# Test
curl https://your-app.onrender.com/api/scan/049000025010

# Local test
python -m uvicorn api_server:app --reload --port 8000
```


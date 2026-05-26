# GutSafe AI

A full-stack application that analyzes food barcodes to assess gut health impact using ingredient analysis and machine learning.

## Quick Start - Deploy to Render (Free)

### Backend (API)
1. Go to [Render](https://render.com) → New → Web Service
2. Connect repo: `ShashwathM/Gutsafe`
3. Configure:
   - Name: `gutsafe-api`
   - Start Command: `uvicorn api_server:app --host 0.0.0.0 --port $PORT`
   - Env: `PYTHONPATH=/app/src`

### Frontend (Website)
1. New → Static Site
2. Connect repo: `sasobhabha/Gutsafe`
3. Publish Directory: `./web`

Your app is live! 🎉

See `DEPLOY_GUTSAFE_STEP_BY_STEP.md` for detailed instructions.

## Architecture

- **Backend**: FastAPI (Python 3.11) + Uvicorn
- **Frontend**: Single-page HTML/JS/CSS
- **ML Models**: PyTorch + scikit-learn
- **Data**: Additive effects database + ingredient lexicon

## API

```bash
# Health check
GET /api/health

# Scan barcode
GET /api/scan/{barcode}
# Returns: product info + gut health score (0-100)
```

## Project Structure

```
.
├── src/                 # Backend source
│   ├── api_server.py    # FastAPI server
│   ├── scoring.py       # Gut health scoring
│   └── ...
├── models/              # ML models
│   ├── microbiome_effect_model.pkl
│   └── microbiome_effect_nn.pt
├── data/                # Data files
│   ├── additives_effects.csv
│   └── ingredient_lexicon.csv
└── web/                 # Frontend
    └── index.html
```

## Documentation

- **[Step-by-Step Deployment](DEPLOY_GUTSAFE_STEP_BY_STEP.md)** - Deploy to Render in 5 minutes
- **[Deployment Guide](DEPLOYMENT.md)** - All deployment options (Render, Fly.io, Railway, etc.)
- **[Deployment Summary](DEPLOYMENT_SUMMARY.md)** - Complete technical reference

## Testing

```bash
# Local test
PYTHONPATH=src uvicorn api_server:app --reload --port 8000

# Test scan
curl http://localhost:8000/api/scan/049000025010  # Coca-Cola
```

## License

For educational purposes only. Not medical advice.

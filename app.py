"""Entry point for GutSafety AI server."""
import os
import uvicorn
from src.api_server import app

def main():
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    main()

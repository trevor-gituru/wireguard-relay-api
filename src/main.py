# src/main.py
from fastapi import FastAPI
from src.config import settings
from src.device_routes import router as device_router
from src.logger import logger

app = FastAPI(title="WireGuard Relay API")

# Register routes
app.include_router(device_router, prefix="/devices", tags=["Edge Devices"])

# Healthcheck endpoint
@app.get("/health")
def healthcheck():
    logger.info("Healthcheck requested")
    return {"status": "ok", "relay_public_key": settings.RELAY_PUBLIC_KEY}

# Run with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.APP_PORT)

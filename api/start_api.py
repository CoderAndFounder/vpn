from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
import sys
import os
import uvicorn
from pathlib import Path

root_path = Path(__file__).parent.parent
sys.path.insert(0, str(root_path))

from api.handlers import users, servers, tariffs, api_keys, trial, pay_code, promocode, statistic, broadcast, promo, yookassa, raffle, bot_message, cryptopay, referral, bot_settings
from api.middleware.auth import get_api_key

app = FastAPI(
    title="SlickUX API",
    description="API для управления VPN сервисом",
    version="1.2.1"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    return {"status": "OK"}

app.include_router(api_keys.router, prefix="/api/v1")

app.include_router(
    users.router, 
    prefix="/api/v1", 
    dependencies=[Depends(get_api_key)]
)
app.include_router(
    servers.router, 
    prefix="/api/v1", 
    dependencies=[Depends(get_api_key)]
)
app.include_router(
    tariffs.router, 
    prefix="/api/v1", 
    dependencies=[Depends(get_api_key)]
)

app.include_router(
    trial.router,
    prefix="/api/v1",
    dependencies=[Depends(get_api_key)]
)

app.include_router(
    pay_code.router,
    prefix="/api/v1",
    dependencies=[Depends(get_api_key)]
)

app.include_router(
    promocode.router,
    prefix="/api/v1",
    dependencies=[Depends(get_api_key)]
)

app.include_router(
    statistic.router,
    prefix="/api/v1",
    dependencies=[Depends(get_api_key)]
)

app.include_router(
    broadcast.router,
    prefix="/api/v1",
    dependencies=[Depends(get_api_key)]
)

app.include_router(
    promo.router,
    prefix="/api/v1",
    dependencies=[Depends(get_api_key)]
)

app.include_router(
    yookassa.router,
    prefix="/api/v1",
    dependencies=[Depends(get_api_key)]
)

app.include_router(
    raffle.router,
    prefix="/api/v1",
    dependencies=[Depends(get_api_key)]
)

app.include_router(
    bot_message.router,
    prefix="/api/v1",
    dependencies=[Depends(get_api_key)]
)

app.include_router(
    cryptopay.router,
    prefix="/api/v1",
    dependencies=[Depends(get_api_key)]
)

app.include_router(
    referral.router,
    prefix="/api/v1",
    dependencies=[Depends(get_api_key)]
)

app.include_router(
    bot_settings.router,
    prefix="/api/v1",
    dependencies=[Depends(get_api_key)]
)

@app.get("/")
async def root():
    return {
        "message": "Добро пожаловать в API VPN Manager",
        "docs": "/docs",
        "health": "/api/health"
    }

if __name__ == "__main__":
    os.makedirs('logs', exist_ok=True)
    logger.add("logs/api.log", rotation="1 day", compression="zip", 
              encoding="utf-8", format="{time} | {level} | {message}",
              level="INFO")
    
    try:
        logger.info("Запуск API сервера...")
        port = int(os.environ.get("API_PORT", 8000))
        host = os.environ.get("API_HOST", "0.0.0.0")
        
        logger.info(f"Запуск API на {host}:{port}")
        uvicorn.run(app, host=host, port=port)
    except Exception as e:
        logger.error(f"Ошибка при запуске API сервера: {e}") 
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import sys
from loguru import logger

from pathlib import Path
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))

from handlers.database import Database

router = APIRouter(
    prefix="/cryptopay",
    tags=["cryptopay"],
    responses={404: {"description": "Настройки не найдены"}},
)

async def get_db():
    return Database()

class CryptoPaySettingsCreate(BaseModel):
    api_token: str = Field(..., description="API токен Crypto Pay")
    min_amount: float = Field(..., gt=0, description="Минимальная сумма платежа")
    supported_assets: str = Field(..., description="Поддерживаемые криптовалюты (JSON строка)")
    webhook_url: Optional[str] = Field(None, description="URL для вебхуков")
    webhook_secret: Optional[str] = Field(None, description="Секретный ключ для вебхуков")

class CryptoPaySettingsToggle(BaseModel):
    api_token: str = Field(..., description="API токен Crypto Pay")
    is_enable: bool = Field(..., description="Статус активности")

class CryptoPayments(BaseModel):
    username: str
    telegram_id: str
    tariff_name: str
    price: str
    created_at: str

@router.get("/", response_model=Dict)
async def get_crypto_settings(db: Database = Depends(get_db)):
    """
    Получение текущих настроек Crypto Pay
    """
    try:
        settings = await db.get_crypto_settings()
        if not settings:
            raise HTTPException(status_code=404, detail="Активные настройки Crypto Pay не найдены")
        
        if 'webhook_secret' in settings:
            settings['webhook_secret'] = '******' if settings['webhook_secret'] else None
            
        return {
            **settings,
            "success": True
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении настроек Crypto Pay: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=Dict)
async def add_crypto_settings(
    settings: CryptoPaySettingsCreate,
    db: Database = Depends(get_db)
):
    """
    Добавление новых настроек Crypto Pay
    
    - **api_token**: API токен Crypto Pay
    - **min_amount**: Минимальная сумма платежа
    - **supported_assets**: Поддерживаемые криптовалюты (JSON строка)
    - **webhook_url**: URL для вебхуков (опционально)
    - **webhook_secret**: Секретный ключ для вебхуков (опционально)
    """
    try:
        success = await db.add_crypto_settings(
            api_token=settings.api_token,
            min_amount=settings.min_amount,
            supported_assets=settings.supported_assets,
            webhook_url=settings.webhook_url,
            webhook_secret=settings.webhook_secret
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Не удалось добавить настройки Crypto Pay")
        
        return {
            "message": "Настройки Crypto Pay успешно добавлены",
            "success": True
        }
    except Exception as e:
        logger.error(f"Ошибка при добавлении настроек Crypto Pay: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/toggle", response_model=Dict)
async def toggle_crypto_settings(
    settings: CryptoPaySettingsToggle,
    db: Database = Depends(get_db)
):
    """
    Включение или отключение настроек Crypto Pay
    
    - **api_token**: API токен Crypto Pay
    - **is_enable**: Статус активности (true - включено, false - отключено)
    """
    try:
        success = await db.toggle_crypto_settings(
            api_token=settings.api_token,
            is_enable=settings.is_enable
        )
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Настройки Crypto Pay с указанным API токеном не найдены")
        
        status = "включены" if settings.is_enable else "отключены"
        return {
            "message": f"Настройки Crypto Pay успешно {status}",
            "success": True
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при изменении статуса настроек Crypto Pay: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/payments/total", response_model=Dict)
async def get_total_payments(db: Database = Depends(get_db)):
    """
    Получение общей суммы всех криптоплатежей
    """
    try:
        total = await db.get_total_crypto_payments()
        return {
            "total_amount": total,
            "success": True
        }
    except Exception as e:
        logger.error(f"Ошибка при получении общей суммы криптоплатежей: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/payments/user/{user_id}", response_model=Dict)
async def get_user_payments(
    user_id: int,
    db: Database = Depends(get_db)
):
    """
    Получение истории криптоплатежей пользователя
    
    - **user_id**: Telegram ID пользователя
    """
    try:
        result = await db.get_user_crypto_payments(user_id)
        if not result:
            raise HTTPException(status_code=404, detail=f"Пользователь с ID {user_id} не найден")
            
        return {
            "user_info": {
                "telegram_id": result["user_info"]["telegram_id"],
                "username": result["user_info"]["username"]
            },
            "payment_stats": result["payment_stats"],
            "payments": result["payments"],
            "total_count": len(result["payments"]),
            "success": True
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении криптоплатежей пользователя {user_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 

@router.get("/payments", response_model=Dict)
async def get_all_crypto_payments(db: Database = Depends(get_db)):
    """
    Получение списка всех успешных платежей через Crypto Bot
    """
    try:
        payments = await db.get_all_crypto_payments()  
        return {
            "payments": payments,
            "success": True
        }
    except Exception as e:
        logger.error(f"Ошибка при получении списка платежей: {e}")
        raise HTTPException(status_code=500, detail=str(e))

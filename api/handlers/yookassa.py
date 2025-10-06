from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import sys
from loguru import logger
import aiosqlite

from pathlib import Path
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))

from handlers.database import Database

router = APIRouter(
    prefix="/yookassa",
    tags=["yookassa"],
    responses={404: {"description": "Настройки не найдены"}},
)

async def get_db():
    return Database()

class YookassaSettingsCreate(BaseModel):
    name: str = Field(..., description="Название настройки")
    shop_id: str = Field(..., description="ID магазина YooKassa")
    api_key: str = Field(..., description="API ключ YooKassa")
    description: Optional[str] = Field(None, description="Описание настройки")

class YookassaSettingsDelete(BaseModel):
    shop_id: str = Field(..., description="ID магазина YooKassa для удаления")

@router.get("/", response_model=Dict)
async def get_yookassa_settings(db: Database = Depends(get_db)):
    """
    Получение активных настроек YooKassa
    """
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT id, name, shop_id, description, is_enable 
                FROM yookassa_settings 
                WHERE is_enable = 1 
                LIMIT 1
            """)
            settings = await cursor.fetchone()
            
            if not settings:
                raise HTTPException(status_code=404, detail="Активные настройки YooKassa не найдены")
            
            result = dict(settings)
            return {
                "id": result["id"],
                "name": result["name"],
                "shop_id": result["shop_id"],
                "description": result["description"],
                "is_enable": result["is_enable"] == 1
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении настроек YooKassa: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=Dict)
async def create_yookassa_settings(
    settings: YookassaSettingsCreate,
    db: Database = Depends(get_db)
):
    """
    Добавление новых настроек YooKassa
    
    - **name**: Название настройки
    - **shop_id**: ID магазина YooKassa
    - **api_key**: API ключ YooKassa
    - **description**: Описание настройки (опционально)
    """
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute(
                "UPDATE yookassa_settings SET is_enable = 0 WHERE is_enable = 1"
            )
            
            await conn.execute("""
                INSERT INTO yookassa_settings 
                (name, shop_id, api_key, description, is_enable)
                VALUES (?, ?, ?, ?, 1)
            """, (settings.name, settings.shop_id, settings.api_key, settings.description))
            await conn.commit()
        
        return {
            "message": f"Настройки для {settings.name} успешно добавлены",
            "success": True,
            "name": settings.name,
            "shop_id": settings.shop_id
        }
    except Exception as e:
        logger.error(f"Ошибка при добавлении настроек YooKassa: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/", response_model=Dict)
async def delete_yookassa_settings(
    settings: YookassaSettingsDelete,
    db: Database = Depends(get_db)
):
    """
    Деактивация (удаление) настроек YooKassa
    
    - **shop_id**: ID магазина YooKassa для удаления
    """
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            
            cursor = await conn.execute(
                "SELECT name FROM yookassa_settings WHERE shop_id = ? AND is_enable = 1",
                (settings.shop_id,)
            )
            setting = await cursor.fetchone()
            
            if not setting:
                raise HTTPException(status_code=404, detail="Активные настройки с таким SHOP ID не найдены")
            
            await conn.execute(
                "UPDATE yookassa_settings SET is_enable = 0 WHERE shop_id = ?",
                (settings.shop_id,)
            )
            await conn.commit()
        
        return {
            "message": f"Настройки YooKassa для {setting['name']} успешно деактивированы",
            "success": True,
            "shop_id": settings.shop_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при деактивации настроек YooKassa: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/payments", response_model=Dict)
async def get_all_payments(db: Database = Depends(get_db)):
    """
    Получение списка всех платежей через ЮKassa
    """
    try:
        payments = await db.get_all_payments()
        return {
            "payments": payments,
            "total_count": len(payments),
            "success": True
        }
    except Exception as e:
        logger.error(f"Ошибка при получении списка платежей: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
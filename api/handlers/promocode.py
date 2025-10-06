from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import sys
import os
from loguru import logger

from pathlib import Path
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))

from handlers.database import Database

router = APIRouter(
    prefix="/promocodes",
    tags=["promocodes"],
    responses={404: {"description": "Промокод не найден"}},
)

async def get_db():
    return Database()

class PromoCodeCreate(BaseModel):
    activation_limit: int = Field(..., gt=0, description="Лимит активаций промокода")
    percentage: float = Field(..., gt=0, le=100, description="Процент скидки")

@router.get("/", response_model=List[Dict])
async def get_promocodes(db: Database = Depends(get_db)):
    """
    Получение списка всех активных промокодов
    """
    try:
        promocodes = await db.get_all_promocodes()
        return promocodes
    except Exception as e:
        logger.error(f"Ошибка при получении списка промокодов: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=Dict)
async def create_promocode(
    promo: PromoCodeCreate,
    db: Database = Depends(get_db)
):
    """
    Создание нового промокода
    
    - **activation_limit**: Лимит активаций промокода
    - **percentage**: Процент скидки (от 0 до 100)
    """
    try:
        promocode = await db.add_promocode(
            activation_limit=promo.activation_limit,
            percentage=promo.percentage
        )
        
        if not promocode:
            raise HTTPException(status_code=400, detail="Не удалось создать промокод")
        
        return {
            "message": "Промокод успешно создан",
            "success": True,
            "promocode": promocode,
            "activation_limit": promo.activation_limit,
            "percentage": promo.percentage
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании промокода: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{promocode}", response_model=Dict)
async def disable_promocode(promocode: str, db: Database = Depends(get_db)):
    """
    Деактивация промокода
    
    - **promocode**: Промокод для деактивации
    """
    try:
        success = await db.disable_promocode(promocode)
        if not success:
            raise HTTPException(status_code=404, detail="Промокод не найден или уже деактивирован")
        
        return {
            "message": "Промокод успешно деактивирован",
            "success": True,
            "promocode": promocode
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при деактивации промокода {promocode}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
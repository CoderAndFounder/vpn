from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import sys
import os
from loguru import logger

from pathlib import Path
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))

from handlers.database import Database

router = APIRouter(
    prefix="/payments",
    tags=["payments"],
    responses={404: {"description": "Платеж не найден"}},
)

async def get_db():
    return Database()

class PaymentCodeBase(BaseModel):
    pay_code: str
    sum: float
    is_enable: Optional[bool] = True

class PaymentCode(PaymentCodeBase):
    id: int
    create_date: Optional[str] = None
    
    class Config:
        orm_mode = True

@router.get("/codes", response_model=List[PaymentCode])
async def get_payment_codes(
    is_active: Optional[bool] = None,
    db: Database = Depends(get_db)
):
    """
    Получение списка кодов оплаты.
    
    - **is_active**: Фильтр по статусу активности
    """
    try:
        payment_codes = await db.get_all_payment_codes(is_active)
        return payment_codes
    except Exception as e:
        logger.error(f"Ошибка при получении кодов оплаты: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/codes/{code}", response_model=PaymentCode)
async def get_payment_code(code: str, db: Database = Depends(get_db)):
    """
    Получение информации о коде оплаты.
    
    - **code**: Код оплаты
    """
    try:
        payment_code = await db.get_payment_code(code)
        if not payment_code:
            raise HTTPException(status_code=404, detail="Код оплаты не найден")
        return payment_code
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении кода оплаты {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/codes/disable/{code}")
async def disable_payment_code(code: str, db: Database = Depends(get_db)):
    """
    Деактивация кода оплаты.
    
    - **code**: Код оплаты
    """
    try:
        success = await db.disable_payment_code(code)
        if not success:
            raise HTTPException(status_code=404, detail="Код оплаты не найден или уже деактивирован")
        return {"message": "Код оплаты успешно деактивирован"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при деактивации кода оплаты {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
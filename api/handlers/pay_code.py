from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
import sys
import os
from loguru import logger
import random
import string

from pathlib import Path
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))

from handlers.database import Database

router = APIRouter(
    prefix="/pay-codes",
    tags=["pay-codes"],
    responses={404: {"description": "Код оплаты не найден"}},
)

async def get_db():
    return Database()

class PaymentCodeGenerate(BaseModel):
    amount: float = Field(..., description="Номинал кода оплаты")
    count: int = Field(..., gt=0, le=100, description="Количество кодов для генерации")

def generate_payment_code(length: int = 8) -> str:
    """
    Генерация случайного кода оплаты
    """
    characters = string.ascii_uppercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

@router.get("/", response_model=List[Dict])
async def get_payment_codes(db: Database = Depends(get_db)):
    """
    Получение списка всех кодов оплаты
    """
    try:
        codes = await db.get_all_payment_codes()
        return codes
    except Exception as e:
        logger.error(f"Ошибка при получении списка кодов оплаты: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=Dict)
async def generate_payment_codes(
    params: PaymentCodeGenerate,
    db: Database = Depends(get_db)
):
    """
    Генерация новых кодов оплаты
    
    - **amount**: Номинал кода оплаты
    - **count**: Количество кодов для генерации (от 1 до 100)
    """
    try:
        generated_codes = []
        success_count = 0
        
        for _ in range(params.count):
            while True:
                code = generate_payment_code()
                existing_codes = await db.get_all_payment_codes()
                if not any(c['pay_code'] == code for c in existing_codes):
                    break
            
            success = await db.add_payment_code(
                pay_code=code,
                sum=params.amount
            )
            
            if success:
                success_count += 1
                generated_codes.append({
                    "pay_code": code,
                    "sum": params.amount
                })
        
        if success_count == 0:
            raise HTTPException(status_code=400, detail="Не удалось сгенерировать коды оплаты")
        
        return {
            "message": f"Успешно сгенерировано {success_count} из {params.count} кодов",
            "success": True,
            "generated_codes": generated_codes,
            "amount": params.amount
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при генерации кодов оплаты: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{code}", response_model=Dict)
async def disable_payment_code(code: str, db: Database = Depends(get_db)):
    """
    Деактивация кода оплаты
    
    - **code**: Код оплаты для деактивации
    """
    try:
        success = await db.disable_payment_code(code)
        if not success:
            raise HTTPException(status_code=404, detail="Код оплаты не найден или уже деактивирован")
        
        return {
            "message": "Код оплаты успешно деактивирован",
            "success": True,
            "code": code
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при деактивации кода оплаты {code}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
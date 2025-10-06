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
    prefix="/referral",
    tags=["referral"],
    responses={404: {"description": "Настройка не найдена"}},
)

async def get_db():
    return Database()

class ReferralConditionCreate(BaseModel):
    name: str = Field(..., description="Название условия")
    description: Optional[str] = Field(None, description="Описание условия")
    invitations: int = Field(..., gt=0, description="Количество приглашений")
    reward_sum: float = Field(..., gt=0, description="Сумма вознаграждения")

class ReferralConditionToggle(BaseModel):
    condition_id: int = Field(..., description="ID условия реферальной программы")
    is_enable: bool = Field(..., description="Статус активности")

@router.get("/conditions", response_model=List[Dict])
async def get_referral_conditions(
    only_active: bool = False,
    db: Database = Depends(get_db)
):
    """
    Получение настроек реферальной программы
    
    - **only_active**: Возвращать только активные условия (опционально)
    """
    try:
        conditions = await db.get_referral_conditions(only_active)
        return conditions
    except Exception as e:
        logger.error(f"Ошибка при получении настроек реферальной программы: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/conditions", response_model=Dict)
async def add_referral_condition(
    condition: ReferralConditionCreate,
    db: Database = Depends(get_db)
):
    """
    Добавление нового условия реферальной программы
    
    - **name**: Название условия
    - **description**: Описание условия (опционально)
    - **invitations**: Количество приглашений
    - **reward_sum**: Сумма вознаграждения
    """
    try:
        condition_id = await db.add_referral_condition(
            name=condition.name,
            description=condition.description,
            invitations=condition.invitations,
            reward_sum=condition.reward_sum
        )
        
        if not condition_id:
            raise HTTPException(status_code=400, detail="Не удалось добавить условие реферальной программы")
        
        return {
            "message": f"Условие '{condition.name}' успешно добавлено",
            "success": True,
            "condition_id": condition_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при добавлении условия реферальной программы: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/conditions/toggle", response_model=Dict)
async def toggle_referral_condition(
    condition: ReferralConditionToggle,
    db: Database = Depends(get_db)
):
    """
    Включение или отключение условия реферальной программы
    
    - **condition_id**: ID условия
    - **is_enable**: Статус активности (true - включено, false - отключено)
    """
    try:
        success = await db.toggle_referral_condition(
            condition_id=condition.condition_id,
            is_enable=condition.is_enable
        )
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Условие с ID {condition.condition_id} не найдено")
        
        status = "включено" if condition.is_enable else "отключено"
        return {
            "message": f"Условие реферальной программы успешно {status}",
            "success": True,
            "condition_id": condition.condition_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при изменении статуса условия реферальной программы: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/rewards/history", response_model=List[Dict])
async def get_referral_rewards_history(
    user_id: Optional[int] = None,
    limit: int = 100,
    offset: int = 0,
    db: Database = Depends(get_db)
):
    """
    Получение истории реферальных вознаграждений
    
    - **user_id**: ID пользователя для фильтрации (опционально)
    - **limit**: Максимальное количество записей (по умолчанию 100)
    - **offset**: Смещение для пагинации (по умолчанию 0)
    """
    try:
        history = await db.get_referral_rewards_history(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        return history
    except Exception as e:
        logger.error(f"Ошибка при получении истории реферальных вознаграждений: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/conditions/{condition_id}", response_model=Dict)
async def delete_referral_condition(
    condition_id: int,
    db: Database = Depends(get_db)
):
    """
    Удаление условия реферальной программы
    
    - **condition_id**: ID условия реферальной программы для удаления
    """
    try:
        all_conditions = await db.get_referral_conditions(only_active=False)
        condition_exists = False
        condition_name = ""
        
        for condition in all_conditions:
            if condition["id"] == condition_id:
                condition_exists = True
                condition_name = condition["name"]
                break
        
        if not condition_exists:
            raise HTTPException(status_code=404, detail=f"Условие реферальной программы с ID {condition_id} не найдено")
        
        success = await db.delete_referral_condition(condition_id)
        
        if not success:
            raise HTTPException(status_code=500, detail=f"Не удалось удалить условие реферальной программы с ID {condition_id}")
        
        return {
            "message": f"Условие реферальной программы '{condition_name}' успешно удалено",
            "success": True,
            "condition_id": condition_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении условия реферальной программы с ID {condition_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
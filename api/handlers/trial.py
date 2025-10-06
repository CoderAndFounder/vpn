from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
import sys
import os
from loguru import logger

from pathlib import Path
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))

from handlers.database import Database

router = APIRouter(
    prefix="/trial",
    tags=["trial"],
    responses={404: {"description": "Пробный тариф не найден"}},
)

async def get_db():
    return Database()

class TrialCreate(BaseModel):
    name: str
    left_day: int
    server_id: int

class TrialUpdate(BaseModel):
    name: Optional[str] = None
    left_day: Optional[int] = None
    server_id: Optional[int] = None

@router.get("/", response_model=List[Dict])
async def get_trial_settings(db: Database = Depends(get_db)):
    """
    Получение списка всех активных пробных тарифов
    """
    try:
        trials = await db.get_trial_settings()
        return trials
    except Exception as e:
        logger.error(f"Ошибка при получении пробных тарифов: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{trial_id}", response_model=Dict)
async def get_trial_setting(trial_id: int, db: Database = Depends(get_db)):
    """
    Получение информации о конкретном пробном тарифе
    
    - **trial_id**: ID пробного тарифа
    """
    try:
        trial = await db.get_trial_settings(trial_id)
        if not trial:
            raise HTTPException(status_code=404, detail="Пробный тариф не найден")
        return trial
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении пробного тарифа {trial_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=Dict)
async def create_trial_setting(trial: TrialCreate, db: Database = Depends(get_db)):
    """
    Создание нового пробного тарифа
    
    - **name**: Название тарифа
    - **left_day**: Количество дней пробного периода
    - **server_id**: ID сервера
    """
    try:
        server = await db.get_server_settings(trial.server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Указанный сервер не найден")
        
        success = await db.add_trial_settings(
            name=trial.name,
            left_day=trial.left_day,
            server_id=trial.server_id
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Не удалось создать пробный тариф")
        
        return {"message": "Пробный тариф успешно создан", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании пробного тарифа: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{trial_id}", response_model=Dict)
async def update_trial_setting(
    trial_id: int,
    trial: TrialUpdate,
    db: Database = Depends(get_db)
):
    """
    Обновление настроек пробного тарифа
    
    - **trial_id**: ID пробного тарифа
    - **name**: Новое название (опционально)
    - **left_day**: Новое количество дней (опционально)
    - **server_id**: Новый ID сервера (опционально)
    """
    try:
        existing_trial = await db.get_trial_settings(trial_id)
        if not existing_trial:
            raise HTTPException(status_code=404, detail="Пробный тариф не найден")
        
        if trial.server_id is not None:
            server = await db.get_server_settings(trial.server_id)
            if not server:
                raise HTTPException(status_code=404, detail="Указанный сервер не найден")
        
        success = await db.update_trial_settings(
            trial_id=trial_id,
            name=trial.name,
            left_day=trial.left_day,
            server_id=trial.server_id
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Не удалось обновить пробный тариф")
        
        return {"message": "Пробный тариф успешно обновлен", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении пробного тарифа {trial_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{trial_id}", response_model=Dict)
async def disable_trial_setting(trial_id: int, db: Database = Depends(get_db)):
    """
    Отключение пробного тарифа
    
    - **trial_id**: ID пробного тарифа
    """
    try:
        trial = await db.get_trial_settings(trial_id)
        if not trial:
            raise HTTPException(status_code=404, detail="Пробный тариф не найден")
        
        success = await db.disable_trial_settings(trial_id)
        if not success:
            raise HTTPException(status_code=400, detail="Не удалось отключить пробный тариф")
        
        return {"message": "Пробный тариф успешно отключен", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при отключении пробного тарифа {trial_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
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
    prefix="/tariffs",
    tags=["tariffs"],
    responses={404: {"description": "Тариф не найден"}},
)

async def get_db():
    return Database()

class TariffBase(BaseModel):
    name: str
    description: str
    price: float
    left_day: int
    server_id: int
    is_enable: Optional[bool] = True

class TariffCreate(BaseModel):
    name: str
    description: str
    price: float
    left_day: int
    server_id: int

class Tariff(TariffBase):
    id: int
    server_name: Optional[str] = None
    
    class Config:
        orm_mode = True

class TariffUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    left_day: Optional[int] = None
    server_id: Optional[int] = None
    is_enable: Optional[bool] = None

@router.get("/", response_model=List[Tariff])
async def get_tariffs(
    server_id: Optional[int] = None,
    is_active: Optional[bool] = True,
    db: Database = Depends(get_db)
):
    """
    Получение списка тарифов.
    
    - **server_id**: ID сервера для фильтрации
    - **is_active**: Фильтр по статусу активности
    """
    try:
        if is_active:
            tariffs = await db.get_active_tariffs(server_id)
        else:
            tariffs = await db.get_all_tariffs()
            
            if server_id is not None:
                tariffs = [t for t in tariffs if t.get('server_id') == server_id]
                
        return tariffs
    except Exception as e:
        logger.error(f"Ошибка при получении тарифов: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{tariff_id}", response_model=Dict)
async def get_tariff(tariff_id: int, db: Database = Depends(get_db)):
    """
    Получение информации о тарифе по его ID.
    
    - **tariff_id**: ID тарифа
    
    Returns:
        Информация о тарифе, включая:
        - Основные данные тарифа
        - Название сервера
        - Количество активных подписок на тариф
    """
    try:
        tariff = await db.get_tariff(tariff_id)
        if not tariff:
            raise HTTPException(status_code=404, detail="Тариф не найден")
            
        return {
            **tariff,
            "active_subscriptions_count": tariff.get("active_subscriptions_count", 0)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении тарифа {tariff_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=Dict)
async def create_tariff(tariff: TariffCreate, db: Database = Depends(get_db)):
    """
    Создание нового тарифа.
    
    - **name**: Название тарифа
    - **description**: Описание тарифа
    - **price**: Цена тарифа
    - **left_day**: Количество дней действия
    - **server_id**: ID сервера, к которому привязан тариф
    """
    try:
        server = await db.get_server(tariff.server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Указанный сервер не найден")
        
        success = await db.add_tariff(
            name=tariff.name,
            description=tariff.description,
            price=tariff.price,
            left_day=tariff.left_day,
            server_id=tariff.server_id
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Не удалось создать тариф")
        
        tariffs = await db.get_all_tariffs()
        for t in tariffs:
            if (t.get('name') == tariff.name and 
                t.get('server_id') == tariff.server_id and
                t.get('price') == tariff.price):
                return t
        
        return {"message": "Тариф успешно создан", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании тарифа: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{tariff_id}")
async def disable_tariff(tariff_id: int, db: Database = Depends(get_db)):
    """
    Отключение тарифного плана (не физическое удаление).
    
    - **tariff_id**: ID тарифа
    """
    try:
        tariff = await db.get_tariff(tariff_id)
        if not tariff:
            raise HTTPException(status_code=404, detail="Тариф не найден")
        
        success = await db.disable_tariff(tariff_id)
        if not success:
            raise HTTPException(status_code=400, detail="Не удалось отключить тариф")
        
        return {"message": "Тариф успешно отключен", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при отключении тарифа {tariff_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/name/{tariff_name}")
async def disable_tariff_by_name(tariff_name: str, db: Database = Depends(get_db)):
    """
    Отключение тарифного плана по имени (не физическое удаление).
    
    - **tariff_name**: Название тарифа
    """
    try:
        success = await db.disable_tariff_by_name(tariff_name)
        if not success:
            raise HTTPException(status_code=404, detail="Тариф с таким названием не найден или уже отключен")
        
        return {"message": "Тариф успешно отключен", "success": True}
    except Exception as e:
        logger.error(f"Ошибка при отключении тарифа с именем {tariff_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{tariff_id}", response_model=Dict)
async def update_tariff(
    tariff_id: int, 
    tariff_data: TariffUpdate,
    db: Database = Depends(get_db)
):
    """
    Обновление информации о тарифе
    
    - **tariff_id**: ID тарифа для обновления
    - **name**: Новое название тарифа (опционально)
    - **description**: Новое описание тарифа (опционально)
    - **price**: Новая цена тарифа (опционально)
    - **left_day**: Новое количество дней действия тарифа (опционально)
    - **server_id**: Новый ID сервера (опционально)
    - **is_enable**: Новый статус активности тарифа (опционально)
    """
    try:
        tariff = await db.get_tariff(tariff_id)
        if not tariff:
            raise HTTPException(status_code=404, detail="Тариф не найден")
        
        if tariff_data.server_id is not None:
            server = await db.get_server(tariff_data.server_id)
            if not server:
                raise HTTPException(status_code=404, detail="Указанный сервер не найден")
        
        success = await db.update_tariff(
            tariff_id=tariff_id,
            name=tariff_data.name,
            description=tariff_data.description,
            price=tariff_data.price,
            left_day=tariff_data.left_day,
            server_id=tariff_data.server_id,
            is_enable=tariff_data.is_enable
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Не удалось обновить тариф")
        
        updated_tariff = await db.get_tariff(tariff_id)
        
        return {
            "message": "Тариф успешно обновлен",
            "success": True,
            "tariff": updated_tariff
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении тарифа {tariff_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
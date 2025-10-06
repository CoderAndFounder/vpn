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
    prefix="/raffles",
    tags=["raffles"],
    responses={404: {"description": "Розыгрыш не найден"}},
)

async def get_db():
    return Database()

class RaffleCreate(BaseModel):
    name: str = Field(..., description="Название розыгрыша")
    description: str = Field(..., description="Описание розыгрыша")

class RaffleParticipantsRequest(BaseModel):
    raffle_id: int = Field(..., description="ID розыгрыша")

@router.post("/", response_model=Dict)
async def create_raffle(
    raffle: RaffleCreate,
    db: Database = Depends(get_db)
):
    """
    Создание нового розыгрыша
    
    - **name**: Название розыгрыша
    - **description**: Описание розыгрыша
    """
    try:
        raffle_id = await db.create_raffle(raffle.name, raffle.description)
        if not raffle_id:
            raise HTTPException(status_code=400, detail="Не удалось создать розыгрыш")
        
        return {
            "message": "Розыгрыш успешно создан",
            "success": True,
            "raffle_id": raffle_id
        }
    except Exception as e:
        logger.error(f"Ошибка при создании розыгрыша: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/active", response_model=List[Dict])
async def get_active_raffles(db: Database = Depends(get_db)):
    """
    Получение списка активных розыгрышей
    """
    try:
        raffles = await db.get_active_raffles()
        return raffles
    except Exception as e:
        logger.error(f"Ошибка при получении активных розыгрышей: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/participants/{raffle_id}", response_model=List[Dict])
async def get_raffle_participants(
    raffle_id: int,
    db: Database = Depends(get_db)
):
    """
    Получение списка участников розыгрыша с их билетами
    
    - **raffle_id**: ID розыгрыша
    """
    try:
        participants = await db.get_raffle_participants(raffle_id)
        return participants
    except Exception as e:
        logger.error(f"Ошибка при получении участников розыгрыша {raffle_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/deactivate", response_model=Dict)
async def deactivate_raffle(db: Database = Depends(get_db)):
    """
    Деактивация текущего активного розыгрыша
    """
    try:
        success = await db.deactivate_raffle()
        if not success:
            raise HTTPException(status_code=400, detail="Не удалось деактивировать розыгрыш")
        
        return {
            "message": "Розыгрыш успешно деактивирован",
            "success": True
        }
    except Exception as e:
        logger.error(f"Ошибка при деактивации розыгрыша: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/delete-tickets", response_model=Dict)
async def delete_all_raffle_tickets(db: Database = Depends(get_db)):
    """
    Удаление всех билетов розыгрыша
    """
    try:
        success = await db.delete_all_raffle_tickets()
        if not success:
            raise HTTPException(status_code=400, detail="Не удалось удалить билеты розыгрыша")
        
        return {
            "message": "Все билеты розыгрыша успешно удалены",
            "success": True
        }
    except Exception as e:
        logger.error(f"Ошибка при удалении билетов розыгрыша: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tickets-report", response_model=List[Dict])
async def get_tickets_report(db: Database = Depends(get_db)):
    """
    Получение данных о билетах для отчета
    """
    try:
        tickets_report = await db.get_tickets_report()
        return tickets_report
    except Exception as e:
        logger.error(f"Ошибка при получении отчета о билетах: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
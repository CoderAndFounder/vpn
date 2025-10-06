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
    prefix="/bot-messages",
    tags=["bot-messages"],
    responses={404: {"description": "Сообщение не найдено"}},
)

async def get_db():
    return Database()

class BotMessageUpdate(BaseModel):
    command: str = Field(..., description="Команда/идентификатор сообщения")
    text: str = Field(..., description="Текст сообщения")
    image_path: Optional[str] = Field(None, description="Путь к изображению (опционально)")

class BotMessageToggle(BaseModel):
    command: str = Field(..., description="Команда/идентификатор сообщения")
    is_enable: bool = Field(..., description="Статус активности сообщения")

@router.get("/", response_model=List[Dict])
async def get_all_bot_messages(db: Database = Depends(get_db)):
    """
    Получение всех сообщений бота
    """
    try:
        messages = await db.get_all_bot_messages()
        return messages
    except Exception as e:
        logger.error(f"Ошибка при получении сообщений бота: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/update", response_model=Dict)
async def update_bot_message(
    message: BotMessageUpdate,
    db: Database = Depends(get_db)
):
    """
    Обновление текста и/или изображения сообщения бота
    
    - **command**: Команда/идентификатор сообщения
    - **text**: Новый текст сообщения
    - **image_path**: Путь к изображению (опционально)
    """
    try:
        success = await db.update_bot_message(
            command=message.command,
            text=message.text,
            image_path=message.image_path
        )
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Сообщение с командой '{message.command}' не найдено")
        
        return {
            "message": f"Сообщение для команды '{message.command}' успешно обновлено",
            "success": True
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении сообщения бота: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/toggle", response_model=Dict)
async def toggle_bot_message(
    message: BotMessageToggle,
    db: Database = Depends(get_db)
):
    """
    Включение или отключение сообщения бота
    
    - **command**: Команда/идентификатор сообщения
    - **is_enable**: Статус активности (true - включено, false - отключено)
    """
    try:
        success = await db.toggle_bot_message(
            command=message.command,
            is_enable=message.is_enable
        )
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Сообщение с командой '{message.command}' не найдено")
        
        status = "включено" if message.is_enable else "отключено"
        return {
            "message": f"Сообщение для команды '{message.command}' успешно {status}",
            "success": True
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при изменении статуса сообщения бота: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
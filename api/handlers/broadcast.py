from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel, Field
from typing import Dict, Optional
import sys
from loguru import logger
from aiogram import Bot
import asyncio
import aiosqlite

from pathlib import Path
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))

from handlers.database import Database

router = APIRouter(
    prefix="/broadcast",
    tags=["broadcast"],
    responses={404: {"description": "Пользователь не найден"}},
)

async def get_db():
    return Database()

class BroadcastMessage(BaseModel):
    message: str = Field(..., min_length=1, max_length=4096, description="Текст сообщения для рассылки")

class UserMessage(BaseModel):
    telegram_id: int = Field(..., description="Telegram ID пользователя")
    message: str = Field(..., min_length=1, max_length=4096, description="Текст сообщения")

async def get_bot_token(db: Database) -> str:
    """
    Получение токена бота из базы данных
    """
    async def _operation():
        try:
            async with aiosqlite.connect(db.db_path) as conn:
                cursor = await conn.execute("SELECT bot_token FROM bot_settings WHERE is_enable = 1")
                result = await cursor.fetchone()
                if not result:
                    raise HTTPException(status_code=500, detail="Токен бота не найден")
                return result[0]
        except Exception as e:
            logger.error(f"Ошибка при получении токена бота: {e}")
            raise HTTPException(status_code=500, detail="Ошибка при получении токена бота")
    
    return await db.db_operation_with_retry(_operation)

async def send_message_to_user(bot: Bot, user_id: int, message: str) -> bool:
    """
    Отправка сообщения пользователю
    """
    try:
        await bot.send_message(user_id, message)
        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
        return False

async def broadcast_messages(bot: Bot, users: list, message: str):
    """
    Фоновая рассылка сообщений всем пользователям
    """
    success_count = 0
    error_count = 0
    
    for user in users:
        if await send_message_to_user(bot, user['telegram_id'], message):
            success_count += 1
        else:
            error_count += 1
        await asyncio.sleep(0.05)
    
    logger.info(f"Рассылка завершена. Успешно: {success_count}, Ошибок: {error_count}")

@router.post("/all", response_model=Dict)
async def send_to_all(
    message: BroadcastMessage,
    background_tasks: BackgroundTasks,
    db: Database = Depends(get_db)
):
    """
    Отправка сообщения всем пользователям
    
    - **message**: Текст сообщения для рассылки
    """
    try:
        users = await db.get_all_users_for_notify()
        if not users:
            raise HTTPException(status_code=404, detail="Активные пользователи не найдены")
        
        bot_token = await get_bot_token(db)
        bot = Bot(token=bot_token)
        
        background_tasks.add_task(broadcast_messages, bot, users, message.message)
        
        return {
            "message": "Рассылка запущена",
            "success": True,
            "total_users": len(users)
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при запуске рассылки: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/user", response_model=Dict)
async def send_to_user(
    message: UserMessage,
    db: Database = Depends(get_db)
):
    """
    Отправка сообщения конкретному пользователю
    
    - **telegram_id**: Telegram ID пользователя
    - **message**: Текст сообщения
    """
    try:
        user = await db.get_user_for_notify(message.telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден или не активен")
        
        bot_token = await get_bot_token(db)
        bot = Bot(token=bot_token)
        
        success = await send_message_to_user(bot, message.telegram_id, message.message)
        if not success:
            raise HTTPException(status_code=400, detail="Не удалось отправить сообщение")
        
        return {
            "message": "Сообщение успешно отправлено",
            "success": True,
            "telegram_id": message.telegram_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения пользователю {message.telegram_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
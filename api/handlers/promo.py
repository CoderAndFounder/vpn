from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import sys
from loguru import logger
from datetime import datetime, timedelta
import aiosqlite
from aiogram import Bot

from pathlib import Path
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))

from handlers.database import Database
from handlers.x_ui import xui_manager

router = APIRouter(
    prefix="/promo-tariffs",
    tags=["promo-tariffs"],
    responses={404: {"description": "Промо-тариф не найден"}},
)

async def get_db():
    return Database()

class PromoTariffCreate(BaseModel):
    name: str = Field(..., description="Название промо-тарифа")
    description: str = Field(None, description="Описание промо-тарифа")
    left_day: int = Field(..., gt=0, description="Количество дней подписки")
    server_id: Optional[int] = Field(None, description="ID сервера (опционально)")

class PromoTariffSend(BaseModel):
    promo_id: int = Field(..., description="ID промо-тарифа")
    telegram_id: int = Field(..., description="Telegram ID пользователя")

@router.get("/", response_model=List[Dict])
async def get_promo_tariffs(db: Database = Depends(get_db)):
    """
    Получение списка всех активных промо-тарифов
    """
    try:
        tariffs = await db.get_all_promo_tariffs()
        return tariffs
    except Exception as e:
        logger.error(f"Ошибка при получении списка промо-тарифов: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=Dict)
async def create_promo_tariff(
    promo: PromoTariffCreate,
    db: Database = Depends(get_db)
):
    """
    Создание нового промо-тарифа
    
    - **name**: Название промо-тарифа
    - **description**: Описание промо-тарифа (опционально)
    - **left_day**: Количество дней подписки
    - **server_id**: ID сервера (опционально)
    """
    try:
        success = await db.add_promo_tariff(
            name=promo.name,
            description=promo.description,
            left_day=promo.left_day,
            server_id=promo.server_id
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Не удалось создать промо-тариф")
        
        return {
            "message": "Промо-тариф успешно создан",
            "success": True,
            "name": promo.name,
            "left_day": promo.left_day,
            "server_id": promo.server_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании промо-тарифа: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{promo_id}", response_model=Dict)
async def disable_promo_tariff(
    promo_id: int,
    db: Database = Depends(get_db)
):
    """
    Деактивация промо-тарифа
    
    - **promo_id**: ID промо-тарифа для деактивации
    """
    try:
        success = await db.disable_promo_tariff(promo_id)
        if not success:
            raise HTTPException(status_code=404, detail="Промо-тариф не найден или уже деактивирован")
        
        return {
            "message": "Промо-тариф успешно деактивирован",
            "success": True,
            "promo_id": promo_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при деактивации промо-тарифа {promo_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send", response_model=Dict)
async def send_promo_tariff(
    promo: PromoTariffSend,
    db: Database = Depends(get_db)
):
    """
    Отправка промо-тарифа пользователю. Только запись в БД без создания пользователя на сервере.
    Для полной активации с созданием пользователя на сервере используйте /send-with-server
    
    - **promo_id**: ID промо-тарифа
    - **telegram_id**: Telegram ID пользователя
    """
    try:
        success = await db.send_promo_tariff(
            promo_id=promo.promo_id,
            user_id=promo.telegram_id
        )
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail="Не удалось отправить промо-тариф. Возможно, закончился лимит активаций или тариф недоступен"
            )
        
        return {
            "message": "Промо-тариф успешно отправлен пользователю (только запись в БД)",
            "success": True,
            "promo_id": promo.promo_id,
            "telegram_id": promo.telegram_id
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при отправке промо-тарифа {promo.promo_id} пользователю {promo.telegram_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/send-with-server", response_model=Dict)
async def send_promo_tariff_with_server(
    promo: PromoTariffSend,
    db: Database = Depends(get_db)
):
    """
    Отправка промо-тарифа пользователю с созданием пользователя на сервере XUI
    
    - **promo_id**: ID промо-тарифа
    - **telegram_id**: Telegram ID пользователя
    """
    try:
        async def get_promo_tariff(promo_id: int):
            async with aiosqlite.connect(db.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute("""
                    SELECT *
                    FROM tariff_promo
                    WHERE id = ? AND is_enable = 1
                """, (promo_id,))
                tariff = await cursor.fetchone()
                return dict(tariff) if tariff else None
        
        async def get_user(telegram_id: int):
            async with aiosqlite.connect(db.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute("""
                    SELECT *
                    FROM user
                    WHERE telegram_id = ? AND is_enable = 1
                """, (telegram_id,))
                user = await cursor.fetchone()
                return dict(user) if user else None
        
        async def get_server(server_id: int):
            async with aiosqlite.connect(db.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute("""
                    SELECT *
                    FROM server_settings
                    WHERE id = ?
                """, (server_id,))
                server = await cursor.fetchone()
                return dict(server) if server else None
        
        async def get_bot_token():
            async with aiosqlite.connect(db.db_path) as conn:
                cursor = await conn.execute("SELECT bot_token FROM bot_settings WHERE is_enable = 1")
                result = await cursor.fetchone()
                if not result:
                    raise HTTPException(status_code=500, detail="Токен бота не найден")
                return result[0]
        
        tariff = await get_promo_tariff(promo.promo_id)
        if not tariff:
            raise HTTPException(status_code=404, detail="Промо-тариф не найден или неактивен")
        
        user = await get_user(promo.telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден или неактивен")
        
        server = await get_server(tariff['server_id'])
        if not server:
            raise HTTPException(status_code=404, detail="Сервер не найден")
        
        end_date = datetime.now() + timedelta(days=tariff['left_day'])
        vless_link = await xui_manager.create_trial_user(server, tariff, user['telegram_id'])
        
        if not vless_link:
            raise HTTPException(status_code=500, detail="Ошибка при создании конфигурации на сервере")
        
        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute("""
                INSERT INTO user_subscription 
                (user_id, tariff_id, server_id, end_date, vless, is_active)
                VALUES (?, ?, ?, ?, ?, 1)
            """, (user['telegram_id'], tariff['id'], tariff['server_id'], 
                  end_date.strftime('%Y-%m-%d %H:%M:%S'), vless_link))
            await conn.commit()
        
        try:
            bot_token = await get_bot_token()
            bot = Bot(token=bot_token)
            
            user_message = (
                f"🎁 Вам предоставлен промо-тариф!\n\n"
                f"Тариф: {tariff['name']}\n"
                f"Срок действия: {tariff['left_day']} дней\n"
                f"Дата окончания: {end_date.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                f"Ваша конфигурация:\n<code>{vless_link}</code>"
            )
            
            await bot.send_message(
                chat_id=user['telegram_id'],
                text=user_message,
                parse_mode="HTML"
            )
            logger.info(f"Отправлено уведомление пользователю {user['telegram_id']} о промо-тарифе")
            
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления пользователю: {e}")
        
        return {
            "message": "Промо-тариф успешно отправлен пользователю",
            "success": True,
            "promo_id": promo.promo_id,
            "telegram_id": promo.telegram_id,
            "username": user.get('username'),
            "end_date": end_date.strftime('%Y-%m-%d %H:%M:%S'),
            "vless_link": vless_link
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при отправке промо-тарифа {promo.promo_id} пользователю {promo.telegram_id} с созданием на сервере: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
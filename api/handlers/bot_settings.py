from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Dict, Optional
import sys
from loguru import logger

from pathlib import Path
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))

from handlers.database import Database

router = APIRouter(
    prefix="/bot-settings",
    tags=["bot-settings"],
    responses={404: {"description": "Настройки бота не найдены"}},
)

async def get_db():
    return Database()

class BotSettingsUpdate(BaseModel):
    bot_token: Optional[str] = None
    admin_id: Optional[str] = None
    chat_id: Optional[str] = None
    chanel_id: Optional[str] = None
    is_enable: Optional[bool] = None
    reg_notify: Optional[int] = None
    pay_notify: Optional[int] = None

@router.get("/", response_model=Dict)
async def get_bot_settings_api(db: Database = Depends(get_db)):
    """
    Получение текущих настроек бота
    """
    try:
        settings = await db.get_bot_settings_api()
        if not settings:
            raise HTTPException(status_code=404, detail="Настройки бота не найдены")
        
            
        if 'bot_token' in settings:
            token = settings['bot_token']   
            if token and len(token) > 10:
                settings['bot_token'] = f"{token[:5]}...{token[-5:]}"
        
        return {
            "settings": settings,
            "success": True
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении настроек бота: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/", response_model=Dict)
async def update_bot_settings(
    settings: BotSettingsUpdate,
    db: Database = Depends(get_db)
):
    """
    Обновление настроек бота
    
    - **bot_token**: Токен бота (опционально)
    - **admin_id**: ID администратора (опционально)
    - **chat_id**: ID чата (опционально)
    - **chanel_id**: ID канала (опционально)
    - **is_enable**: Статус активности (опционально)
    - **reg_notify**: Флаг уведомлений о регистрации (0 - выкл, 1 - вкл) (опционально)
    - **pay_notify**: Флаг уведомлений о платежах (0 - выкл, 1 - вкл) (опционально)
    """
    try:
        current_settings = await db.get_bot_settings_api()
        
        if not current_settings:
            if not settings.bot_token or not settings.admin_id:
                raise HTTPException(
                    status_code=400, 
                    detail="При первоначальной настройке требуется указать bot_token и admin_id"
                )
            
            success = await db.create_bot_settings(
                bot_token=settings.bot_token,
                admin_id=settings.admin_id,
                chat_id=settings.chat_id,
                chanel_id=settings.chanel_id,
                is_enable=settings.is_enable if settings.is_enable is not None else True,
                reg_notify=settings.reg_notify if settings.reg_notify is not None else 0,
                pay_notify=settings.pay_notify if settings.pay_notify is not None else 0
            )
            
            if not success:
                raise HTTPException(status_code=500, detail="Не удалось создать настройки бота")
            
            return {
                "message": "Настройки бота успешно созданы",
                "success": True
            }
        else:
            success = await db.update_bot_settings(
                bot_token=settings.bot_token,
                admin_id=settings.admin_id,
                chat_id=settings.chat_id,
                chanel_id=settings.chanel_id,
                is_enable=settings.is_enable,
                reg_notify=settings.reg_notify,
                pay_notify=settings.pay_notify
            )
            
            if not success:
                raise HTTPException(status_code=500, detail="Не удалось обновить настройки бота")
            
            return {
                "message": "Настройки бота успешно обновлены",
                "success": True
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении настроек бота: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
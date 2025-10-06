from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict
import secrets
import string
from loguru import logger
import os

from handlers.database import Database, db

router = APIRouter(
    prefix="/setup",
    tags=["setup"]
)

async def get_db():
    return db

class InitialSetup(BaseModel):
    admin_name: str
    init_code: str

@router.post("/init-api", response_model=Dict)
async def initialize_api(setup: InitialSetup, db: Database = Depends(get_db)):
    """
    Инициализация API и создание первого API ключа.
    Этот маршрут доступен только при первом запуске или когда нет активных ключей.
    
    - **admin_name**: Имя администратора
    - **init_code**: Код инициализации (должен совпадать с переменной окружения API_INIT_CODE)
    """
    try:
        init_code = os.environ.get("API_INIT_CODE", "initial-setup-code")
        if setup.init_code != init_code:
            raise HTTPException(status_code=403, detail="Неверный код инициализации")
        
        keys = await db.get_all_api_keys()
        active_keys = [k for k in keys if k['is_enable']]
        
        if active_keys:
            raise HTTPException(
                status_code=400,
                detail="Нельзя выполнить инициализацию: уже есть активные API ключи"
            )
        
        alphabet = string.ascii_letters + string.digits
        key = ''.join(secrets.choice(alphabet) for _ in range(32))
        
        success = await db.add_api_key(f"Admin: {setup.admin_name}", key)
        
        if not success:
            raise HTTPException(status_code=500, detail="Не удалось создать API ключ")
        
        return {
            "message": "API успешно инициализирован",
            "admin_name": setup.admin_name,
            "api_key": key,
            "note": "Сохраните этот ключ в надежном месте, он понадобится для дальнейшей работы с API"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при инициализации API: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
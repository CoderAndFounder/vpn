from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional, Dict
import secrets
import string
from loguru import logger

from api.middleware.auth import get_api_key
from handlers.database import Database, db

router = APIRouter(
    prefix="/api-keys",
    tags=["api-keys"],
    dependencies=[Depends(get_api_key)]
)

async def get_db():
    return db

class ApiKeyBase(BaseModel):
    name: str

class ApiKeyCreate(ApiKeyBase):
    pass

class ApiKey(ApiKeyBase):
    id: int
    key: str
    is_enable: bool
    date: str
    
    class Config:
        orm_mode = True

@router.get("/", response_model=List[ApiKey])
async def get_all_api_keys(db: Database = Depends(get_db)):
    """
    Получение списка всех API ключей.
    Требует авторизации существующим API ключом.
    """
    try:
        keys = await db.get_all_api_keys()
        return keys
    except Exception as e:
        logger.error(f"Ошибка при получении списка API ключей: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=Dict)
async def create_api_key(key_data: ApiKeyCreate, db: Database = Depends(get_db)):
    """
    Создание нового API ключа.
    Требует авторизации существующим API ключом.
    
    - **name**: Название/описание ключа
    """
    try:
        alphabet = string.ascii_letters + string.digits
        key = ''.join(secrets.choice(alphabet) for _ in range(32))
        
        success = await db.add_api_key(key_data.name, key)
        
        if not success:
            raise HTTPException(status_code=400, detail="Не удалось создать API ключ")
        
        return {
            "name": key_data.name,
            "key": key,
            "message": "API ключ успешно создан"
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании API ключа: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{key_id}", response_model=Dict)
async def disable_api_key(key_id: int, db: Database = Depends(get_db)):
    """
    Отключение API ключа.
    Требует авторизации существующим API ключом.
    
    - **key_id**: ID ключа для отключения
    """
    try:
        success = await db.disable_api_key(key_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="API ключ не найден или уже отключен")
        
        return {"message": "API ключ успешно отключен"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при отключении API ключа {key_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
from fastapi import Depends, HTTPException, Security
from fastapi.security.api_key import APIKeyHeader
from typing import Optional
from loguru import logger
from handlers.database import Database

API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_db():
    return Database()

async def get_api_key(
    api_key_header: str = Security(API_KEY_HEADER),
    db: Database = Depends(get_db)
):
    if not api_key_header:
        raise HTTPException(
            status_code=401,
            detail="API ключ отсутствует в заголовке X-API-Key"
        )
    
    api_key_info = await db.get_api_key(api_key_header)
    
    if not api_key_info:
        raise HTTPException(
            status_code=403,
            detail="Недействительный или отключенный API ключ"
        )
    
    return api_key_info 
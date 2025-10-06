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
    prefix="/servers",
    tags=["servers"],
    responses={404: {"description": "Сервер не найден"}},
)

async def get_db():
    return Database()

class ServerBase(BaseModel):
    name: str
    url: str
    port: str
    secret_path: str
    username: str
    password: str
    ip: Optional[str] = None
    inbound_id: Optional[int] = None
    protocol: Optional[str] = "vless"
    is_enable: Optional[bool] = True

class ServerCreate(BaseModel):
    name: str
    url: str
    port: str
    secret_path: str
    username: str
    password: str
    inbound_id: int
    protocol: Optional[str] = "vless"
    ip: Optional[str] = None

class Server(ServerBase):
    id: int
    
    class Config:
        orm_mode = True

class ServerUpdate(BaseModel):
    name: Optional[str] = None
    ip: Optional[str] = None
    port: Optional[str] = None
    inbound_id: Optional[int] = None
    is_enable: Optional[bool] = None
    inbound_id_promo: Optional[int] = None

class ServerTotalEarningsStats(BaseModel):
    server_name: str
    total_subscriptions: int
    total_earnings: int

class ServerSubscriptionsStats(BaseModel):
    server_id: int
    server_name: str
    subscriptions_count: int

@router.get("/", response_model=List[Server])
async def get_servers(
    is_active: Optional[bool] = None,
    db: Database = Depends(get_db)
):
    """
    Получение списка серверов.
    
    - **is_active**: Фильтр по статусу активности
    """
    try:
        if is_active:
            servers = await db.get_active_servers()
        else:
            servers = await db.get_all_servers()
        return servers
    except Exception as e:
        logger.error(f"Ошибка при получении серверов: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{server_id}", response_model=Server)
async def get_server(server_id: int, db: Database = Depends(get_db)):
    """
    Получение информации о сервере по его ID.
    
    - **server_id**: ID сервера
    """
    try:
        server = await db.get_server(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Сервер не найден")
        return server
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении сервера {server_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=Dict)
async def add_server(server: ServerCreate, db: Database = Depends(get_db)):
    """
    Добавление нового сервера.
    
    - **name**: Название сервера
    - **url**: URL сервера
    - **port**: Порт
    - **secret_path**: Секретный путь
    - **username**: Имя пользователя для доступа
    - **password**: Пароль для доступа
    - **inbound_id**: ID входящего соединения
    - **protocol**: Протокол (по умолчанию vless)
    - **ip**: IP-адрес сервера (опционально)
    """
    try:
        success = await db.add_server(
            url=server.url,
            port=server.port,
            secret_path=server.secret_path,
            username=server.username,
            password=server.password,
            name=server.name,
            inbound_id=server.inbound_id,
            protocol=server.protocol,
            ip=server.ip
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Не удалось добавить сервер")
        
        servers = await db.get_all_servers()
        for srv in servers:
            if (srv.get('name') == server.name and 
                srv.get('url') == server.url and 
                srv.get('port') == server.port):
                return srv
        
        return {"message": "Сервер успешно добавлен", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при добавлении сервера: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{server_id}", response_model=Dict)
async def delete_server(server_id: int, db: Database = Depends(get_db)):
    """
    Удаление сервера и отключение всех связанных тарифов.
    
    - **server_id**: ID сервера для удаления
    
    Returns:
        {
            "success": bool,
            "message": str,
            "server_name": str,
            "disabled_tariffs_count": int
        }
    """
    try:
        server = await db.get_server_settings(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Сервер не найден")
        
        result = await db.delete_server(server_id)
        
        if not result["success"]:
            raise HTTPException(status_code=400, detail="Не удалось удалить сервер")
        
        return {
            "success": True,
            "message": f"Сервер «{result['server_name']}» успешно удален",
            "server_name": result["server_name"],
            "disabled_tariffs_count": result["disabled_tariffs_count"]
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при удалении сервера {server_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{server_id}", response_model=Dict)
async def update_server(
    server_id: int, 
    server_data: ServerUpdate,
    db: Database = Depends(get_db)
):
    """
    Обновление настроек сервера
    
    - **server_id**: ID сервера для обновления
    - **name**: Новое название сервера (опционально)
    - **ip**: Новый IP-адрес сервера (опционально)
    - **port**: Новый порт сервера (опционально)
    - **inbound_id**: Новый ID входящего соединения (опционально)
    - **is_enable**: Новый статус активности сервера (опционально)
    - **inbound_id_promo**: Новый ID входящего соединения для промо (опционально)
    """
    try:
        server = await db.get_server_settings(server_id)
        if not server:
            raise HTTPException(status_code=404, detail="Сервер не найден")
        
        success = await db.update_server(
            server_id=server_id,
            name=server_data.name,
            ip=server_data.ip,
            port=server_data.port,
            inbound_id=server_data.inbound_id,
            is_enable=server_data.is_enable,
            inbound_id_promo=server_data.inbound_id_promo
        )
        
        if not success:
            raise HTTPException(status_code=400, detail="Не удалось обновить сервер")
        
        updated_server = await db.get_server_settings(server_id)
        
        return {
            "message": "Сервер успешно обновлен",
            "success": True,
            "server": updated_server
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении сервера {server_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/subscriptions/stats", response_model=List[ServerSubscriptionsStats])
async def get_servers_subscriptions_stats(db: Database = Depends(get_db)):
    """
    Получение статистики по количеству активных подписок на каждом сервере.
    
    Returns:
        List[ServerSubscriptionsStats]: Список серверов с количеством активных подписок
    """
    try:
        stats = await db.get_servers_subscriptions_count()
        return stats
    except Exception as e:
        logger.error(f"Ошибка при получении статистики подписок на серверах: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 

@router.get("/earnings/stats", response_model=List[ServerTotalEarningsStats])
async def get_servers_total_earnings(db: Database = Depends(get_db)):
    """
    Получение статистики по общей сумме заработка на каждом сервере.
    
    Returns:
        List[ServerTotalEarningsStats]: Список серверов с общей суммой заработка
    """
    try:
        stats = await db.get_servers_total_earnings()
        return stats
    except Exception as e:
        logger.error(f"Ошибка при получении статистики общей суммы заработка на серверах: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
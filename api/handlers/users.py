from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel, Field, EmailStr
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import sys
import os
from loguru import logger
import random
import string
import hashlib
import json
import aiohttp

from pathlib import Path
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))

from handlers.database import Database

from handlers.x_ui import xui_manager

router = APIRouter(
    prefix="/users",
    tags=["users"],
    responses={404: {"description": "Пользователь не найден"}},
)

async def get_db():
    return Database()

class UserBase(BaseModel):
    username: Optional[str] = None
    telegram_id: int
    trial_period: Optional[bool] = False
    is_enable: Optional[bool] = True
    referral_code: Optional[str] = None
    referral_count: Optional[int] = 0
    referred_by: Optional[str] = None

class UserCreate(UserBase):
    pass

class User(UserBase):
    id: Optional[int] = None
    date: Optional[datetime] = None
    
    class Config:
        orm_mode = True

class UserUpdate(BaseModel):
    username: Optional[str] = None
    trial_period: Optional[bool] = None
    is_enable: Optional[bool] = None
    referral_count: Optional[int] = None

class BalanceUpdate(BaseModel):
    user_id: int
    amount: float
    type: str
    description: Optional[str] = None

class Transaction(BaseModel):
    id: int
    user_id: int
    amount: float
    type: str
    description: Optional[str] = None
    transaction_date: datetime

class Subscription(BaseModel):
    id: int
    user_id: int
    tariff_id: int
    server_id: int
    end_date: datetime
    vless_link: Optional[str] = None
    is_active: bool

class SubscriptionDueInNext10Days(BaseModel):
    telegram_id: int
    server_name: str
    tariff_name: str
    end_date: datetime
    end_date_formatted: str

class BalanceTransaction(BaseModel):
    id: int
    username: Optional[str] = None
    telegram_id: int
    amount: float
    type: str
    description: Optional[str] = None
    payment_id: Optional[str] = None
    created_at: datetime
    
class CreateUserPayload(BaseModel):
    email: str = Field(..., description="Email пользователя (будет использоваться как имя)")
    tariff_id: int = Field(..., description="ID тарифного плана")
    server_id: int = Field(..., description="ID сервера")
    telegram_id: Optional[int] = Field(None, description="Telegram ID пользователя (опционально)")
    username: Optional[str] = Field(None, description="Username пользователя (опционально)")

@router.get("/all", response_model=List[Optional[Dict]])
async def get_all_users(
    skip: int = 0,
    limit: int = 100,
    db: Database = Depends(get_db)
):
    """
    Получение списка всех пользователей с пагинацией.
    
    - **skip**: Количество пропускаемых записей (для пагинации)
    - **limit**: Максимальное количество возвращаемых записей (для пагинации)
    """
    try:
        users = await db.get_all_users()
        return users[skip:skip+limit]
    except Exception as e:
        logger.error(f"Ошибка при получении всех пользователей: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/", response_model=List[Optional[Dict]])
async def get_users(
    telegram_id: Optional[int] = None,
    db: Database = Depends(get_db)
):
    """
    Получение информации о пользователе по его Telegram ID.
    Если ID не указан, возвращает ошибку.
    
    - **telegram_id**: Telegram ID пользователя
    """
    try:
        if not telegram_id:
            raise HTTPException(status_code=400, detail="Необходимо указать telegram_id")
            
        user = await db.get_user(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        return [user]
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{telegram_id}", response_model=Optional[Dict])
async def get_user(telegram_id: int, db: Database = Depends(get_db)):
    """
    Получение информации о пользователе по его Telegram ID.
    
    - **telegram_id**: Telegram ID пользователя
    """
    try:
        user = await db.get_user(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        return user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении пользователя {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{telegram_id}", response_model=Optional[Dict])
async def update_user(
    telegram_id: int, 
    user_update: UserUpdate, 
    db: Database = Depends(get_db)
):
    """
    Обновление статуса триального периода пользователя.
    
    - **telegram_id**: Telegram ID пользователя
    - **user_update**: Данные для обновления
    """
    try:
        existing_user = await db.get_user(telegram_id)
        if not existing_user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
            
        if user_update.trial_period is not None:
            updated = await db.update_user_trial_status(telegram_id, user_update.trial_period)
            if not updated:
                raise HTTPException(status_code=500, detail="Не удалось обновить статус триального периода")
        
        updated_user = await db.get_user(telegram_id)
        return updated_user
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении пользователя {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{telegram_id}/balance")
async def get_balance(telegram_id: int, db: Database = Depends(get_db)):
    """
    Получение баланса пользователя.
    """
    try:
        user = await db.get_user(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
            
        balance = await db.get_user_balance(telegram_id)
        return {"telegram_id": telegram_id, "balance": balance}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении баланса пользователя {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/balance/update")
async def update_balance(update: BalanceUpdate, db: Database = Depends(get_db)):
    """
    Обновление баланса пользователя.
    """
    try:
        success = await db.update_balance(
            user_id=update.user_id,
            amount=update.amount,
            type=update.type,
            description=update.description
        )
        if not success:
            raise HTTPException(status_code=400, detail="Не удалось обновить баланс")
        return {"message": "Баланс успешно обновлен", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при обновлении баланса: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{telegram_id}/transactions")
async def get_user_transactions(
    telegram_id: int,
    limit: int = 50,
    db: Database = Depends(get_db)
):
    """
    Получение транзакций пользователя.
    """
    try:
        transactions = await db.get_balance_transactions(telegram_id, limit)
        return transactions
    except Exception as e:
        logger.error(f"Ошибка при получении транзакций пользователя {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{telegram_id}/subscriptions", response_model=List[Dict])
async def get_user_subscriptions(telegram_id: int, db: Database = Depends(get_db)):
    """
    Получение всех подписок пользователя.
    
    - **telegram_id**: Telegram ID пользователя
    """
    try:
        user = await db.get_user(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
            
        subscriptions = await db.get_user_subscriptions(telegram_id)
        return subscriptions
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении подписок пользователя {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{telegram_id}")
async def disable_user(telegram_id: int, db: Database = Depends(get_db)):
    """
    Блокировка пользователя.
    
    - **telegram_id**: Telegram ID пользователя
    """
    try:
        user = await db.get_user(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        success = await db.disable_user(telegram_id)
        if not success:
            raise HTTPException(status_code=400, detail="Не удалось заблокировать пользователя")
        
        return {"message": "Пользователь успешно заблокирован", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при блокировке пользователя {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{telegram_id}/enable")
async def enable_user(telegram_id: int, db: Database = Depends(get_db)):
    """
    Разблокировка пользователя.
    
    - **telegram_id**: Telegram ID пользователя
    """
    try:
        user = await db.get_user(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
        
        success = await db.enable_user(telegram_id)
        if not success:
            raise HTTPException(status_code=400, detail="Не удалось разблокировать пользователя. Возможно, он уже разблокирован.")
        
        return {"message": "Пользователь успешно разблокирован", "success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при разблокировке пользователя {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{telegram_id}/payments", response_model=List[Dict])
async def get_user_payments(telegram_id: int, db: Database = Depends(get_db)):
    """
    Получение всех платежей пользователя.
    
    - **telegram_id**: Telegram ID пользователя
    """
    try:
        user = await db.get_user(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
            
        payments = await db.get_user_payments(telegram_id)
        return payments
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении платежей пользователя {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{telegram_id}/payments/sum", response_model=Dict)
async def get_user_payments_sum(telegram_id: int, db: Database = Depends(get_db)):
    """
    Получение общей суммы платежей пользователя.
    
    - **telegram_id**: Telegram ID пользователя
    """
    try:
        user = await db.get_user(telegram_id)
        if not user:
            raise HTTPException(status_code=404, detail="Пользователь не найден")
            
        result = await db.get_user_payments(telegram_id, only_sum=True)
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении суммы платежей пользователя {telegram_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create", response_model=Dict)
async def create_user_on_server(
    payload: CreateUserPayload,
    db: Database = Depends(get_db)
):
    """
    Создание пользователя на сервере 3xui
    
    - **email**: Email пользователя (будет использоваться как имя)
    - **tariff_id**: ID тарифного плана
    - **server_id**: ID сервера
    - **telegram_id**: Telegram ID пользователя (опционально)
    - **username**: Username пользователя (опционально)
    """
    try:
        tariff = await db.get_tariff(payload.tariff_id)
        if not tariff:
            raise HTTPException(status_code=404, detail=f"Тариф с ID {payload.tariff_id} не найден")
        
        if not tariff["is_enable"]:
            raise HTTPException(status_code=400, detail=f"Тариф с ID {payload.tariff_id} неактивен")
        
        server = await db.get_server_settings(payload.server_id)
        if not server:
            raise HTTPException(status_code=404, detail=f"Сервер с ID {payload.server_id} не найден")
        
        if not server["is_enable"]:
            raise HTTPException(status_code=400, detail=f"Сервер с ID {payload.server_id} неактивен")
        

        vless_link = await xui_manager.create_trial_user(
            server_settings=server,
            trial_settings=tariff,
            telegram_id=payload.telegram_id or random.randint(10000, 99999)
        )
        
        if not vless_link:
            raise HTTPException(status_code=500, detail="Не удалось создать пользователя на сервере")
        
        if "#" in vless_link:
            base_link, _ = vless_link.split("#", 1)
            custom_label = f"{payload.email}@api_create"
            vless_link = f"{base_link}#{custom_label}"
        
        if payload.telegram_id and payload.telegram_id > 0:
            user = await db.get_user(payload.telegram_id)
            
            if user:
                db_user_id = user["id"]
                logger.info(f"Пользователь с Telegram ID {payload.telegram_id} уже существует в БД, id: {db_user_id}")
            else:
                db_user_id = await db.add_user(
                    telegram_id=payload.telegram_id,
                    username=payload.username or ""
                )
                if not db_user_id:
                    logger.warning(f"Не удалось создать пользователя в базе: {payload.telegram_id}")
            
            if db_user_id:
                end_date = datetime.now() + timedelta(days=tariff["left_day"])
                
                subscription_id = await db.add_user_subscription(
                    user_id=payload.telegram_id,
                    tariff_id=payload.tariff_id,
                    server_id=payload.server_id,
                    end_date=end_date.strftime("%Y-%m-%d %H:%M:%S"),
                    vless=vless_link
                )
                
                if subscription_id:
                    logger.info(f"Создана подписка {subscription_id} для пользователя с Telegram ID {payload.telegram_id}")
                else:
                    logger.warning(f"Не удалось создать подписку для пользователя с Telegram ID {payload.telegram_id}")
        
        expiry_date = (datetime.now() + timedelta(days=tariff["left_day"])).strftime("%Y-%m-%d %H:%M:%S")
        
        response_data = {
            "success": True,
            "message": "Пользователь успешно создан на сервере",
            "user_data": {
                "email": payload.email,
                "expiry_date": expiry_date,
                "traffic_limit_gb": 0,
                "telegram_id": payload.telegram_id,
                "username": payload.username,
                "server_id": payload.server_id,
                "server_name": server["name"],
                "tariff_id": payload.tariff_id,
                "tariff_name": tariff["name"],
                "days": tariff["left_day"]
            },
            "connect_link": vless_link
        }
        
        return response_data
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при создании пользователя на сервере: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 

@router.get("/subscriptions/due-in-next-10-days", response_model=List[SubscriptionDueInNext10Days])
async def get_subscriptions_due_in_next_10_days(db: Database = Depends(get_db)):
    """
    Получение подписок, которые заканчиваются в течение ближайших 10 дней.
    """
    try:
        subscriptions = await db.get_subscriptions_due_in_next_10_days()
        return subscriptions
    except Exception as e:
        logger.error(f"Ошибка при получении подписок, которые заканчиваются в течение ближайших 10 дней: {e}")
        raise HTTPException(status_code=500, detail=str(e))
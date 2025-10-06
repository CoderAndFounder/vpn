from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Dict, Optional
import sys
from loguru import logger

from pathlib import Path
root_path = Path(__file__).parent.parent.parent
sys.path.insert(0, str(root_path))

from handlers.database import Database

router = APIRouter(
    prefix="/statistics",
    tags=["statistics"],
    responses={404: {"description": "Данные не найдены"}},
)

async def get_db():
    return Database()

@router.get("/users/count", response_model=Dict)
async def get_users_count(db: Database = Depends(get_db)):
    """
    Получение общего количества пользователей
    """
    try:
        count = await db.get_total_users_count()
        return {"total_users": count}
    except Exception as e:
        logger.error(f"Ошибка при получении количества пользователей: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/subscriptions/count", response_model=Dict)
async def get_subscriptions_count(db: Database = Depends(get_db)):
    """
    Получение общего количества подписок
    """
    try:
        count = await db.get_total_subscriptions_count()
        return {"total_subscriptions": count}
    except Exception as e:
        logger.error(f"Ошибка при получении количества подписок: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tariffs/popular", response_model=Dict)
async def get_popular_tariff(db: Database = Depends(get_db)):
    """
    Получение самого популярного тарифа
    """
    try:
        tariff = await db.get_most_popular_tariff()
        if not tariff:
            raise HTTPException(status_code=404, detail="Тарифы не найдены")
        return tariff
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении популярного тарифа: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/payments/last", response_model=Dict)
async def get_last_payment(db: Database = Depends(get_db)):
    """
    Получение информации о последнем платеже
    """
    try:
        payment = await db.get_last_payment()
        if not payment:
            raise HTTPException(status_code=404, detail="Платежи не найдены")
        return payment
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении последнего платежа: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/payments/total", response_model=Dict)
async def get_total_payments(db: Database = Depends(get_db)):
    """
    Получение общей суммы платежей
    """
    try:
        total = await db.get_total_payments_amount()
        return {"total_amount": total}
    except Exception as e:
        logger.error(f"Ошибка при получении общей суммы платежей: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/buyers/top", response_model=Dict)
async def get_top_buyer(db: Database = Depends(get_db)):
    """
    Получение информации о самом активном покупателе
    """
    try:
        buyer = await db.get_top_buyer()
        if not buyer:
            raise HTTPException(status_code=404, detail="Покупатели не найдены")
        return buyer
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Ошибка при получении топ покупателя: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary", response_model=Dict)
async def get_statistics_summary(db: Database = Depends(get_db)):
    """
    Получение общей статистики
    """
    try:
        total_users = await db.get_total_users_count()
        total_subscriptions = await db.get_total_subscriptions_count()
        popular_tariff = await db.get_most_popular_tariff()
        last_payment = await db.get_last_payment()
        total_amount = await db.get_total_payments_amount()
        top_buyer = await db.get_top_buyer()
        
        return {
            "total_users": total_users,
            "total_subscriptions": total_subscriptions,
            "popular_tariff": popular_tariff,
            "last_payment": last_payment,
            "total_amount": total_amount,
            "top_buyer": top_buyer
        }
    except Exception as e:
        logger.error(f"Ошибка при получении общей статистики: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user-balance", response_model=Dict)
async def get_user_balance_info(db: Database = Depends(get_db)):
    """
    Получение информации о балансах пользователей:
    - Количество пользователей с балансом
    - Общая сумма на счетах пользователей
    """
    try:
        balance_info = await db.get_user_balance_info()
        return {
            "users_count": balance_info["users_count"],
            "total_balance": balance_info["total_balance"],
            "success": True
        }
    except Exception as e:
        logger.error(f"Ошибка при получении информации о балансах пользователей: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/balance-transactions", response_model=Dict)
async def get_all_balance_transactions(
    skip: int = Query(0, ge=0, description="Количество пропускаемых записей (для пагинации)"),
    limit: int = Query(100, ge=1, le=1000, description="Максимальное количество возвращаемых записей (для пагинации)"),
    type_filter: Optional[str] = Query(None, description="Фильтр по типу транзакции"),
    db: Database = Depends(get_db)
):
    """
    Получение всех транзакций баланса с пагинацией.
    
    - **skip**: Количество пропускаемых записей (для пагинации)
    - **limit**: Максимальное количество возвращаемых записей (для пагинации)
    - **type_filter**: Фильтр по типу транзакции (опционально)
    
    Returns:
        Dict: Словарь со списком транзакций и информацией о пагинации
    """
    try:
        result = await db.get_all_balance_transactions(skip=skip, limit=limit, type_filter=type_filter)
        if not result:
            return {
                "transactions": [],
                "total_count": 0,
                "limit": limit,
                "offset": skip
            }
        
        return result
    except Exception as e:
        logger.error(f"Ошибка при получении всех транзакций баланса: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 
from typing import Optional, Dict, Tuple
from loguru import logger
import aiosqlite
from handlers.database import db

class PromoCodeManager:
    async def check_promo_code(self, promo_code: str) -> Tuple[bool, str, Optional[float]]:
        """
        Проверка промокода
        Returns: (is_valid, message, discount_percentage)
        """
        try:
            async with aiosqlite.connect(db.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute("""
                    SELECT * FROM promocodes 
                    WHERE promocod = ? 
                """, (promo_code,)) as cursor:
                    promo = await cursor.fetchone()
                    
                    if not promo:
                        return False, "Промокод не найден", None
                        
                    if not promo['is_enable']:
                        return False, "К сожалению промокод больше недоступен", None
                        
                    if promo['activation_total'] >= promo['activation_limit']:
                        return False, "У данного промокода закончились активации", None
                    
                    return True, "Промокод применен", promo['percentage']
                    
        except Exception as e:
            logger.error(f"Ошибка при проверке промокода: {e}")
            return False, "Произошла ошибка при проверке промокода", None

    async def apply_promo_code(self, promo_code: str, price: float) -> Tuple[bool, str, Optional[float]]:
        """
        Применение промокода и расчет новой цены
        Returns: (success, message, new_price)
        """
        is_valid, message, percentage = await self.check_promo_code(promo_code)
        
        if not is_valid:
            return False, message, None
            
        try:
            discount = price * (percentage / 100)
            new_price = price - discount
            
            async with aiosqlite.connect(db.db_path) as conn:
                await conn.execute("""
                    UPDATE promocodes 
                    SET activation_total = activation_total + 1 
                    WHERE promocod = ?
                """, (promo_code,))
                await conn.commit()
            
            return True, f"Промокод успешно применен! Скидка: {percentage}%", new_price
            
        except Exception as e:
            logger.error(f"Ошибка при применении промокода: {e}")
            return False, "Произошла ошибка при применении промокода", None

promo_manager = PromoCodeManager() 
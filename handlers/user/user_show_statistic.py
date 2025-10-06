from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger
import aiosqlite
from datetime import datetime
from handlers.database import db
from handlers.user.user_kb import get_back_keyboard

router = Router()

@router.callback_query(F.data == "lk_my_payments")
async def show_user_statistics(callback: CallbackQuery):
    """Отображение статистики платежей пользователя"""
    try:
        await callback.message.delete()
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            
            async with conn.execute(
                "SELECT username, date FROM user WHERE telegram_id = ?",
                (callback.from_user.id,)
            ) as cursor:
                user = await cursor.fetchone()
                
            if not user:
                await callback.message.answer(
                    "Не удалось найти информацию о пользователе",
                    reply_markup=get_back_keyboard()
                )
                return
                
            async with conn.execute(
                "SELECT SUM(price) as total FROM payments WHERE user_id = ?",
                (callback.from_user.id,)
            ) as cursor:
                total_payments = await cursor.fetchone()
                
            async with conn.execute("""
                SELECT p.*, t.name as tariff_name 
                FROM payments p
                JOIN tariff t ON p.tariff_id = t.id
                WHERE p.user_id = ?
                ORDER BY p.date DESC
                LIMIT 1
            """, (callback.from_user.id,)) as cursor:
                last_payment = await cursor.fetchone()

        message_text = (
            f"@{user['username']}, вот небольшой отчет:\n\n"
            f"<blockquote>"
        )
        
        if last_payment:
            message_text += (
                f"<b>Последний платеж:</b> {last_payment['price']} руб.\n"
                f"<b>Тариф:</b> {last_payment['tariff_name']}\n"
                f"<b>Дата:</b> {last_payment['date']}\n"
            )
        else:
            message_text += "У вас пока нет платежей\n"
            
        message_text += (
            f"<b>Всего потрачено:</b> {total_payments['total'] or 0} руб.\n"
            f"<b>Зарегистрирован с:</b> {user['date']}\n"
            f"</blockquote>"
        )

        await callback.message.answer(
            text=message_text,
            reply_markup=get_back_keyboard(),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Ошибка при отображении статистики: {e}")
        await callback.message.answer(
            "Произошла ошибка при получении статистики. Попробуйте позже.",
            reply_markup=get_back_keyboard()
        ) 
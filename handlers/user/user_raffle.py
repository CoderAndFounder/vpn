from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InputMediaPhoto
from loguru import logger
import aiosqlite
import os

from handlers.database import db
from handlers.user.user_kb import get_start_keyboard, get_back_keyboard, get_back_raffle_keyboard

router = Router()

@router.callback_query(F.data == "start_raffle")
async def show_user_raffle(callback: CallbackQuery):
    """Отображение информации о розыгрыше и билетах пользователя"""
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            
            cursor = await conn.execute("""
                SELECT * FROM raffles 
                WHERE status = 'active' 
                AND (end_date IS NULL OR end_date > datetime('now'))
                LIMIT 1
            """)
            raffle = await cursor.fetchone()
            
            if not raffle:
                await callback.answer("В данный момент нет активных розыгрышей", show_alert=True)
                return
            
            cursor = await conn.execute("""
                WITH user_stats AS (
                    SELECT 
                        telegram_id,
                        COUNT(*) as user_tickets,
                        (COUNT(*) * 100.0 / (SELECT COUNT(*) FROM raffle_tickets WHERE raffle_id = ?)) as win_chance
                    FROM raffle_tickets 
                    WHERE raffle_id = ?
                    GROUP BY telegram_id
                    ORDER BY win_chance DESC
                )
                SELECT 
                    user_tickets,
                    win_chance,
                    (SELECT COUNT(*) + 1 
                     FROM user_stats us2 
                     WHERE us2.win_chance > us1.win_chance) as top_position
                FROM user_stats us1
                WHERE telegram_id = ?
            """, (raffle['id'], raffle['id'], callback.from_user.id))
            stats = await cursor.fetchone()
            
            cursor = await conn.execute("""
                SELECT ticket_number 
                FROM raffle_tickets 
                WHERE telegram_id = ? AND raffle_id = ?
                ORDER BY created_at
            """, (callback.from_user.id, raffle['id']))
            tickets = await cursor.fetchall()
            
            tickets_text = ""
            if tickets:
                for i, ticket in enumerate(tickets, 1):
                    tickets_text += f"{i}. {ticket['ticket_number']}\n"
            else:
                tickets_text = "У вас пока нет билетов\n"

            cursor = await conn.execute("""
                SELECT COUNT(DISTINCT telegram_id) as total_participants
                FROM raffle_tickets
                WHERE raffle_id = ?
            """, (raffle['id'],))
            total = await cursor.fetchone()
            
            win_chance = stats['win_chance'] if stats else 0
            top_position = stats['top_position'] if stats else "-"
            total_participants = total['total_participants'] if total else 0

            message_text = (
                f"<blockquote>\n"
                f"<b>{raffle['name']}</b>\n"
                f"Описание: {raffle['description']}\n"
                f"</blockquote>\n"
                f"Твои билеты: <b>{len(tickets)} шт.</b>\n"
                f"Шанс на победу: <b>{win_chance:.1f}%</b>\n"
                f"Место в топе: <b>{top_position} из {total_participants}</b>\n"
                f"Список билетов:\n"
                f"<blockquote>\n"
                f"{tickets_text}"
                f"</blockquote>"
            )

            await callback.message.delete()

            image_path = 'static/images/raffles.jpg'
            if os.path.exists(image_path):
                await callback.message.answer_photo(
                    photo=FSInputFile(image_path),
                    caption=message_text,
                    parse_mode="HTML",
                    reply_markup=get_back_raffle_keyboard()
                )
            else:
                await callback.message.answer(
                    text=message_text,
                    parse_mode="HTML",
                    reply_markup=get_back_raffle_keyboard()
                )

    except Exception as e:
        logger.error(f"Ошибка при отображении розыгрыша: {e}")
        await callback.answer("Произошла ошибка при загрузке данных розыгрыша", show_alert=True) 
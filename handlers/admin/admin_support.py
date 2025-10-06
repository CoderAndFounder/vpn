from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger
import aiosqlite

from handlers.database import db
from handlers.admin.admin_kb import get_admin_keyboard

router = Router()

@router.callback_query(F.data == "admin_show_support")
async def show_support_info(callback: CallbackQuery):
    """Отображение информации о технической поддержке"""
    try:
        await callback.message.delete()
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("""
                SELECT message, bot_version, support_url
                FROM support_info
                LIMIT 1
            """) as cursor:
                support_info = await cursor.fetchone()

        if not support_info:
            await callback.message.answer(
                "❌ Информация о поддержке не найдена",
                reply_markup=get_admin_keyboard()
            )
            return

        message_text = (
            "Служба технической поддержки!\n"
            "<blockquote>"
            f"Версия бота: {support_info['bot_version']}\n"
            f"Описание: {support_info['message']}\n"
            f"Ссылка: {support_info['support_url']}\n"
            "</blockquote>"
        )

        await callback.message.answer(
            text=message_text,
            reply_markup=get_admin_keyboard(),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Ошибка при отображении информации о поддержке: {e}")
        await callback.message.answer(
            "Произошла ошибка при получении информации о поддержке",
            reply_markup=get_admin_keyboard()
        ) 
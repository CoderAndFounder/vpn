from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
import aiosqlite

from handlers.database import db
from handlers.admin.admin_kb import get_admin_keyboard, get_admin_show_trial_keyboard

router = Router()

@router.callback_query(F.data == "admin_show_trial")
async def show_trial_settings(callback: CallbackQuery):
    """Отображение настроек пробного периода"""
    try:
        await callback.message.delete()
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            
            async with conn.execute("""
                SELECT ts.*, ss.name as server_name
                FROM trial_settings ts
                JOIN server_settings ss ON ts.server_id = ss.id
                WHERE ts.is_enable = 1
                LIMIT 1
            """) as cursor:
                settings = await cursor.fetchone()

        if not settings:
            await callback.message.answer(
                "❌ Настройки пробного периода не найдены",
                reply_markup=get_admin_show_trial_keyboard()
            )
            return

        message_text = (
            "🕒 <b>Меню настроек пробного периода</b>\n\n"
            "<b>Текущие настройки:</b>\n"
            "<blockquote>"
            f"<b>ID:</b> {settings['id']}\n"
            f"<b>Наименование:</b> {settings['name']}\n"
            f"<b>Пробных дней:</b> {settings['left_day']}\n"
            f"<b>Страна:</b> {settings['server_name']}\n"
            "</blockquote>"
        )

        await callback.message.answer(
            text=message_text,
            reply_markup=get_admin_show_trial_keyboard(),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Ошибка при отображении настроек пробного периода: {e}")
        await callback.message.answer(
            "Произошла ошибка при получении настроек пробного периода",
            reply_markup=get_admin_show_trial_keyboard()
        )

@router.callback_query(F.data == "trial_back_to_admin")
async def process_back_to_admin(callback: CallbackQuery):
    """Обработчик кнопки возврата в админ-панель"""
    try:
        await callback.message.delete()
        admin_message = await db.get_bot_message("admin")
        text = admin_message['text'] if admin_message else "Панель администратора"
        
        await callback.message.answer(
            text=text,
            reply_markup=get_admin_show_trial_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при возврате в админ-панель: {e}")
        await callback.message.answer(
            "Произошла ошибка при возврате в админ-панель",
            reply_markup=get_admin_show_trial_keyboard()
        ) 
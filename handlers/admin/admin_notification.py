from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger
import aiosqlite

from handlers.database import db
from handlers.admin.admin_kb import get_admin_notifications_keyboard

router = Router()

@router.callback_query(F.data == "admin_show_notifications")
async def show_notifications_settings(callback: CallbackQuery):
    """Отображение настроек уведомлений"""
    try:
        await callback.message.delete()
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("""
                SELECT reg_notify, pay_notify
                FROM bot_settings
                LIMIT 1
            """) as cursor:
                settings = await cursor.fetchone()

        if not settings:
            await callback.message.answer(
                "❌ Настройки уведомлений не найдены",
                reply_markup=get_admin_notifications_keyboard()
            )
            return

        reg_notify = settings['reg_notify'] if settings['reg_notify'] != 0 else "Выключено"
        pay_notify = settings['pay_notify'] if settings['pay_notify'] != 0 else "Выключено"

        message_text = (
            "✨ <b>Меню настроек оповещений администратора</b> ✨\n\n"
            "📢 Здесь вы можете настроить уведомления для важных событий:\n"
            "- Оповещения при регистрации новых пользователей\n"
            "- Оповещения при успешной оплате счета\n\n"
            "<b>Текущие настройки:</b>\n"
            "<blockquote>"
            f"🔔 <b>Оповещение о регистрации:</b> {reg_notify}\n"
            f"💰 <b>Оповещение об оплате:</b> {pay_notify}\n"
            "</blockquote>"
        )

        await callback.message.answer(
            text=message_text,
            reply_markup=get_admin_notifications_keyboard(),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Ошибка при отображении настроек уведомлений: {e}")
        await callback.message.answer(
            "Произошла ошибка при получении настроек уведомлений",
            reply_markup=get_admin_notifications_keyboard()
        )

@router.callback_query(F.data == "notifications_back_to_admin")
async def process_back_to_admin(callback: CallbackQuery):
    """Обработчик кнопки возврата в админ-панель"""
    try:
        await callback.message.delete()
        admin_message = await db.get_bot_message("admin")
        text = admin_message['text'] if admin_message else "Панель администратора"
        
        await callback.message.answer(
            text=text,
            reply_markup=get_admin_notifications_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при возврате в админ-панель: {e}")
        await callback.message.answer(
            "Произошла ошибка при возврате в админ-панель",
            reply_markup=get_admin_notifications_keyboard()
        ) 
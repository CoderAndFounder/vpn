from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger
import aiosqlite
from datetime import datetime
from handlers.database import db
from handlers.user.user_kb import get_trial_vless_keyboard, get_subscriptions_keyboard, get_continue_merge_keyboard, get_no_subscriptions_keyboard

router = Router()

@router.callback_query(F.data == "lk_my_subscriptions")
async def show_user_subscriptions(callback: CallbackQuery):
    """Отображение активных подписок пользователя"""
    try:
        await callback.message.delete()
        
        async with aiosqlite.connect(db.db_path) as conn:
            async with conn.execute("SELECT datetime('now', 'localtime') as current_time") as cursor:
                current_time = await cursor.fetchone()
                logger.info(f"Текущее время: {current_time[0]}")

            conn.row_factory = aiosqlite.Row
            async with conn.execute("""
                SELECT us.*, s.name as server_name
                FROM user_subscription us
                JOIN server_settings s ON us.server_id = s.id
                WHERE us.user_id = ? AND us.is_active = 1
            """, (callback.from_user.id,)) as cursor:
                all_subs = await cursor.fetchall()
                for sub in all_subs:
                    logger.info(f"Подписка ID: {sub['id']}, end_date: {sub['end_date']}, is_active: {sub['is_active']}")

            deactivation_query = """
                UPDATE user_subscription 
                SET is_active = 0 
                WHERE user_id = ? 
                AND is_active = 1 
                AND datetime(end_date) < datetime('now', 'localtime')
            """
            logger.info(f"Выполняем запрос деактивации: {deactivation_query}")
            await conn.execute(deactivation_query, (callback.from_user.id,))
            await conn.commit()

            async with conn.execute("""
                SELECT 
                    us.*,
                    s.name as server_name,
                    datetime('now', 'localtime') as current_time,
                    datetime(us.end_date) as formatted_end_date,
                    CASE 
                        WHEN datetime(us.end_date) < datetime('now', 'localtime') THEN 0
                        ELSE CAST(
                            (julianday(us.end_date) - julianday('now', 'localtime')) * 24 
                            AS INTEGER
                        )
                    END as hours_left
                FROM user_subscription us
                JOIN server_settings s ON us.server_id = s.id
                WHERE us.user_id = ? AND us.is_active = 1
                ORDER BY us.end_date DESC
            """, (callback.from_user.id,)) as cursor:
                subscriptions = await cursor.fetchall()
                for sub in subscriptions:
                    logger.info(
                        f"После обновления - Подписка ID: {sub['id']}, "
                        f"end_date: {sub['end_date']}, "
                        f"formatted_end_date: {sub['formatted_end_date']}, "
                        f"current_time: {sub['current_time']}, "
                        f"hours_left: {sub['hours_left']}, "
                        f"is_active: {sub['is_active']}"
                    )

        if not subscriptions:
            await callback.message.answer(
                "🎉 Нет активных подписок? Не проблема!\n\n"
                "🔒 Подключайтесь к нашему сервису: шифруйте свои данные, обходите ограничения и наслаждайтесь полной свободой в интернете.\n\n"
                "💡 Оформи новую подписку прямо сейчас в разделе Тарифы, и получите доступ к миру без границ! 🌍✨",
                reply_markup=get_no_subscriptions_keyboard()
            )
            return

        message_text = "📋 <b>Ваши активные подписки:</b>\n"
        
        for sub in subscriptions:
            hours = sub['hours_left']
            days = hours // 24
            remaining_hours = hours % 24
            minutes = int((hours % 1) * 60)

            time_parts = []
            if days > 0:
                time_parts.append(f"{days} дн.")
            if remaining_hours > 0 or (days == 0 and minutes == 0):
                time_parts.append(f"{remaining_hours} ч.")
            if minutes > 0:
                time_parts.append(f"{minutes} мин.")
            time_str = " ".join(time_parts)

            end_date = sub['end_date'].split('.')[0]

            message_text += (
                f"\n<blockquote>"
                f"<b>Сервер:</b> {sub['server_name']}\n"
                f"<b>Действует:</b> {time_str}\n"
                f"<b>До:</b> {end_date}\n"
                f"<b>Ключ:</b> <code>{sub['vless']}</code>\n"
                f"</blockquote>\n"
            )

        await callback.message.answer(
            text=message_text,
            reply_markup=get_subscriptions_keyboard(),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Ошибка при отображении подписок: {e}")
        await callback.message.answer(
            "Произошла ошибка при получении списка подписок. Попробуйте позже.",
            reply_markup=get_trial_vless_keyboard()
        )

@router.callback_query(F.data == "merge_subscriptions")
async def merge_subscriptions(callback: CallbackQuery):
    """Обработчик кнопки объединения подписок"""
    try:
        await callback.message.delete()
        
        message_text = (
            "🔗 <b>Объединение подписок:</b>\n"
            "<blockquote>"
            "✨ Как это работает? \n"
            "Ваши активные подписки будут закодированы в формате Base64 🔐 и преобразованы в один удобный ключ. Этот ключ можно использовать в следующих поддерживаемых клиентах:\n"
        
            "1️⃣ Happ\n"
            "2️⃣ V2raytun\n"
            "3️⃣ Hiddify\n\n"
            "</blockquote>"
            "🌟 Это просто, удобно и позволяет быстро настроить доступ ко всем вашим подпискам!"
        )
        
        await callback.message.answer(
            text=message_text,
            reply_markup=get_continue_merge_keyboard(),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки объединения подписок: {e}")
        await callback.message.answer(
            "Произошла ошибка. Попробуйте позже.",
            reply_markup=get_subscriptions_keyboard()
        ) 
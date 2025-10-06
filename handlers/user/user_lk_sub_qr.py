from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, BufferedInputFile
from loguru import logger
import aiosqlite
from datetime import datetime
import qrcode
import io
from handlers.database import db
from handlers.user.user_kb import get_trial_vless_keyboard, get_subscriptions_keyboard, get_continue_merge_keyboard, get_no_subscriptions_keyboard

router = Router()

@router.callback_query(F.data == "lk_my_subscriptions")
async def show_user_subscriptions(callback: CallbackQuery):
    """Отображение активных подписок пользователя"""
    try:
        await callback.message.delete()
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("""
                SELECT us.*, s.name as server_name
                FROM user_subscription us
                JOIN server_settings s ON us.server_id = s.id
                WHERE us.user_id = ? AND us.is_active = 1
                ORDER BY us.end_date DESC
            """, (callback.from_user.id,)) as cursor:
                subscriptions = await cursor.fetchall()

        if not subscriptions:
            await callback.message.answer(
            "🎉 Нет активных подписок? Не проблема!\n\n"
            "🔒 Подключайтесь к нашему сервису: шифруйте свои данные, обходите ограничения и наслаждайтесь полной свободой в интернете.\n\n"
            "💡 Оформи новую подписку прямо сейчас в разделе Тарифы, и получите доступ к миру без границ! 🌍✨",
         reply_markup=get_no_subscriptions_keyboard()
        )
            return

        message_text = "📋 <b>Ваши активные подписки:</b>\n"
        
        for idx, sub in enumerate(subscriptions, 1):
            try:
                end_date_str = sub['end_date'].split('.')[0]
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S')
                time_left = end_date - datetime.now()
                
                days_left = time_left.days
                hours_left = time_left.seconds // 3600
                
                if days_left > 0:
                    time_str = f"{days_left} дн. {hours_left} ч."
                else:
                    time_str = f"{hours_left} ч."

                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(sub['vless'])
                qr.make(fit=True)
                
                img_byte_arr = io.BytesIO()
                qr.make_image(fill_color="black", back_color="white").save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)
                
                photo = BufferedInputFile(
                    img_byte_arr.getvalue(),
                    filename="qr_code.png"
                )
                
                message_text = (
                    f"<blockquote>"
                    f"<b>Страна:</b> {sub['server_name']}\n"
                    f"<b>Осталось:</b> {time_str}\n"
                    f"<b>Ключ:</b> <code>{sub['vless']}</code>\n"
                    f"</blockquote>\n"
                )
                
                await callback.message.answer_photo(
                    photo=photo,
                    caption=message_text,
                    parse_mode="HTML"
                )

            except Exception as date_error:
                logger.error(f"Ошибка при обработке даты для подписки: {date_error}")
                continue

        await callback.message.answer(
            text="Выберите действие:",
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
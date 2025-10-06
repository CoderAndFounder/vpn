from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger
import aiosqlite

from handlers.database import db
from handlers.admin.admin_kb import get_admin_payment_settings_keyboard

router = Router()

@router.callback_query(F.data == "admin_show_payment_settings")
async def show_payment_settings(callback: CallbackQuery):
    """Отображение настроек платежных систем"""
    try:
        if not await db.is_admin(callback.from_user.id):
            await callback.answer("У вас нет прав для выполнения этого действия")
            return

        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            
            yookassa = await conn.execute(
                "SELECT * FROM yookassa_settings WHERE is_enable = 1 LIMIT 1"
            )
            yookassa_settings = await yookassa.fetchone()
            
            crypto = await conn.execute(
                "SELECT * FROM crypto_settings WHERE is_enable = 1 LIMIT 1"
            )
            crypto_settings = await crypto.fetchone()
            
            codes = await conn.execute(
                "SELECT SUM(sum) as total FROM payments_code WHERE is_enable = 1"
            )
            codes_sum = await codes.fetchone()
            total_sum = codes_sum['total'] if codes_sum['total'] else 0

        yoomoney_text = "✅ Подключено\n" if yookassa_settings else "❌ Не настроено\n"
        if yookassa_settings:
            yoomoney_text += f"└ ID магазина: {yookassa_settings['shop_id']}\n"

        crypto_text = "✅ Подключено\n" if crypto_settings else "❌ Не настроено\n"
        if crypto_settings:
            crypto_text += f"└ Мин. сумма: {crypto_settings['min_amount']} USDT\n"

        message_text = (
            "💰 <b>Настройки приема платежей</b>\n\n"
            "<blockquote>"
            f"💳 <b>Настройки Юмани:</b>\n{yoomoney_text}\n"
            f"🪙 <b>Настройки Crypto Pay:</b>\n{crypto_text}\n"
            f"🎫 <b>Кодов оплаты на сумму:</b> {total_sum:.2f} ₽"
            "</blockquote>"
        )

        await callback.message.delete()
        await callback.message.answer(
            message_text,
            reply_markup=get_admin_payment_settings_keyboard(),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Ошибка при отображении платежных настроек: {e}")
        await callback.answer(
            "Произошла ошибка при получении настроек",
            show_alert=True
        ) 
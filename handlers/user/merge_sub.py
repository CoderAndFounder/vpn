import base64
import aiosqlite
from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardButton
from loguru import logger
import urllib.parse

from handlers.database import db
from handlers.user.user_kb import get_back_keyboard

router = Router()

async def get_merged_subscriptions(user_id: int) -> str | None:
    """Получение и кодирование всех активных подписок пользователя"""
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("""
                SELECT vless
                FROM user_subscription 
                WHERE user_id = ? AND is_active = 1
                ORDER BY end_date DESC
            """, (user_id,)) as cursor:
                subscriptions = await cursor.fetchall()

            if not subscriptions:
                return None

            combined_urls = "\n".join([sub['vless'] for sub in subscriptions])
            
            encoded_url = base64.b64encode(combined_urls.encode('utf-8')).decode('utf-8')
            
            return encoded_url

    except Exception as e:
        logger.error(f"Ошибка при получении и кодировании подписок: {e}")
        return None

@router.callback_query(F.data == "continue_merge")
async def process_continue_merge(callback: CallbackQuery):
    """Обработчик кнопки продолжения объединения подписок"""
    try:
        await callback.message.delete()

        encoded_subscriptions = await get_merged_subscriptions(callback.from_user.id)

        if not encoded_subscriptions:
            await callback.message.answer(
                "У вас нет активных подписок для объединения.",
                reply_markup=get_back_keyboard()
            )
            return

        url_encoded_subs = urllib.parse.quote(encoded_subscriptions)

        v2raytun_url = f"https://auto.syslab.space/v2raytun?vless={url_encoded_subs}"
        hiddify_url = f"https://auto.syslab.space/hiddify?vless={url_encoded_subs}"

        keyboard = get_back_keyboard()
        keyboard.inline_keyboard.insert(0, [
            InlineKeyboardButton(text="V2RayTun", url=v2raytun_url),
            InlineKeyboardButton(text="Hiddify", url=hiddify_url),
        ])

        message_text = (
            "<b>Результат объединения подписок:</b>\n\n"
            f"<blockquote>"
            f"<code>{encoded_subscriptions}</code>\n\n"
            "</blockquote>"
            "💡 Выберите приложение для автоматической настройки или скопируйте ключ вручную."
        )

        await callback.message.answer(
            text=message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Ошибка при объединении подписок: {e}")
        await callback.message.answer(
            "Произошла ошибка при объединении подписок. Попробуйте позже.",
            reply_markup=get_back_keyboard()
        ) 
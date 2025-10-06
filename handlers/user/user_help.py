from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, InlineKeyboardButton
from loguru import logger
import os
import aiosqlite
import urllib.parse

from handlers.database import db
from handlers.user.user_kb import get_help_keyboard

router = Router()

async def get_active_subscription(user_id: int) -> str | None:
    """Получение активной подписки пользователя"""
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("""
                SELECT vless
                FROM user_subscription
                WHERE user_id = ? AND is_active = 1
                ORDER BY end_date DESC
                LIMIT 1
            """, (user_id,)) as cursor:
                subscription = await cursor.fetchone()
                return subscription['vless'] if subscription else None
    except Exception as e:
        logger.error(f"Ошибка при получении подписки: {e}")
        return None

@router.callback_query(F.data == "start_help")
async def show_help(callback: CallbackQuery):
    """Отображение справочной информации"""
    try:
        await callback.message.delete()
        
        help_message = await db.get_bot_message('user_help')
        
        if not help_message:
            await callback.message.answer(
                "К сожалению, справочная информация временно недоступна.",
                reply_markup=get_help_keyboard()
            )
            return

        keyboard = get_help_keyboard()
        
        vless_link = await get_active_subscription(callback.from_user.id)
        if vless_link:
            encoded_vless = urllib.parse.quote(vless_link)
            v2raytun_url = f"https://auto.syslab.space/v2raytun?vless={encoded_vless}"
            hiddify_url = f"https://auto.syslab.space/hiddify?vless={encoded_vless}"
            keyboard.inline_keyboard.insert(0, [
                InlineKeyboardButton(text="V2RayTun", url=v2raytun_url),
                InlineKeyboardButton(text="Hiddify", url=hiddify_url),
            ])
            
        if help_message['image_path'] and os.path.exists(help_message['image_path']):
            await callback.message.answer_photo(
                photo=FSInputFile(help_message['image_path']),
                caption=f"<blockquote>{help_message['text']}</blockquote>",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await callback.message.answer(
                text=f"<blockquote>{help_message['text']}</blockquote>",
                reply_markup=keyboard,
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Ошибка при отображении справки: {e}")
        await callback.message.answer(
            "Произошла ошибка при загрузке справочной информации. Попробуйте позже.",
            reply_markup=get_help_keyboard()
        ) 
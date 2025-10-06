from aiogram import Router, F
import aiosqlite
from aiogram.types import CallbackQuery
from handlers.database import Database
from handlers.user.user_kb import get_back_to_start_keyboard
from loguru import logger

router = Router()

@router.callback_query(F.data == "referral_program")
async def show_referral_program(callback: CallbackQuery):
    """Показать информацию о реферальной программе"""
    try:
        await callback.message.delete()
        
        db = Database()
        
        conditions = await db.get_referral_conditions()
        
        if not conditions:
            await callback.message.answer(
                "❌ В данный момент реферальная программа неактивна.\n"
                "Пожалуйста, попробуйте позже.",
                reply_markup=get_back_to_start_keyboard()
            )
            return
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("""
                SELECT username, referral_code, referral_count 
                FROM user 
                WHERE telegram_id = ?
            """, (callback.from_user.id,)) as cursor:
                user_info = await cursor.fetchone()
            
            if not user_info:
                logger.error(f"Пользователь {callback.from_user.id} не найден в базе данных")
                await callback.message.answer(
                    "❌ Произошла ошибка при получении данных.\n"
                    "Пожалуйста, попробуйте позже.",
                    reply_markup=get_back_to_start_keyboard()
                )
                return
                
        conditions_text = ""
        for condition in conditions:
            conditions_text += (
                f"\n<blockquote>\n"
                f"Наименование: {condition['name']}\n"
                f"Описание: {condition['description']}\n"
                f"Требуется приглашений: {condition['invitations']}\n"
                f"Сумма бонуса: {condition['reward_sum']} руб.\n"
                f"</blockquote>"
            )
        
        bot_info = await callback.bot.get_me()
        ref_link = f"https://t.me/{bot_info.username}?start={user_info['referral_code']}"
        
        await callback.message.answer(
            "🎁 Реферальная программа\n\n"
            "Приглашайте друзей и получайте бонусы на свой баланс!\n\n"
            f"🔗 Ваша реферальная ссылка:\n<code>{ref_link}</code>\n\n"
            f"📊 Вы пригласили: {user_info['referral_count']} человек.\n\n"
            f"Условия получения бонусов:{conditions_text}",
            parse_mode="HTML",
            reply_markup=get_back_to_start_keyboard(),
            disable_web_page_preview=True
        )
        
        logger.info(f"Показана информация о реферальной программе пользователю {callback.from_user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка при показе реферальной программы: {e}")
        await callback.message.answer(
            "❌ Произошла ошибка при получении информации.\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=get_back_to_start_keyboard()
        ) 
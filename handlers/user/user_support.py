from aiogram import Router, F
from aiogram.types import CallbackQuery, Message, FSInputFile
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from loguru import logger
import os
import aiosqlite

from handlers.database import db
from handlers.user.user_kb import get_back_keyboard
from handlers.admin.admin_kb import get_admin_answer_keyboard

router = Router()

class SupportStates(StatesGroup):
    waiting_for_message = State()

@router.callback_query(F.data == "help_support")
async def show_support(callback: CallbackQuery, state: FSMContext):
    """Отображение информации о техподдержке"""
    try:
        await callback.message.delete()
        
        support_message = await db.get_bot_message('support_text')
        
        if not support_message:
            await callback.message.answer(
                "К сожалению, техподдержка временно недоступна.",
                reply_markup=get_back_keyboard()
            )
            return

        if support_message['image_path'] and os.path.exists(support_message['image_path']):
            await callback.message.answer_photo(
                photo=FSInputFile(support_message['image_path']),
                caption=f"<blockquote>{support_message['text']}</blockquote>",
                reply_markup=get_back_keyboard(),
                parse_mode="HTML"
            )
        else:
            await callback.message.answer(
                text=f"<blockquote>{support_message['text']}</blockquote>",
                reply_markup=get_back_keyboard(),
                parse_mode="HTML"
            )

        await state.set_state(SupportStates.waiting_for_message)

    except Exception as e:
        logger.error(f"Ошибка при отображении информации о поддержке: {e}")
        await callback.message.answer(
            "Произошла ошибка. Попробуйте позже.",
            reply_markup=get_back_keyboard()
        )

@router.message(SupportStates.waiting_for_message)
async def process_support_message(message: Message, state: FSMContext):
    """Обработка сообщения для техподдержки"""
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            
            async with conn.execute(
                "SELECT admin_id FROM bot_settings LIMIT 1"
            ) as cursor:
                settings = await cursor.fetchone()
                
            if not settings or not settings['admin_id']:
                await message.answer(
                    "Извините, но сейчас невозможно отправить сообщение. Попробуйте позже.",
                    reply_markup=get_back_keyboard()
                )
                await state.clear()
                return

            async with conn.execute("""
                SELECT u.username, u.date, 
                       COALESCE(t.name, 'Нет активного тарифа') as tariff_name,
                       us.vless, us.end_date
                FROM user u
                LEFT JOIN user_subscription us ON u.telegram_id = us.user_id AND us.is_active = 1
                LEFT JOIN tariff t ON us.tariff_id = t.id
                WHERE u.telegram_id = ?
                ORDER BY us.end_date DESC
            """, (message.from_user.id,)) as cursor:
                user_data = await cursor.fetchall()

            if not user_data:
                await message.answer(
                    "Произошла ошибка при получении данных пользователя.",
                    reply_markup=get_back_keyboard()
                )
                return

            subscriptions_info = ""
            for sub in user_data:
                if sub['vless']:
                    subscriptions_info += (
                        f"\n<b>Тариф:</b> {sub['tariff_name']}\n"
                        f"<b>Действует до:</b> {sub['end_date']}\n"
                        f"<b>Ключ:</b> <code>{sub['vless']}</code>\n"
                    )

            if not subscriptions_info:
                subscriptions_info = "\n<b>Активные подписки отсутствуют</b>"

            admin_message = (
                f"Пользователь @{user_data[0]['username']} обратился за помощью!\n"
                f"ID: {message.from_user.id}\n\n"
                f"<b>Дата регистрации:</b> {user_data[0]['date']}\n"
                f"<b>Подписки:</b>{subscriptions_info}\n\n"
                f"<b>Текст сообщения:</b>\n"
                f"<blockquote>{message.text}</blockquote>"
            )

            await message.bot.send_message(
                chat_id=settings['admin_id'],
                text=admin_message,
                parse_mode="HTML",
                reply_markup=get_admin_answer_keyboard()
            )

            await message.answer(
                "✅ Ваше сообщение успешно отправлено в техподдержку! "
                "Мы ответим вам в ближайшее время.",
                reply_markup=get_back_keyboard()
            )

    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения поддержки: {e}")
        await message.answer(
            "Произошла ошибка при отправке сообщения. Попробуйте позже.",
            reply_markup=get_back_keyboard()
        )
    finally:
        await state.clear() 
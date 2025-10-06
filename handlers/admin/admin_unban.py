from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import aiosqlite
from loguru import logger

from handlers.database import db
from handlers.admin.admin_kb import get_admin_users_keyboard, get_admin_users_keyboard_cancel

router = Router()

class UserUnbanStates(StatesGroup):
    waiting_for_username = State()

def get_cancel_keyboard():
    """Создание клавиатуры с кнопкой отмены"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Отмена", callback_data="cancel_unban")
    return keyboard.as_markup()

@router.callback_query(F.data == "unban_user")
async def process_unban_user(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки разблокировки пользователя"""
    try:
        await callback.message.delete()
        await callback.message.answer(
            "Введите имя пользователя для снятия ограничений",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(UserUnbanStates.waiting_for_username)
    except Exception as e:
        logger.error(f"Ошибка при начале процесса разблокировки: {e}")
        await callback.message.answer(
            "Произошла ошибка. Попробуйте позже.",
            reply_markup=get_admin_users_keyboard()
        )

@router.message(UserUnbanStates.waiting_for_username)
async def process_username_input(message: Message, state: FSMContext):
    """Обработчик ввода имени пользователя"""
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM user WHERE username = ?",
                (message.text,)
            ) as cursor:
                user = await cursor.fetchone()

            if not user:
                await message.answer(
                    "❌ Пользователь не найден",
                    reply_markup=get_admin_users_keyboard()
                )
                await state.clear()
                return

            await conn.execute(
                "UPDATE user SET is_enable = 1 WHERE username = ?",
                (message.text,)
            )
            await conn.commit()
            logger.info(f"Пользователь @{message.text} разблокирован")

            await message.answer(
                f"✅ Пользователь @{message.text} успешно разблокирован",
                reply_markup=get_admin_users_keyboard()
            )

    except Exception as e:
        logger.error(f"Ошибка при разблокировке пользователя: {e}")
        await message.answer(
            "Произошла ошибка при разблокировке пользователя",
            reply_markup=get_admin_users_keyboard()
        )
    finally:
        await state.clear()

@router.callback_query(F.data == "cancel_unban")
async def process_cancel_unban(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены разблокировки"""
    try:
        await callback.message.edit_text(
            "Операция отменена",
            reply_markup=get_admin_users_keyboard_cancel()
        )
    except Exception as e:
        logger.error(f"Ошибка при отмене разблокировки: {e}")
        await callback.message.edit_text(
            "Произошла ошибка",
            reply_markup=get_admin_users_keyboard()
        )
    finally:
        await state.clear() 
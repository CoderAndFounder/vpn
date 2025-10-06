from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import aiosqlite
from loguru import logger

from handlers.database import db
from handlers.admin.admin_kb import get_admin_users_keyboard, get_admin_users_keyboard_cancel, get_admin_reset_trial_keyboard

router = Router()

class UserResetTrialStates(StatesGroup):
    waiting_for_username = State()

def get_cancel_keyboard():
    """Создание клавиатуры с кнопкой отмены"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Отмена", callback_data="cancel_reset_trial")
    return keyboard.as_markup()

@router.callback_query(F.data == "reset_trial")
async def process_reset_trial(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки сброса триал периода"""
    try:
        await callback.message.delete()
        await callback.message.answer(
            "Введите имя пользователя для сброса пробного периода",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(UserResetTrialStates.waiting_for_username)
    except Exception as e:
        logger.error(f"Ошибка при начале процесса сброса триал периода: {e}")
        await callback.message.answer(
            "Произошла ошибка. Попробуйте позже.",
            reply_markup=get_admin_reset_trial_keyboard()
        )

@router.message(UserResetTrialStates.waiting_for_username)
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
                    reply_markup=get_admin_reset_trial_keyboard()
                )
                await state.clear()
                return

            await conn.execute(
                "UPDATE user SET trial_period = 0 WHERE username = ?",
                (message.text,)
            )
            await conn.commit()
            logger.info(f"Пользователь @{message.text} сброшен триал период")

            await message.answer(
                f"✅ <b>Пробный период успешно сброшен!</b>\n"
                f"Теперь пользователь @{message.text} может запросить пробный период заново",
                reply_markup=get_admin_reset_trial_keyboard(),
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Ошибка при сбросе триал периода: {e}")
        await message.answer(
            "Произошла ошибка при сбросе триал периода",
            reply_markup=get_admin_reset_trial_keyboard()
        )
    finally:
        await state.clear()

@router.callback_query(F.data == "cancel_reset_trial")
async def process_cancel_reset_trial(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены сброса триал периода"""
    try:
        await callback.message.edit_text(
            "Операция отменена",
            reply_markup=get_admin_users_keyboard_cancel()
        )
    except Exception as e:
        logger.error(f"Ошибка при отмене сброса триал периода: {e}")
        await callback.message.edit_text(
            "Произошла ошибка",
            reply_markup=get_admin_reset_trial_keyboard()
        )
    finally:
        await state.clear() 
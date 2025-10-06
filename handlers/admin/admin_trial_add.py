from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import aiosqlite
from loguru import logger

from handlers.database import db
from handlers.admin.admin_kb import get_admin_show_trial_keyboard

router = Router()

class TrialAddStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_days = State()

def get_servers_keyboard():
    """Создание клавиатуры с списком серверов"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔙 Отмена", callback_data="cancel_add_trial")
    return keyboard.as_markup()

@router.callback_query(F.data == "admin_add_trial")
async def start_add_trial(callback: CallbackQuery):
    """Начало процесса добавления пробного периода"""
    try:
        await callback.message.delete()
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("""
                SELECT id, name 
                FROM server_settings 
                WHERE is_enable = 1
            """) as cursor:
                servers = await cursor.fetchall()

        if not servers:
            await callback.message.answer(
                "❌ Нет доступных серверов",
                reply_markup=get_admin_show_trial_keyboard()
            )
            return

        keyboard = InlineKeyboardBuilder()
        for server in servers:
            keyboard.button(
                text=server['name'],
                callback_data=f"select_trial_server_{server['id']}"
            )
        keyboard.button(text="🔙 Отмена", callback_data="cancel_add_trial")
        keyboard.adjust(2, 1)

        await callback.message.answer(
            "Выберите сервер (Страну) для добавления пробного периода:",
            reply_markup=keyboard.as_markup()
        )

    except Exception as e:
        logger.error(f"Ошибка при начале добавления пробного периода: {e}")
        await callback.message.answer(
            "Произошла ошибка. Попробуйте позже.",
            reply_markup=get_admin_show_trial_keyboard()
        )

@router.callback_query(F.data.startswith("select_trial_server_"))
async def process_server_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора сервера"""
    try:
        server_id = int(callback.data.split('_')[-1])
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT name FROM server_settings WHERE id = ?",
                (server_id,)
            ) as cursor:
                server = await cursor.fetchone()

        if not server:
            await callback.message.edit_text(
                "Сервер не найден",
                reply_markup=get_admin_show_trial_keyboard()
            )
            return

        await state.update_data(server_id=server_id, server_name=server['name'])
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Отмена", callback_data="cancel_add_trial")

        await callback.message.edit_text(
            f"Вы выбрали {server['name']} для добавления пробного периода, "
            "введите наименование для добавления:",
            reply_markup=keyboard.as_markup()
        )
        
        await state.set_state(TrialAddStates.waiting_for_name)

    except Exception as e:
        logger.error(f"Ошибка при выборе сервера: {e}")
        await callback.message.edit_text(
            "Произошла ошибка при выборе сервера",
            reply_markup=get_admin_show_trial_keyboard()
        )

@router.message(TrialAddStates.waiting_for_name)
async def process_name_input(message: Message, state: FSMContext):
    """Обработка ввода наименования"""
    try:
        await state.update_data(name=message.text.strip())
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Отмена", callback_data="cancel_add_trial")

        await message.answer(
            "Введите кол-во пробных дней:",
            reply_markup=keyboard.as_markup()
        )
        
        await state.set_state(TrialAddStates.waiting_for_days)

    except Exception as e:
        logger.error(f"Ошибка при обработке наименования: {e}")
        await message.answer(
            "Произошла ошибка. Попробуйте позже.",
            reply_markup=get_admin_show_trial_keyboard()
        )
        await state.clear()

@router.message(TrialAddStates.waiting_for_days)
async def process_days_input(message: Message, state: FSMContext):
    """Обработка ввода количества дней"""
    try:
        days = int(message.text.strip())
        if days <= 0:
            raise ValueError("Количество дней должно быть положительным числом")

        data = await state.get_data()
        
        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute(
                "UPDATE trial_settings SET is_enable = 0 WHERE is_enable = 1"
            )
            
            await conn.execute("""
                INSERT INTO trial_settings (id, name, left_day, server_id, is_enable)
                VALUES ((SELECT COALESCE(MAX(id), 100) + 1 FROM trial_settings), ?, ?, ?, 1)
            """, (data['name'], days, data['server_id']))
            
            await conn.commit()

        message_text = (
            "✅ Пробный тарифный план\n"
            "<blockquote>"
            f"<b>Наименование:</b> {data['name']}\n"
            f"<b>Сроком на:</b> {days} д.\n"
            "</blockquote>\n"
            "Успешно добавлен!"
        )

        await message.answer(
            text=message_text,
            reply_markup=get_admin_show_trial_keyboard(),
            parse_mode="HTML"
        )
        logger.info(f"Добавлен новый пробный период: {data['name']}")

    except ValueError as ve:
        await message.answer(
            "Пожалуйста, введите корректное количество дней (целое положительное число)"
        )
        return
    except Exception as e:
        logger.error(f"Ошибка при добавлении пробного периода: {e}")
        await message.answer(
            "Произошла ошибка при добавлении пробного периода",
            reply_markup=get_admin_show_trial_keyboard()
        )
    finally:
        await state.clear()

@router.callback_query(F.data == "cancel_add_trial")
async def cancel_add_trial(callback: CallbackQuery, state: FSMContext):
    """Отмена добавления пробного периода"""
    await state.clear()
    await callback.message.edit_text(
        "Добавление пробного периода отменено",
        reply_markup=get_admin_show_trial_keyboard()
    ) 
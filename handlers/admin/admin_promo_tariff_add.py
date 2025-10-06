from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import aiosqlite
from loguru import logger

from handlers.database import db
from handlers.admin.admin_kb import get_admin_show_promo_tariff_keyboard, get_admin_users_keyboard_cancel

router = Router()

class PromoTariffStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_days = State()
    waiting_for_server = State()

def get_cancel_keyboard():
    """Создание клавиатуры с кнопкой отмены"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔙 Отмена", callback_data="cancel_add_promo_tariff")
    return keyboard.as_markup()

async def get_servers_keyboard():
    """Создание клавиатуры с серверами"""
    keyboard = InlineKeyboardBuilder()
    
    async with aiosqlite.connect(db.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        async with conn.execute("""
            SELECT id, name 
            FROM server_settings 
            WHERE is_enable = 1
        """) as cursor:
            servers = await cursor.fetchall()
            
    for server in servers:
        keyboard.button(
            text=server['name'],
            callback_data=f"select_promo_server:{server['id']}"
        )
    
    keyboard.button(text="🔙 Отмена", callback_data="cancel_add_promo_tariff")
    keyboard.adjust(2, 2)
    return keyboard.as_markup()

@router.callback_query(F.data == "admin_add_promo_tariff")
async def start_add_promo_tariff(callback: CallbackQuery, state: FSMContext):
    """Начало процесса добавления промо-тарифа"""
    try:
        await callback.message.delete()
        await callback.message.answer(
            "Введите наименование:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(PromoTariffStates.waiting_for_name)
    except Exception as e:
        logger.error(f"Ошибка при старте добавления промо-тарифа: {e}")
        await callback.message.answer(
            "Произошла ошибка. Попробуйте позже.",
            reply_markup=get_admin_show_promo_tariff_keyboard()
        )

@router.message(PromoTariffStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Обработка ввода наименования"""
    await state.update_data(name=message.text)
    await message.answer("Введите описание:", reply_markup=get_cancel_keyboard())
    await state.set_state(PromoTariffStates.waiting_for_description)

@router.message(PromoTariffStates.waiting_for_description)
async def process_description(message: Message, state: FSMContext):
    """Обработка ввода описания"""
    await state.update_data(description=message.text)
    data = await state.get_data()
    await message.answer(
        f"Введите количество промо дней в тарифе ({data['name']}):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(PromoTariffStates.waiting_for_days)

@router.message(PromoTariffStates.waiting_for_days)
async def process_days(message: Message, state: FSMContext):
    """Обработка ввода количества дней"""
    try:
        days = int(message.text)
        if days <= 0:
            await message.answer("Количество дней должно быть положительным числом. Попробуйте еще раз:")
            return
        
        await state.update_data(left_day=days)
        await message.answer(
            "Выберите сервер для создания промо тарифа:",
            reply_markup=await get_servers_keyboard()
        )
        await state.set_state(PromoTariffStates.waiting_for_server)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число дней:")

@router.callback_query(F.data.startswith("select_promo_server:"))
async def process_server_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора сервера и сохранение промо-тарифа"""
    try:
        server_id = int(callback.data.split(":")[1])
        data = await state.get_data()
        
        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute("""
                INSERT INTO tariff_promo (name, description, left_day, server_id, is_enable)
                VALUES (?, ?, ?, ?, 1)
            """, (data['name'], data['description'], data['left_day'], server_id))
            await conn.commit()

        await callback.message.edit_text(
            "✅ Промо-тариф успешно добавлен!",
            reply_markup=get_admin_users_keyboard_cancel()
        )
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении промо-тарифа: {e}")
        await callback.message.edit_text(
            "Произошла ошибка при сохранении промо-тарифа",
            reply_markup=get_admin_show_promo_tariff_keyboard()
        )
    finally:
        await state.clear()

@router.callback_query(F.data == "cancel_add_promo_tariff")
async def cancel_add_promo_tariff(callback: CallbackQuery, state: FSMContext):
    """Отмена добавления промо-тарифа"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Добавление промо-тарифа отменено",
        reply_markup=get_admin_show_promo_tariff_keyboard()
    ) 
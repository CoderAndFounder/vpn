from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
import aiosqlite
from loguru import logger
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
import random
import string

from handlers.database import db
from handlers.admin.admin_kb import get_admin_keyboard, get_promocodes_keyboard, get_promocodes_keyboard_delete

router = Router()

class PromoStates(StatesGroup):
    waiting_for_limit = State()
    waiting_for_percentage = State()
    waiting_for_delete = State()  

def generate_promocode(length=12):
    """Генерация случайного промокода"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

@router.callback_query(F.data == "admin_show_promocodes")
async def process_show_promocodes(callback: CallbackQuery):
    """Обработчик просмотра списка промокодов"""
    try:
        await callback.message.delete()

        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("""
                SELECT promocod, activation_limit, activation_total, percentage
                FROM promocodes
                WHERE is_enable = 1
                ORDER BY date DESC
            """) as cursor:
                promocodes = await cursor.fetchall()

        if not promocodes:
            message_text = "📋 *Список промокодов*\n\nАктивных промокодов нет"
        else:
            message_text = "📋 *Список активных промокодов:*\n\n"
            for promo in promocodes:
                remaining_activations = promo['activation_limit'] - promo['activation_total']
                message_text += (
                    f"🎟️ *Промокод:* `{promo['promocod']}`\n"
                    f"📊 Скидка: *{promo['percentage']}%*\n"
                    f"🔄 Лимит активаций: *{promo['activation_limit']}*\n"
                    f"✨ Осталось активаций: *{remaining_activations}*\n"
                    "───────────────────\n"
                )

        await callback.message.answer(
            text=message_text,
            parse_mode="Markdown",
            reply_markup=get_promocodes_keyboard()
        )

    except Exception as e:
        logger.error(f"Ошибка при получении списка промокодов: {e}")
        await callback.message.answer(
            "Произошла ошибка при получении списка промокодов",
            reply_markup=get_admin_keyboard()
        )

@router.callback_query(F.data == "promocodes_back_to_admin")
async def process_back_to_admin(callback: CallbackQuery):
    """Обработчик кнопки возврата в админ-панель"""
    try:
        await callback.message.delete()
        admin_message = await db.get_bot_message("admin")
        text = admin_message['text'] if admin_message else "Панель администратора"
        
        await callback.message.answer(
            text=text,
            reply_markup=get_admin_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при возврате в админ-панель: {e}")
        await callback.message.answer(
            "Произошла ошибка при возврате в админ-панель",
            reply_markup=get_admin_keyboard()
        )

@router.callback_query(F.data == "add_promocode")
async def process_add_promocode(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки добавления промокода"""
    try:
        await callback.message.delete()
        
        await callback.message.answer(
            "Для добавления промокода отправь мне кол-во активаций\nНапример 25"
        )
        
        await state.set_state(PromoStates.waiting_for_limit)
        
    except Exception as e:
        logger.error(f"Ошибка при начале создания промокода: {e}")
        await callback.message.answer(
            "Произошла ошибка. Попробуйте позже.",
            reply_markup=get_promocodes_keyboard()
        )

@router.message(PromoStates.waiting_for_limit)
async def process_activation_limit(message: Message, state: FSMContext):
    """Обработчик ввода количества активаций"""
    try:
        activation_limit = int(message.text)
        
        await state.update_data(activation_limit=activation_limit)
        
        await message.delete()
        
        await message.answer(
            "Отправь мне процент скидки который должен применятся для данного промокода"
        )
        
        await state.set_state(PromoStates.waiting_for_percentage)
        
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число.")
    except Exception as e:
        logger.error(f"Ошибка при обработке количества активаций: {e}")
        await message.answer(
            "Произошла ошибка. Попробуйте позже.",
            reply_markup=get_promocodes_keyboard()
        )
        await state.clear()

@router.message(PromoStates.waiting_for_percentage)
async def process_percentage(message: Message, state: FSMContext):
    """Обработчик ввода процента скидки"""
    try:
        percentage = float(message.text)
        
        data = await state.get_data()
        activation_limit = data['activation_limit']
        
        promocode = generate_promocode()
        
        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute("""
                INSERT INTO promocodes (promocod, activation_limit, percentage, is_enable)
                VALUES (?, ?, ?, 1)
            """, (promocode, activation_limit, percentage))
            await conn.commit()
        
        message_text = (
            "Все получилось!\n"
            "Новый промокод добавлен в базу\n"
            f"Промокод: {promocode}\n"
            f"Скидка: {percentage}%\n"
            f"Кол-во активаций: {activation_limit}"
        )
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Назад", callback_data="promocodes_back_to_admin")
        keyboard.adjust(1)
        
        await message.answer(
            text=message_text,
            reply_markup=keyboard.as_markup()
        )
        
        await state.clear()
        
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число.")
    except Exception as e:
        logger.error(f"Ошибка при создании промокода: {e}")
        await message.answer(
            "Произошла ошибка при создании промокода. Попробуйте позже.",
            reply_markup=get_promocodes_keyboard()
        )
        await state.clear()

@router.callback_query(F.data == "delete_promocode")
async def process_delete_promocode(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки удаления промокода"""
    try:
        await callback.message.delete()
        
        await callback.message.answer(
            "Введите промокод для удаления:"
        )
        
        await state.set_state(PromoStates.waiting_for_delete)
        
    except Exception as e:
        logger.error(f"Ошибка при начале удаления промокода: {e}")
        await callback.message.answer(
            "Произошла ошибка. Попробуйте позже.",
            reply_markup=get_promocodes_keyboard()
        )

@router.message(PromoStates.waiting_for_delete)
async def process_delete_promo_code(message: Message, state: FSMContext):
    """Обработчик ввода промокода для удаления"""
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            async with conn.execute(
                "SELECT promocod FROM promocodes WHERE promocod = ? AND is_enable = 1",
                (message.text,)
            ) as cursor:
                promo = await cursor.fetchone()
                
                if not promo:
                    await message.answer(
                        "❌ Промокод не найден или уже удален.",
                        reply_markup=get_promocodes_keyboard_delete()
                    )
                    await state.clear()
                    return
                
            await conn.execute(
                "UPDATE promocodes SET is_enable = 0 WHERE promocod = ?",
                (message.text,)
            )
            await conn.commit()
        
        await message.answer(
            f"✅ Промокод *{message.text}* успешно удален!",
            parse_mode="Markdown",
            reply_markup=get_promocodes_keyboard_delete()
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при удалении промокода: {e}")
        await message.answer(
            "Произошла ошибка при удалении промокода. Попробуйте позже.",
            reply_markup=get_promocodes_keyboard_delete()
        )
        await state.clear() 
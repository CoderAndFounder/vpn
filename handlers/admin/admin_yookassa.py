from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
import aiosqlite
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from handlers.database import db
from handlers.admin.admin_kb import get_admin_keyboard, get_yokassa_keyboard

router = Router()

class YookassaAddStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_shop_id = State()
    waiting_for_api_key = State()
    waiting_for_delete_shop_id = State()

@router.callback_query(F.data == "admin_show_yokassa")
async def show_yokassa_settings(callback: CallbackQuery):
    """Отображение настроек YooKassa"""
    try:
        await callback.message.delete()
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("""
                SELECT * FROM yookassa_settings 
                WHERE is_enable = 1 
                LIMIT 1
            """) as cursor:
                settings = await cursor.fetchone()

        if not settings:
            await callback.message.answer(
                "❌ Настройки YooKassa не найдены",
                reply_markup=get_yokassa_keyboard()
            )
            return

        message_text = (
            "<b>Текущие настройки YooKassa</b>\n\n"
            f"<b>Наименование:</b> {settings['name']}\n"
            f"<b>SHOP ID:</b> <code>{settings['shop_id']}</code>\n"
            f"<b>API:</b> <code>{settings['api_key']}</code>\n"
        )

        await callback.message.answer(
            text=message_text,
            reply_markup=get_yokassa_keyboard(),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Ошибка при отображении настроек YooKassa: {e}")
        await callback.message.answer(
            "Произошла ошибка при получении настроек YooKassa",
            reply_markup=get_admin_keyboard()
        )

@router.callback_query(F.data == "yokassa_back_to_admin")
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

@router.callback_query(F.data == "add_yokassa")
async def start_add_yokassa(callback: CallbackQuery, state: FSMContext):
    """Начало процесса добавления настроек YooKassa"""
    try:
        await callback.message.delete()
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Отмена", callback_data="cancel_add_yokassa")
        
        await callback.message.answer(
            "Введите наименование для настроек YooKassa:",
            reply_markup=keyboard.as_markup()
        )
        
        await state.set_state(YookassaAddStates.waiting_for_name)
        
    except Exception as e:
        logger.error(f"Ошибка при начале добавления настроек YooKassa: {e}")
        await callback.message.answer(
            "Произошла ошибка. Попробуйте позже.",
            reply_markup=get_yokassa_keyboard()
        )

@router.message(YookassaAddStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Обработка введенного наименования"""
    await state.update_data(name=message.text.strip())
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔙 Отмена", callback_data="cancel_add_yokassa")
    
    await message.answer(
        "Введите SHOP ID:",
        reply_markup=keyboard.as_markup()
    )
    await state.set_state(YookassaAddStates.waiting_for_shop_id)

@router.message(YookassaAddStates.waiting_for_shop_id)
async def process_shop_id(message: Message, state: FSMContext):
    """Обработка введенного SHOP ID"""
    await state.update_data(shop_id=message.text.strip())
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔙 Отмена", callback_data="cancel_add_yokassa")
    
    await message.answer(
        "Введите API KEY:",
        reply_markup=keyboard.as_markup()
    )
    await state.set_state(YookassaAddStates.waiting_for_api_key)

@router.message(YookassaAddStates.waiting_for_api_key)
async def process_api_key(message: Message, state: FSMContext):
    """Обработка введенного API KEY и сохранение настроек"""
    try:
        data = await state.get_data()
        api_key = message.text.strip()
        
        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute(
                "UPDATE yookassa_settings SET is_enable = 0 WHERE is_enable = 1"
            )
            
            await conn.execute("""
                INSERT INTO yookassa_settings 
                (name, shop_id, api_key, is_enable)
                VALUES (?, ?, ?, 1)
            """, (data['name'], data['shop_id'], api_key))
            await conn.commit()
        
        await message.answer(
            f"✅ Настройки для {data['name']} успешно добавлены.",
            reply_markup=get_yokassa_keyboard()
        )
        logger.info(f"Добавлены новые настройки YooKassa: {data['name']}")
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении настроек YooKassa: {e}")
        await message.answer(
            "Произошла ошибка при сохранении настроек. Попробуйте позже.",
            reply_markup=get_yokassa_keyboard()
        )
    finally:
        await state.clear()

@router.callback_query(F.data == "cancel_add_yokassa")
async def cancel_add_yokassa(callback: CallbackQuery, state: FSMContext):
    """Отмена добавления настроек"""
    await state.clear()
    await callback.message.edit_text(
        "Добавление настроек отменено",
        reply_markup=get_yokassa_keyboard()
    )

@router.callback_query(F.data == "delete_yokassa")
async def start_delete_yokassa(callback: CallbackQuery, state: FSMContext):
    """Начало процесса удаления настроек YooKassa"""
    try:
        await callback.message.delete()
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Отмена", callback_data="cancel_delete_yokassa")
        
        await callback.message.answer(
            "Введите SHOP ID для удаления настроек:",
            reply_markup=keyboard.as_markup()
        )
        
        await state.set_state(YookassaAddStates.waiting_for_delete_shop_id)
        
    except Exception as e:
        logger.error(f"Ошибка при начале удаления настроек YooKassa: {e}")
        await callback.message.answer(
            "Произошла ошибка. Попробуйте позже.",
            reply_markup=get_yokassa_keyboard()
        )

@router.message(YookassaAddStates.waiting_for_delete_shop_id)
async def process_delete_shop_id(message: Message, state: FSMContext):
    """Обработка введенного SHOP ID и удаление настроек"""
    try:
        shop_id = message.text.strip()
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            
            async with conn.execute(
                "SELECT name FROM yookassa_settings WHERE shop_id = ? AND is_enable = 1",
                (shop_id,)
            ) as cursor:
                settings = await cursor.fetchone()
                
            if not settings:
                await message.answer(
                    "❌ Активные настройки с таким SHOP ID не найдены.",
                    reply_markup=get_yokassa_keyboard()
                )
                await state.clear()
                return
                
            await conn.execute(
                "UPDATE yookassa_settings SET is_enable = 0 WHERE shop_id = ?",
                (shop_id,)
            )
            await conn.commit()
            
        await message.answer(
            f"✅ Настройки YooKassa для {settings['name']} успешно удалены.",
            reply_markup=get_yokassa_keyboard()
        )
        logger.info(f"Удалены настройки YooKassa для {settings['name']} (SHOP ID: {shop_id})")
        
    except Exception as e:
        logger.error(f"Ошибка при удалении настроек YooKassa: {e}")
        await message.answer(
            "Произошла ошибка при удалении настроек. Попробуйте позже.",
            reply_markup=get_yokassa_keyboard()
        )
    finally:
        await state.clear()

@router.callback_query(F.data == "cancel_delete_yokassa")
async def cancel_delete_yokassa(callback: CallbackQuery, state: FSMContext):
    """Отмена удаления настроек"""
    await state.clear()
    await callback.message.edit_text(
        "Удаление настроек отменено",
        reply_markup=get_yokassa_keyboard()
    ) 
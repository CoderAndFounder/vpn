from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
import json
import aiosqlite

from handlers.database import db
from handlers.admin.admin_kb import get_admin_keyboard
from handlers.crypto_pay import crypto_pay_manager, CryptoPayAPI

router = Router()

class CryptoPayState(StatesGroup):
    waiting_for_token = State()
    waiting_for_min_amount = State()
    waiting_for_assets = State()
    waiting_for_webhook = State()

def get_crypto_pay_keyboard():
    """Клавиатура управления Crypto Pay"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="➕ Добавить настройки", callback_data="crypto_pay_add")
    keyboard.button(text="❌ Удалить настройки", callback_data="crypto_pay_delete")
    keyboard.button(text="🔄 Обновить валюты", callback_data="crypto_pay_update_assets")
    keyboard.button(text="🔙 Назад", callback_data="admin_show_payment_settings")
    keyboard.adjust(2, 1)
    return keyboard.as_markup()

@router.callback_query(F.data == "admin_show_crypto_pay")
async def show_crypto_settings(callback: CallbackQuery):
    """Отображение текущих настроек Crypto Pay"""
    try:
        if not await db.is_admin(callback.from_user.id):
            await callback.answer("У вас нет прав для выполнения этого действия")
            return

        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute('SELECT * FROM crypto_settings LIMIT 1') as cursor:
                settings = await cursor.fetchone()

        if settings:
            supported_assets = json.loads(settings['supported_assets']) if settings['supported_assets'] else []
            assets_str = ", ".join(supported_assets) if supported_assets else "Не указаны"

            message_text = (
                "📊 <b>Текущие настройки Crypto Pay:</b>\n\n"
                f"🔑 API Token: <code>{settings['api_token'][:6]}...{settings['api_token'][-4:]}</code>\n"
                f"💰 Минимальная сумма: {settings['min_amount']} USDT\n"
                f"💱 Поддерживаемые валюты: {assets_str}\n"
                f"🌐 Webhook URL: {settings['webhook_url'] or 'Не настроен'}\n"
                f"📡 Статус: {'✅ Активен' if settings['is_enable'] else '❌ Отключен'}"
            )
        else:
            message_text = "⚠️ Настройки Crypto Pay не найдены"

        await callback.message.edit_text(
            text=message_text,
            reply_markup=get_crypto_pay_keyboard(),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Ошибка при отображении настроек Crypto Pay: {e}")
        await callback.answer("Произошла ошибка при получении настроек", show_alert=True)

@router.callback_query(F.data == "crypto_pay_add")
async def start_add_settings(callback: CallbackQuery, state: FSMContext):
    """Начало процесса добавления настроек"""
    try:
        await callback.message.edit_text(
            "Введите API Token от Crypto Pay Bot:",
            reply_markup=None
        )
        await state.set_state(CryptoPayState.waiting_for_token)
    except Exception as e:
        logger.error(f"Ошибка при старте добавления настроек: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@router.message(CryptoPayState.waiting_for_token)
async def process_token(message: Message, state: FSMContext):
    """Обработка введенного токена"""
    try:
        await state.update_data(api_token=message.text)
        await message.answer("Введите минимальную сумму в USDT:")
        await state.set_state(CryptoPayState.waiting_for_min_amount)
    except Exception as e:
        logger.error(f"Ошибка при обработке токена: {e}")
        await state.clear()
        await message.answer(
            "Произошла ошибка. Попробуйте снова.",
            reply_markup=get_crypto_pay_keyboard()
        )

@router.message(CryptoPayState.waiting_for_min_amount)
async def process_min_amount(message: Message, state: FSMContext):
    """Обработка минимальной суммы"""
    try:
        min_amount = float(message.text)
        await state.update_data(min_amount=min_amount)
        await message.answer(
            "Введите поддерживаемые валюты через запятую (например: USDT,BTC,TON):"
        )
        await state.set_state(CryptoPayState.waiting_for_assets)
    except ValueError:
        await message.answer("Пожалуйста, введите корректное число")
    except Exception as e:
        logger.error(f"Ошибка при обработке минимальной суммы: {e}")
        await state.clear()
        await message.answer(
            "Произошла ошибка. Попробуйте снова.",
            reply_markup=get_crypto_pay_keyboard()
        )

@router.message(CryptoPayState.waiting_for_assets)
async def process_assets(message: Message, state: FSMContext):
    """Обработка списка валют"""
    try:
        if not await db.is_admin(message.from_user.id):
            await message.answer("У вас нет прав для выполнения этого действия")
            await state.clear()
            return

        assets = [asset.strip().upper() for asset in message.text.split(',')]
        data = await state.get_data()
        
        test_api = CryptoPayAPI(data['api_token'])
        try:
            await test_api.get_me()
        except Exception as e:
            logger.error(f"Ошибка проверки API токена: {e}")
            await message.answer(
                "❌ Ошибка: Неверный API токен или проблема с подключением",
                reply_markup=get_crypto_pay_keyboard()
            )
            await state.clear()
            return

        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute("""
                INSERT OR REPLACE INTO crypto_settings 
                (api_token, min_amount, supported_assets, is_enable)
                VALUES (?, ?, ?, 1)
            """, (data['api_token'], data['min_amount'], json.dumps(assets)))
            await conn.commit()

        await crypto_pay_manager.init_api()

        await message.answer(
            "✅ Настройки Crypto Pay успешно сохранены!",
            reply_markup=get_crypto_pay_keyboard()
        )
        await state.clear()

    except Exception as e:
        logger.error(f"Ошибка при сохранении настроек: {e}")
        await message.answer(
            "Произошла ошибка при сохранении настроек",
            reply_markup=get_crypto_pay_keyboard()
        )
        await state.clear()

@router.callback_query(F.data == "crypto_pay_delete")
async def delete_settings(callback: CallbackQuery):
    """Удаление настроек Crypto Pay"""
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute('DELETE FROM crypto_settings')
            await conn.commit()

        await callback.message.edit_text(
            "✅ Настройки Crypto Pay удалены",
            reply_markup=get_crypto_pay_keyboard()
        )
    except Exception as e:
        logger.error(f"Ошибка при удалении настроек: {e}")
        await callback.answer("Произошла ошибка при удалении настроек", show_alert=True)

@router.callback_query(F.data == "crypto_pay_update_assets")
async def update_assets(callback: CallbackQuery):
    """Обновление списка поддерживаемых валют через API"""
    try:
        if not crypto_pay_manager.api:
            await callback.answer("API не инициализирован", show_alert=True)
            return

        currencies = await crypto_pay_manager.api.get_currencies()
        assets = [curr['code'] for curr in currencies]

        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute(
                'UPDATE crypto_settings SET supported_assets = ?',
                (json.dumps(assets),)
            )
            await conn.commit()

        await callback.answer("Список валют обновлен!", show_alert=True)
        await show_crypto_settings(callback)  

    except Exception as e:
        logger.error(f"Ошибка при обновлении валют: {e}")
        await callback.answer("Произошла ошибка при обновлении валют", show_alert=True) 
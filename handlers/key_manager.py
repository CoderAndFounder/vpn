from aiogram import Router, F
from aiogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from handlers.database import Database
from handlers.user.user_kb import get_back_to_start_keyboard
from datetime import datetime
from loguru import logger
import aiosqlite

router = Router()

def format_date(date_str: str) -> str:
    """Форматирование даты для отображения"""
    try:
        date_str = date_str.split('.')[0]
        date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        return date.strftime("%d.%m.%Y")
    except Exception as e:
        logger.error(f"Ошибка форматирования даты: {e}")
        return date_str

async def get_user_keys_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    """Создание клавиатуры с ключами пользователя"""
    db = Database()
    keyboard = []
    
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            
            async with conn.execute("""
                SELECT us.*, s.name as server_name
                FROM user_subscription us
                JOIN server_settings s ON us.server_id = s.id
                WHERE us.user_id = ? AND us.is_active = 1
            """, (telegram_id,)) as cursor:
                subscriptions = await cursor.fetchall()
                
                for sub in subscriptions:
                    formatted_date = format_date(sub['end_date'])
                    button_text = f"🔑 {sub['server_name']} | 📅 Дата окончания: {formatted_date}"
                    keyboard.append([
                        InlineKeyboardButton(
                            text=button_text,
                            callback_data=f"change_key_{sub['id']}"
                        )
                    ])

    except Exception as e:
        logger.error(f"Ошибка при создании клавиатуры ключей: {e}")

    keyboard.append([
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="lk_back_to_start"
        )
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)

@router.callback_query(F.data == "lk_my_keys")
async def show_user_keys(callback: CallbackQuery):
    """Показать список ключей пользователя"""
    try:
        await callback.message.delete()
        
        keyboard = await get_user_keys_keyboard(callback.from_user.id)
        
        has_subscriptions = len(keyboard.inline_keyboard) > 1
        
        if not has_subscriptions:
            await callback.message.answer(
                "🔑 <b>У вас нет активных ключей, которые можно перенести на другой сервер.</b>\n\n"
                "📌 Чтобы изменить локацию сервера, сначала приобретите тарифный план. После этого у вас появится ключ, и вы сможете выбрать новый сервер.",
                reply_markup=get_back_to_start_keyboard(),
                parse_mode="HTML"
            )
            return
        
        await callback.message.answer(
            "🔑 Добро пожаловать в меню управления ключами!\n "
            "Здесь вы можете <b>изменить сервер</b> для одного из ваших ключей.\n\n"
            "Выберите нужный ключ из списка ниже. 👇",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
        logger.info(f"Показано меню ключей пользователю {callback.from_user.id}")
        
    except Exception as e:
        logger.error(f"Ошибка при отображении меню ключей: {e}")
        await callback.message.answer(
            "❌ Произошла ошибка при получении списка ключей.\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=get_back_to_start_keyboard()
        )

@router.callback_query(F.data.startswith("change_key_"))
async def show_available_servers(callback: CallbackQuery):
    """Показать доступные серверы для смены"""
    try:
        await callback.message.delete()
        
        subscription_id = int(callback.data.split('_')[2])
        
        async with aiosqlite.connect(Database().db_path) as conn:
            conn.row_factory = aiosqlite.Row
            
            async with conn.execute("""
                SELECT us.*, ss.name as current_server_name, ss.protocol as current_protocol
                FROM user_subscription us
                JOIN server_settings ss ON us.server_id = ss.id
                WHERE us.id = ? AND us.is_active = 1
            """, (subscription_id,)) as cursor:
                subscription = await cursor.fetchone()
                
            if not subscription:
                await callback.message.answer(
                    "❌ Подписка не найдена или неактивна.",
                    reply_markup=get_back_to_start_keyboard()
                )
                return

            key_protocol = 'shadowsocks' if subscription['vless'].startswith('ss://') else 'vless'
                
            async with conn.execute("""
                SELECT id, name 
                FROM server_settings 
                WHERE id != ? 
                AND is_enable = 1 
                AND protocol = ?
                ORDER BY name
            """, (subscription['server_id'], key_protocol)) as cursor:
                available_servers = await cursor.fetchall()

            if not available_servers:
                await callback.message.answer(
                    f"❌ Нет доступных серверов с протоколом {key_protocol} для переноса ключа.\n"
                    "Пожалуйста, попробуйте позже.",
                    reply_markup=get_back_to_start_keyboard()
                )
                return

        formatted_date = format_date(subscription['end_date'])
        
        keyboard = []
        for server in available_servers:
            keyboard.append([
                InlineKeyboardButton(
                    text=f"🖥️ {server['name']}",
                    callback_data=f"select_server_{subscription_id}_{server['id']}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="lk_my_keys"
            )
        ])
        
        await callback.message.answer(
            f"Вы собираетесь сменить сервер для ключа:\n"
            f"<blockquote><code>{subscription['vless']}</code></blockquote>\n\n"
            f"Дата окончания: <b>{formatted_date}</b>\n"
            f"Текущий сервер: <b>{subscription['current_server_name']}</b>\n"
            f"Протокол: <b>{key_protocol.upper()}</b>\n"
            f"Для смены сервера выберите доступный из списка ниже 👇",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )
        
        logger.info(f"Показаны доступные серверы для подписки {subscription_id} с протоколом {key_protocol}")
        
    except Exception as e:
        logger.error(f"Ошибка при отображении доступных серверов: {e}")
        await callback.message.answer(
            "❌ Произошла ошибка при получении списка серверов.\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=get_back_to_start_keyboard()
        )

@router.callback_query(F.data.startswith("select_server_"))
async def confirm_server_change(callback: CallbackQuery):
    """Подтверждение смены сервера"""
    try:
        await callback.message.delete()
        
        _, _, subscription_id, new_server_id = callback.data.split('_')
        
        async with aiosqlite.connect(Database().db_path) as conn:
            conn.row_factory = aiosqlite.Row
            
            async with conn.execute("""
                SELECT name 
                FROM server_settings 
                WHERE id = ? AND is_enable = 1
            """, (new_server_id,)) as cursor:
                server = await cursor.fetchone()
                
            if not server:
                await callback.message.answer(
                    "❌ Выбранный сервер недоступен.",
                    reply_markup=get_back_to_start_keyboard()
                )
                return
        
        keyboard = [
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data=f"confirm_change_{subscription_id}_{new_server_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отмена",
                    callback_data="lk_my_keys"
                )
            ]
        ]
        
        await callback.message.answer(
            f"Ваш ключ будет перемещен на сервер: <b>{server['name']}</b>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            parse_mode="HTML"
        )
        
        logger.info(f"Запрошено подтверждение смены сервера для подписки {subscription_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при подтверждении смены сервера: {e}")
        await callback.message.answer(
            "❌ Произошла ошибка при выборе сервера.\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=get_back_to_start_keyboard()
        ) 
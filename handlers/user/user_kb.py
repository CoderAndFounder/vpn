from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
import aiosqlite
from loguru import logger
from handlers.database import db
import logging

logger = logging.getLogger(__name__)

async def get_start_keyboard() -> InlineKeyboardMarkup:
    """Создание стартовой клавиатуры"""
    builder = InlineKeyboardBuilder()
    
    base_buttons = [
        InlineKeyboardButton(text="👤 Личный кабинет", callback_data="start_lk"),
        InlineKeyboardButton(text="🎁 Пробный период", callback_data="start_trial"),
        InlineKeyboardButton(text="💳 Тарифы", callback_data="start_tariffs"),
        InlineKeyboardButton(text="📞 Техподдержка", callback_data="help_support"),
    ]
    
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT name 
                FROM raffles 
                WHERE status = 'active' 
                AND (end_date IS NULL OR end_date > datetime('now'))
                LIMIT 1
            """)
            active_raffle = await cursor.fetchone()
            
            if active_raffle:
                base_buttons.append(
                    InlineKeyboardButton(
                        text=f"🎉 {active_raffle['name']} 🎉", 
                        callback_data="start_raffle"
                    )
                )
    except Exception as e:
        logger.error(f"Ошибка при проверке активного розыгрыша: {e}")
    
    for i in range(0, len(base_buttons), 2):
        row_buttons = base_buttons[i:i+2]
        builder.row(*row_buttons)
    
    builder.row(InlineKeyboardButton(text="🔗 Реферальная программа", callback_data="referral_program"))
    builder.row(InlineKeyboardButton(text="📢 Наши новости", url="https://t.me/dzhamaal05"))
    
    return builder.as_markup()

def get_lk_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры личного кабинета"""
    builder = InlineKeyboardBuilder()

    buttons = [
        InlineKeyboardButton(text="📋 Мои подписки", callback_data="lk_my_subscriptions"),
        InlineKeyboardButton(text="💰 Мои платежи", callback_data="lk_my_payments"),
        InlineKeyboardButton(text="💲 Мой баланс", callback_data="lk_my_balance"),
        InlineKeyboardButton(text="📢 Инструкции", callback_data="lk_instructions"),
        InlineKeyboardButton(text="💬 Помощь", callback_data="start_help"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="lk_back_to_start"),
    ]
    
    for i in range(0, len(buttons), 2):
        builder.row(*buttons[i:i + 2])


    return builder.as_markup()

def get_trial_keyboard(show_connect: bool = True) -> InlineKeyboardMarkup:
    """Создание клавиатуры для пробного периода"""
    builder = InlineKeyboardBuilder()
    
    if show_connect:
        buttons = [
            InlineKeyboardButton(text="🔗 Подключить", callback_data="trial_connect"),
            InlineKeyboardButton(text="🔙 Назад", callback_data="lk_back_to_start"),
        ]
    else:
        buttons = [
            InlineKeyboardButton(text="💳 Тарифы", callback_data="start_tariffs"),
            InlineKeyboardButton(text="🔙 Назад", callback_data="lk_back_to_start"),
        ]
    
    builder.row(*buttons)
    
    return builder.as_markup()

def get_trial_vless_keyboard(show_connect: bool = True) -> InlineKeyboardMarkup:
    """Создание клавиатуры для сообщения с ключом vless"""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        InlineKeyboardButton(text="💳 Тарифы", callback_data="start_tariffs"),
        InlineKeyboardButton(text="🚀 VPN Клиент", callback_data="show_vpn_client"),
        InlineKeyboardButton(text="⚙️ Настройки", callback_data="show_settings"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="lk_back_to_start"),
    ]
    builder.row(*buttons[:2])
    builder.row(*buttons[2:4])
    return builder.as_markup()

def get_subscriptions_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для отображения подписок"""
    builder = InlineKeyboardBuilder()

    buttons = [
        InlineKeyboardButton(text="👤 Вернуться в кабинет", callback_data="start_lk"),
        InlineKeyboardButton(text="🤝 Объединить подписки", callback_data="merge_subscriptions"),
        InlineKeyboardButton(text="💳 Тарифы", callback_data="start_tariffs"),
        InlineKeyboardButton(text="💬 Помощь", callback_data="start_help"),
    ]

    for i in range(0, len(buttons), 2):
        builder.row(*buttons[i:i + 2])

    builder.row(InlineKeyboardButton(text="🔑 Управление ключами", callback_data="lk_my_keys"))

    return builder.as_markup()

def get_continue_merge_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для продолжения объединения подписок"""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        InlineKeyboardButton(text="👤 Вернуться в кабинет", callback_data="start_lk"),
        InlineKeyboardButton(text="✅ Продолжить", callback_data="continue_merge"),
    ]
    
    builder.row(*buttons[:2])
    return builder.as_markup()

def get_back_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для кнопки назад"""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        InlineKeyboardButton(text="👤 Вернуться в кабинет", callback_data="start_lk"),
    ]
    
    builder.row(*buttons[:2])
    return builder.as_markup()

def get_success_by_keyboard(show_connect: bool = True) -> InlineKeyboardMarkup:
    """Создание клавиатуры для сообщения с ключом vless"""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        InlineKeyboardButton(text="👤 Личный кабинет", callback_data="start_lk"),
        InlineKeyboardButton(text="📋 Мои подписки", callback_data="lk_my_subscriptions"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="lk_back_to_start"),
    ]
    builder.row(*buttons[:2])
    builder.row(*buttons[2:4])
    return builder.as_markup()

def get_help_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для раздела помощи"""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        InlineKeyboardButton(text="🤝 Объединить подписки", callback_data="merge_subscriptions"),
        InlineKeyboardButton(text="📞 Техподдержка", callback_data="help_support"),
        InlineKeyboardButton(text="👤 Вернуться в кабинет", callback_data="start_lk"),
    ]
    
    builder.row(*buttons[:2])
    builder.row(*buttons[2:4])
    return builder.as_markup()

def get_no_subscriptions_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для сообщения о том что нет активных подписок"""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        InlineKeyboardButton(text="👤 В личный кабинет", callback_data="start_lk"),
        InlineKeyboardButton(text="💳 Тарифы", callback_data="start_tariffs"),
        InlineKeyboardButton(text="📞 Техподдержка", callback_data="help_support"),
    ]
    
    builder.row(*buttons[:2])
    builder.row(*buttons[2:4])
    return builder.as_markup()

def get_user_instructions_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для раздела инструкций"""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        InlineKeyboardButton(text="📱 Android", callback_data="instructions_android"),
        InlineKeyboardButton(text="📱 IOS", callback_data="instructions_ios"),
        InlineKeyboardButton(text="💻 Windows", callback_data="instructions_windows"),
        InlineKeyboardButton(text="💻 MacOS", callback_data="instructions_macos"),
    ]
    
    builder.row(*buttons[:2])
    builder.row(*buttons[2:4])
    return builder.as_markup()

def get_unknown_command_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для неизвестной команды"""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        InlineKeyboardButton(text="📞 Техподдержка", callback_data="help_support"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="lk_back_to_start"),
    ]
    
    builder.row(*buttons[:2])
    return builder.as_markup()

def get_back_raffle_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для кнопки назад"""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        InlineKeyboardButton(text="💳 Тарифы", callback_data="start_tariffs"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="lk_back_to_start"),
    ]
    
    builder.row(*buttons[:2])
    return builder.as_markup()


async def get_allocation_tickets_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры под условием розыгрыша"""
    builder = InlineKeyboardBuilder()
    base_buttons = [

        InlineKeyboardButton(text="💳 Тарифы", callback_data="start_tariffs"),
    ]
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT name 
                FROM raffles 
                WHERE status = 'active' 
                AND (end_date IS NULL OR end_date > datetime('now'))
                LIMIT 1
            """)
            active_raffle = await cursor.fetchone()
            
            if active_raffle:
                base_buttons.append(
                    InlineKeyboardButton(
                        text=f"🎉 {active_raffle['name']} 🎉", 
                        callback_data="start_raffle"
                    )
                )
    except Exception as e:
        logger.error(f"Ошибка при проверке активного розыгрыша: {e}")

    for i in range(0, len(base_buttons), 2):
        row_buttons = base_buttons[i:i+2]
        builder.row(*row_buttons)
    
    
    return builder.as_markup()

def get_user_balance_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для баланса"""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        InlineKeyboardButton(text="➕ Пополнить баланс", callback_data="start_add_balance"),
        InlineKeyboardButton(text="💳 Тарифы", callback_data="start_tariffs"),
        InlineKeyboardButton(text="💸 Поделиться балансом", callback_data="start_transfer_balance"),
        InlineKeyboardButton(text="🔙 Назад", callback_data="start_lk"),
    ]
    
    builder.row(buttons[0], buttons[1])
    builder.row(buttons[2])
    builder.row(buttons[3])
    return builder.as_markup()

def get_user_edit_balance_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для баланса"""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        InlineKeyboardButton(text="💲 Посмотреть баланс", callback_data="lk_my_balance"),
        InlineKeyboardButton(text="➕ Пополнить баланс", callback_data="start_add_balance"),
        InlineKeyboardButton(text="💳 Тарифы", callback_data="start_tariffs"),
    ]
    
    builder.row(buttons[0], buttons[1])
    builder.row(buttons[2])
    return builder.as_markup()

def get_user_success_transfer_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для баланса"""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        InlineKeyboardButton(text="💲 Посмотреть баланс", callback_data="lk_my_balance"),
        InlineKeyboardButton(text="💳 Купить тариф", callback_data="start_tariffs"),
        InlineKeyboardButton(text="👤 В личный кабинет", callback_data="start_lk"),
    ]
    
    builder.row(buttons[0])
    builder.row(buttons[1])
    builder.row(buttons[2])
    return builder.as_markup()

def get_user_cancel_transfer_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для отмены перевода баланса"""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        InlineKeyboardButton(text="❌ Отмена", callback_data="lk_my_balance"),
    ]
    builder.row(buttons[0])
    return builder.as_markup()

def get_back_to_start_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для неизвестной команды"""
    builder = InlineKeyboardBuilder()
    
    buttons = [
        InlineKeyboardButton(text="🔙 Назад", callback_data="lk_back_to_start"),
    ]
    
    builder.row(*buttons[:1])
    return builder.as_markup()
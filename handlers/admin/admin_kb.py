from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры администратора"""
    keyboard = InlineKeyboardBuilder()
    
    keyboard.button(text="🖥️ Сервера", callback_data="admin_show_servers")
    keyboard.button(text="📈 Статистика", callback_data="admin_show_payments")
    keyboard.button(text="🎁 Промокоды", callback_data="admin_show_promocodes")
    keyboard.button(text="👥 Пользователи", callback_data="admin_show_users")
    keyboard.button(text="💳 Тарифы", callback_data="admin_show_tariff")
    keyboard.button(text="⏳ Пробный тариф", callback_data="admin_show_trial")
  #  keyboard.button(text="💳 Настройки тарифов", callback_data="admin_show_tariff_settings")
    keyboard.button(text="💲 Платежные настройки", callback_data="admin_show_payment_settings") 
    keyboard.button(text="🔔 Оповещения", callback_data="admin_show_notifications")
    keyboard.button(text="🔥 Промо тарифы", callback_data="admin_show_promo_tariff")
    keyboard.button(text="🎉 Розыгрыши", callback_data="admin_show_raffles")
    keyboard.button(text="🆘 Служба поддержки", callback_data="admin_show_support")
    keyboard.button(text="🔗 Реферальная программа", callback_data="admin_show_referral") 
    keyboard.button(text="🔙 Вернуться", callback_data="admin_back_to_start")
    
    keyboard.adjust(2, 2)  
    return keyboard.as_markup()

def get_servers_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для списка серверов"""
    keyboard = InlineKeyboardBuilder()
    
    keyboard.button(text="Обновить", callback_data="servers_update")
    keyboard.button(text="Добавить сервер", callback_data="add_server")
    keyboard.button(text="Удалить сервер", callback_data="delete_server")
    keyboard.button(text="Назад", callback_data="servers_back_to_admin")
    
    keyboard.adjust(2, 2)  
    return keyboard.as_markup()

def get_promocodes_keyboard() -> InlineKeyboardBuilder:
    """Создание клавиатуры для управления промокодами"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="➕ Добавить промокод", callback_data="add_promocode")
    keyboard.button(text="❌ Удалить промокод", callback_data="delete_promocode")
    keyboard.button(text="🔙 Назад", callback_data="promocodes_back_to_admin")
    keyboard.adjust(2, 1)  
    return keyboard.as_markup()

def get_promocodes_keyboard_delete() -> InlineKeyboardBuilder:
    """Создание клавиатуры для управления промокодами после удаления"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="➕ Добавить промокод", callback_data="add_promocode")
    keyboard.button(text="🎁 Показать промокоды", callback_data="admin_show_promocodes")
    keyboard.button(text="🔙 Назад", callback_data="promocodes_back_to_admin")
    keyboard.adjust(2, 1)  
    return keyboard.as_markup()

def get_admin_users_keyboard() -> InlineKeyboardBuilder:
    """Создание клавиатуры для управления пользователями"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="❌ Заблокировать", callback_data="ban_user")
    keyboard.button(text="✅ Разблокировать", callback_data="unban_user")
    keyboard.button(text="🔄 Сбросить триал", callback_data="reset_trial")
    keyboard.button(text="🚀 В админку", callback_data="promocodes_back_to_admin")
    keyboard.adjust(2, 1)  
    return keyboard.as_markup()

def get_admin_users_keyboard_cancel() -> InlineKeyboardBuilder:
    """Создание клавиатуры для управления пользователями"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔙 Назад", callback_data="promocodes_back_to_admin")
    keyboard.adjust(2, 1)  
    return keyboard.as_markup()

def get_admin_reset_trial_keyboard() -> InlineKeyboardBuilder:
    """Создание клавиатуры для управления пользователями"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔙 Назад", callback_data="admin_show_users")
    keyboard.adjust(1)  
    return keyboard.as_markup()

def get_admin_show_tariff_keyboard() -> InlineKeyboardBuilder:
    """Создание клавиатуры для управления пользователями"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="➕ Добавить тариф", callback_data="admin_add_tariff")
    keyboard.button(text="❌ Удалить тариф", callback_data="admin_delete_tariff")
    keyboard.button(text="🔙 Назад", callback_data="admin_back_to_start")
    keyboard.adjust(2, 1)  
    return keyboard.as_markup()

def get_yokassa_keyboard() -> InlineKeyboardMarkup:
    """Создание клавиатуры для списка серверов"""
    keyboard = InlineKeyboardBuilder()
    
    keyboard.button(text="Добавить YoKassa", callback_data="add_yokassa")
    keyboard.button(text="Удалить YoKassa", callback_data="delete_yokassa")
    keyboard.button(text="Назад", callback_data="admin_show_payment_settings")
    
    keyboard.adjust(2, 1)  
    return keyboard.as_markup()

def get_admin_show_trial_keyboard() -> InlineKeyboardBuilder:
    """Создание клавиатуры для управления пробным тарифом"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="➕ Добавить проб. тариф", callback_data="admin_add_trial")
    keyboard.button(text="❌ Удалить проб. тариф", callback_data="admin_delete_trial")
    keyboard.button(text="🔙 Назад", callback_data="servers_back_to_admin")
    keyboard.adjust(2, 1)  
    return keyboard.as_markup()

def get_admin_notifications_keyboard() -> InlineKeyboardBuilder:
    """Создание клавиатуры для управления оповещениями"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🖊️ Изменить", callback_data="admin_add_notification")
    keyboard.button(text="❌ Выключить", callback_data="admin_off_notification")
    keyboard.button(text="🔔 Пользовательские", callback_data="admin_user_sub_notification")
    keyboard.button(text="📬 Рассылка", callback_data="admin_send_notification")
    keyboard.button(text="🔙 Назад", callback_data="servers_back_to_admin")
    keyboard.adjust(2, 2, 1)  
    return keyboard.as_markup()

def get_admin_show_promo_tariff_keyboard() -> InlineKeyboardBuilder:
    """Создание клавиатуры для управления пробным тарифом"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="➕ Добавить промо тариф", callback_data="admin_add_promo_tariff")
    keyboard.button(text="❌ Удалить промо тариф", callback_data="admin_delete_promo_tariff")
    keyboard.button(text="🚀 Отправить пользователю", callback_data="admin_send_promo_tariff")
    keyboard.button(text="🔙 Назад", callback_data="servers_back_to_admin")
    keyboard.adjust(2, 1)  
    return keyboard.as_markup()

def get_admin_user_sub_notify_keyboard() -> InlineKeyboardBuilder:
    """Создание клавиатуры для управления оповещениями"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🖊️ Изменить", callback_data="admin_edit_user_notify")
    keyboard.button(text="❌ Выключить", callback_data="admin_off_user_notify")
    keyboard.button(text="🚀 В админку", callback_data="servers_back_to_admin")
    keyboard.adjust(2, 1)  
    return keyboard.as_markup()

def get_admin_show_payments_code_keyboard() -> InlineKeyboardBuilder:
    """Создание клавиатуры для управления кодами оплаты"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="➕ Добавить код оплаты", callback_data="admin_add_payments_code")
    keyboard.button(text="❌ Удалить код оплаты", callback_data="admin_delete_payments_code")
    keyboard.button(text="💾 Получить все коды в виде файла", callback_data="admin_get_all_payments_code")
    keyboard.button(text="🔙 Назад", callback_data="admin_show_payment_settings")
    keyboard.adjust(2, 1)  
    return keyboard.as_markup()

def get_admin_answer_keyboard() -> InlineKeyboardBuilder:
    """Создание клавиатуры для ответа на сообщение"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✍️ Ответить", callback_data="admin_answer_message")
    keyboard.button(text="🔙 Назад", callback_data="servers_back_to_admin")
    keyboard.adjust(2)  
    return keyboard.as_markup()

def get_admin_payment_settings_keyboard() -> InlineKeyboardBuilder:
    """Создание клавиатуры для платежных настроек"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="💲 Настройки ЮKassa", callback_data="admin_show_yokassa")
    keyboard.button(text="₿ Настройки Crypto Pay", callback_data="admin_show_crypto_pay")
    keyboard.button(text="💰 Коды оплаты", callback_data="admin_show_payments_code")
    keyboard.button(text="💲 Баланс пользователей", callback_data="admin_show_users_balance")
    keyboard.button(text="🔙 Назад", callback_data="servers_back_to_admin")
    keyboard.adjust(2)  
    return keyboard.as_markup()

def get_admin_show_raffles_keyboard() -> InlineKeyboardBuilder:
    """Создание клавиатуры для управления розыгрышами"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="➕ Добавить розыгрыш", callback_data="admin_add_raffle")
    keyboard.button(text="❌ Удалить розыгрыш", callback_data="admin_delete_raffle")
    keyboard.button(text="💾 Сохранить билеты в файл", callback_data="admin_save_tickets_to_file")
    keyboard.button(text="🚮 Удалить билеты", callback_data="admin_delete_tickets")
    keyboard.button(text="🔙 Назад", callback_data="servers_back_to_admin")
    keyboard.adjust(2, 1)  
    return keyboard.as_markup()

def get_admin_confirm_delete_raffle_keyboard() -> InlineKeyboardBuilder:
    """Создание клавиатуры для подтверждения удаления розыгрыша"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Подтвердить", callback_data="admin_confirm_delete_raffle")
    keyboard.button(text="❌ Отмена", callback_data="admin_show_raffles")
    keyboard.adjust(2)  
    return keyboard.as_markup()

def get_admin_show_users_balance_keyboard() -> InlineKeyboardBuilder:
    """Создание клавиатуры для баланса"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🕵️ Найти пользователя", callback_data="admin_find_user")
    keyboard.button(text="💾 Получить все транзакции", callback_data="admin_get_all_transactions")
    keyboard.button(text="🔙 Назад", callback_data="admin_show_payment_settings")
    keyboard.adjust(2, 1)  
    return keyboard.as_markup()

def get_admin_add_users_balance_keyboard() -> InlineKeyboardBuilder:
    """Создание клавиатуры для баланса"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="➕ Добавить баланс", callback_data="admin_add_users_balance")
    keyboard.button(text="🔄 Обнулить баланс", callback_data="admin_reset_users_balance")
    keyboard.button(text="🔙 Назад", callback_data="admin_show_payment_settings")
    keyboard.adjust(2, 1)  
    return keyboard.as_markup()

def get_admin_balance_back_edit_keyboard() -> InlineKeyboardBuilder:
    """Создание клавиатуры для возврата в меню баланса"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="🔙 Назад", callback_data="admin_show_payment_settings")
    keyboard.adjust(1)  
    return keyboard.as_markup()

def get_admin_referral_keyboard() -> InlineKeyboardBuilder:
    """Создание клавиатуры для управления реферальной программой"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="➕ Добавить условие", callback_data="admin_add_referral_condition")
    keyboard.button(text="🔄 Изменить условие", callback_data="admin_edit_referral_condition")
    keyboard.button(text="❌ Удалить условие", callback_data="admin_delete_referral_condition")
    keyboard.button(text="🔙 Назад", callback_data="servers_back_to_admin")
    keyboard.adjust(1)  
    return keyboard.as_markup()
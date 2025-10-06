import os
import asyncio
import aiosqlite
from aiogram import Bot, Dispatcher
from loguru import logger
from handlers.database import db
from handlers.admin.admin import router as admin_router
from handlers.commands import router as commands_router
from handlers.user.user_lk import router as user_router
from handlers.trial import router as trial_router
from handlers.tariff import router as tariff_router
from handlers.user.user_lk_sub import router as user_lk_sub_router
from handlers.user.merge_sub import router as merge_sub_router
from handlers.admin.admin_promocodes import router as admin_promocodes_router
from handlers.admin.admin_users import router as admin_users_router
from handlers.admin.admin_user_del import router as admin_user_del_router
from handlers.admin.admin_unban import router as admin_unban_router
from handlers.admin.admin_reset_trial import router as admin_reset_trial_router
from handlers.user.user_show_statistic import router as user_statistic_router
from handlers.user.user_help import router as user_help_router
from handlers.user.user_support import router as user_support_router
from handlers.admin.admin_server_add import router as admin_server_add_router
from handlers.admin.admin_server_del import router as admin_server_del_router
from handlers.admin.admin_tariff import router as admin_tariff_router
from handlers.admin.admin_tariff_add import router as admin_tariff_add_router
from handlers.admin.admin_yookassa import router as admin_yookassa_router
from handlers.admin.admin_trial import router as admin_trial_router
from handlers.admin.admin_trial_add import router as admin_trial_add_router
from handlers.admin.admin_trial_del import router as admin_trial_del_router
from handlers.admin.admin_notification import router as admin_notification_router
from handlers.admin.admin_notify_edit import router as admin_notify_edit_router
from handlers.admin.admin_send_notify import router as admin_send_notify_router
from handlers.admin.admin_promo_tariff import router as admin_promo_tariff_router
from handlers.admin.admin_promo_tariff_add import router as admin_promo_tariff_add_router
from handlers.admin.admin_promo_send import router as admin_promo_send_router
from handlers.admin.admin_support import router as admin_support_router
from handlers.admin.admin_user_notify import router as admin_user_notify_router
from handlers.admin.admin_pay_code import router as admin_pay_code_router
from handlers.admin.admin_get_pay_code import router as admin_get_pay_code_router
from handlers.admin.admin_cryptopay import router as admin_cryptopay_router
from handlers.user.user_lk_inst import router as user_lk_inst_router
from handlers.user.user_pay_code import router as user_pay_code_router
from handlers.user.user_cryptopay import router as user_cryptopay_router
from handlers.admin.admin_answer import router as admin_answer_router
from handlers.sub_scheduler import start_scheduler
from handlers.crypto_pay import crypto_pay_manager
from handlers.admin.admin_pay_menu import router as admin_pay_menu_router
from handlers.user.user_raffle import router as user_raffle_router
from handlers.admin.admin_raffles import router as raffles_router
from handlers.user.unknown_messages import router as unknown_messages_router
from handlers.user.user_balance import router as user_balance_router
from handlers.user.user_pay_balance import router as user_pay_balance_router
from handlers.admin.admin_user_balance import router as admin_user_balance_router
from handlers.admin.admin_balance_edit import router as admin_balance_edit_router
from handlers.user.user_transfer_balance import router as user_transfer_balance_router
from handlers.user.user_referral_menu import router as user_referral_router
from handlers.admin.admin_referral import router as admin_referral_router
from handlers.key_manager import router as key_manager_router
from handlers.key_change_server import router as key_change_router



os.makedirs('instance', exist_ok=True)

async def bot_start():
    """Запуск бота"""
    await db.init_db()
    
    settings = await db.get_bot_settings()
    if not settings:
        logger.error("Настройки бота не найдены в базе данных")
        return
    
    if not settings['is_enable']:
        logger.warning("Бот отключен в настройках")
        return

    try:
        await crypto_pay_manager.init_api()
        logger.info("Crypto Pay API инициализирован")
    except Exception as e:
        logger.error(f"Ошибка при инициализации Crypto Pay API: {e}")

    bot = Bot(token=settings['bot_token'])
    dp = Dispatcher()
    
    dp.include_router(user_balance_router)  
    dp.include_router(commands_router)  
    dp.include_router(user_router)      
    dp.include_router(user_lk_sub_router) 
    dp.include_router(trial_router)     
    dp.include_router(admin_router)     
    dp.include_router(admin_pay_code_router)  
    dp.include_router(tariff_router)    
    dp.include_router(merge_sub_router)  
    dp.include_router(admin_promocodes_router)  
    dp.include_router(admin_users_router)  
    dp.include_router(admin_user_del_router)  
    dp.include_router(admin_unban_router)  
    dp.include_router(admin_reset_trial_router)  
    dp.include_router(user_statistic_router)  
    dp.include_router(user_help_router)  
    dp.include_router(user_support_router)  
    dp.include_router(admin_server_add_router)  
    dp.include_router(admin_server_del_router)  
    dp.include_router(admin_tariff_router)
    dp.include_router(admin_tariff_add_router)
    dp.include_router(admin_yookassa_router)
    dp.include_router(admin_trial_router)
    dp.include_router(admin_trial_add_router)
    dp.include_router(admin_trial_del_router)
    dp.include_router(admin_notification_router)
    dp.include_router(admin_notify_edit_router)
    dp.include_router(admin_send_notify_router)
    dp.include_router(admin_promo_tariff_router)
    dp.include_router(admin_promo_tariff_add_router)
    dp.include_router(admin_promo_send_router)
    dp.include_router(admin_support_router)
    dp.include_router(admin_user_notify_router)
    dp.include_router(admin_get_pay_code_router)
    dp.include_router(admin_cryptopay_router)
    dp.include_router(user_pay_code_router)
    dp.include_router(user_cryptopay_router)
    dp.include_router(user_lk_inst_router)
    dp.include_router(admin_answer_router)
    dp.include_router(admin_pay_menu_router)
    dp.include_router(user_raffle_router)
    dp.include_router(raffles_router) 
    dp.include_router(user_pay_balance_router)
    dp.include_router(admin_user_balance_router)
    dp.include_router(admin_balance_edit_router)
    dp.include_router(user_transfer_balance_router)
    dp.include_router(user_referral_router)
    dp.include_router(admin_referral_router)
    dp.include_router(key_manager_router)
    dp.include_router(key_change_router)
    dp.include_router(unknown_messages_router)  
    
    
    asyncio.create_task(start_scheduler(bot))
    
    try:
        logger.info("Бот запущен")
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"Ошибка при работе бота: {e}")
    finally:
        await bot.session.close()
        logger.info("Бот остановлен")

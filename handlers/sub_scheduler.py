import asyncio
import aiosqlite
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Optional

from aiogram import Bot
from loguru import logger
from handlers.database import db
from handlers.user.user_kb import get_no_subscriptions_keyboard

async def format_remaining_time(end_date: str) -> str:
    """Форматирование оставшегося времени в днях и часах"""
    try:
        end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
        now = datetime.now(timezone.utc)
        
        if end_datetime.tzinfo is None:
            end_datetime = end_datetime.replace(tzinfo=timezone.utc)
        
        remaining = end_datetime - now
        
        days = remaining.days
        hours = remaining.seconds // 3600
        
        if days > 0:
            return f"{days}д. {hours}ч."
        return f"{hours}ч."
    except Exception as e:
        logger.error(f"Ошибка при форматировании времени: {e}")
        return "время неизвестно"

async def check_subscriptions(bot: Bot):
    """Проверка подписок и отправка уведомлений"""
    try:
        active_settings = await db.get_active_notify_settings()
        
        for setting in active_settings:
            if setting['type'] != 'subscription_check':
                continue
                
            logger.info(f"Запуск проверки подписок для планировщика '{setting['name']}'")
            
            expiring_subs = await db.get_expiring_subscriptions()
            
            if not expiring_subs:
                logger.info("Нет подписок, требующих уведомления")
                continue
            
            for sub in expiring_subs:
                try:
                    tariff = await db.get_tariff(sub['tariff_id'])
                    if not tariff:
                        logger.error(f"Тариф не найден для ID: {sub['tariff_id']}")
                        continue
                    
                    server = await db.get_server(sub['server_id'])
                    if not server:
                        logger.error(f"Сервер не найден для ID: {sub['server_id']}")
                        continue
                    
                    remaining_time = await format_remaining_time(sub['end_date'])
                    
                    message = (
                        "Ваша подписка скоро закончится\n"
                        "<blockquote>\n"
                        #f"Наименование: {setting['name']}\n"
                        f"Тариф: {tariff['name']}\n"
                        f"Страна: {server['name']}\n"
                        f"Осталось: {remaining_time}\n"
                        "</blockquote>"
                        "Вы можете приобрести новую подписку в разделе <b>Тарифы</b>"
                    )
                    
                    await bot.send_message(
                        chat_id=sub['user_id'],
                        text=message,
                        parse_mode="HTML",
                        reply_markup=get_no_subscriptions_keyboard()
                    )
                    
                    logger.info(f"Отправлено уведомление пользователю {sub['user_id']} о подписке {sub['id']}")
                    
                except Exception as e:
                    logger.error(f"Ошибка при отправке уведомления для подписки {sub['id']}: {e}")
            
            await asyncio.sleep(setting['interval'] * 60)
            
    except Exception as e:
        logger.error(f"Ошибка в планировщике подписок: {e}")

async def start_scheduler(bot: Bot):
    """Запуск планировщика"""
    logger.info("Запуск планировщика подписок")
    while True:
        try:
            await check_subscriptions(bot)
        except Exception as e:
            logger.error(f"Ошибка в цикле планировщика: {e}")
        await asyncio.sleep(60)  

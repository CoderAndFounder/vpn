from aiogram import Router, F
from aiogram.types import CallbackQuery
from handlers.database import Database
from handlers.user.user_kb import get_back_to_start_keyboard
from handlers.x_ui import xui_manager
from handlers.x_ui_ss import xui_ss_manager
from loguru import logger
import aiosqlite
from datetime import datetime
import re
import py3xui

router = Router()

@router.callback_query(F.data.startswith("confirm_change_"))
async def process_server_change(callback: CallbackQuery):
    """Обработка подтверждения смены сервера"""
    try:
        await callback.message.delete()
        
        _, _, subscription_id, new_server_id = callback.data.split('_')
        subscription_id = int(subscription_id)
        new_server_id = int(new_server_id)
        
        db = Database()
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            
            async with conn.execute("""
                SELECT 
                    us.*, 
                    ss.*, 
                    t.id as tariff_id, 
                    t.name as tariff_name,
                    us.user_id as telegram_id,
                    u.id as real_user_id
                FROM user_subscription us
                JOIN server_settings ss ON us.server_id = ss.id
                JOIN tariff t ON us.tariff_id = t.id
                JOIN user u ON u.telegram_id = us.user_id
                WHERE us.id = ? AND us.is_active = 1
            """, (subscription_id,)) as cursor:
                row = await cursor.fetchone()
                old_subscription = dict(row) if row else None  # Преобразуем в обычный словарь
                
            if not old_subscription:
                logger.error(f"Подписка {subscription_id} не найдена")
                raise Exception("Подписка не найдена или неактивна")
                
            logger.debug(f"Найдена подписка: {old_subscription}")
            
            async with conn.execute("""
                SELECT * FROM server_settings 
                WHERE id = ? AND is_enable = 1
            """, (new_server_id,)) as cursor:
                new_server = await cursor.fetchone()
                
            if not new_server:
                logger.error(f"Сервер {new_server_id} не найден или неактивен")
                raise Exception("Новый сервер недоступен")

            logger.debug(f"Найден новый сервер: {dict(new_server)}")

            is_shadowsocks = old_subscription['vless'].startswith('ss://')
            
            server_settings = dict(new_server)

            end_date = old_subscription['end_date'].split('.')[0]
            end_datetime = datetime.strptime(end_date, '%Y-%m-%d %H:%M:%S')
            now = datetime.now()
            time_diff = end_datetime - now

            days_left = max(1, int((time_diff.total_seconds() + 86399) // 86400))

            trial_settings = {
                'left_day': days_left
            }

            logger.debug(f"Дата окончания: {end_datetime}")
            logger.debug(f"Текущая дата: {now}")
            logger.debug(f"Разница в днях: {days_left}")

            required_fields = ['telegram_id', 'tariff_id', 'server_id', 'end_date', 'vless']
            for field in required_fields:
                if field not in old_subscription:
                    logger.error(f"Отсутствует обязательное поле {field} в данных подписки")
                    raise Exception(f"Отсутствует обязательное поле {field}")

            if is_shadowsocks:
                new_key = await xui_ss_manager.create_ss_user(
                    server_settings=server_settings,
                    trial_settings=trial_settings,
                    telegram_id=old_subscription['telegram_id']
                )
            else:
                new_key = await xui_manager.create_trial_user(
                    server_settings=server_settings,
                    trial_settings=trial_settings,
                    telegram_id=old_subscription['telegram_id']
                )

            if not new_key:
                raise Exception("Ошибка при создании нового ключа")

            try:
                if is_shadowsocks:
                    await xui_ss_manager.delete_ss_user(
                        server_settings=dict(old_subscription),
                        email=f"tg_{old_subscription['telegram_id']}@"
                    )
                else:
                    uuid_match = re.search(r'vless://([^@]+)@', old_subscription['vless'])
                    if not uuid_match:
                        logger.error(f"Не удалось извлечь UUID из строки vless: {old_subscription['vless']}")
                        raise Exception("Не удалось извлечь UUID")
                        
                    client_uuid = uuid_match.group(1)
                    logger.info(f"Извлечен UUID для удаления: {client_uuid}")

                    api_url = f"{old_subscription['url']}:{old_subscription['port']}/{old_subscription['secret_path']}"
                    
                    api = py3xui.AsyncApi(
                        host=api_url,
                        username=old_subscription['username'],
                        password=old_subscription['password'],
                        use_tls_verify=False
                    )
                    
                    await api.login()
                    await api.client.delete(old_subscription['inbound_id'], client_uuid)
                    logger.info(f"Клиент успешно удален с сервера {api_url}")

            except Exception as e:
                logger.warning(f"Не удалось удалить старый ключ: {e}")

            await conn.execute("""
                UPDATE user_subscription 
                SET is_active = 0 
                WHERE id = ?
            """, (subscription_id,))

            await conn.execute("""
                INSERT INTO user_subscription 
                (user_id, tariff_id, server_id, end_date, vless, is_active, payment_id)
                VALUES (?, ?, ?, ?, ?, 1, ?)
            """, (
                old_subscription['telegram_id'],
                old_subscription['tariff_id'],
                new_server_id,
                end_date,
                new_key,
                old_subscription['payment_id']
            ))
            
            await conn.commit()

            await callback.message.answer(
                "✅ Ключ успешно перемещен на новый сервер!\n\n"
                f"<b>Тариф:</b> {old_subscription['tariff_name']}\n"
                f"<b>Сервер:</b> {new_server['name']}\n"
                f"<b>Дата окончания:</b> {old_subscription['end_date'].split('.')[0]}\n\n"
                f"<b>Ваш новый ключ:</b>\n"
                f"<code>{new_key}</code>",
                parse_mode="HTML",
                reply_markup=get_back_to_start_keyboard()
            )
            
            logger.info(f"Успешно перемещен ключ для пользователя {old_subscription['telegram_id']} "
                       f"с сервера {old_subscription['server_id']} на сервер {new_server_id}")
            
    except Exception as e:
        logger.error(f"Ошибка при смене сервера: {e}")
        await callback.message.answer(
            "❌ Произошла ошибка при смене сервера.\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=get_back_to_start_keyboard()
        ) 
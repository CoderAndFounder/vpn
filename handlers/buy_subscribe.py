import random
import aiosqlite
from loguru import logger
from typing import Optional, Dict
from handlers.x_ui import xui_manager
from handlers.x_ui_ss import xui_ss_manager
from handlers.database import db
from datetime import datetime, timedelta
from handlers.admin.admin_kb import get_admin_keyboard
from aiogram.types import Message
from handlers.user.user_kb import get_allocation_tickets_keyboard

class SubscriptionManager:
    @staticmethod
    def generate_user_id() -> str:
        """Генерация уникального ID пользователя"""
        return f"@{random.randint(10000, 99999)}"

    async def create_subscription(self, user_id: int, tariff_id: int, is_trial: bool = False, bot = None, payment_id: str = None) -> Optional[Dict]:
        """Создание подписки для пользователя"""
        try:
            async with aiosqlite.connect(db.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                if is_trial:
                    async with conn.execute("""
                        SELECT t.*, s.* 
                        FROM trial_settings t 
                        JOIN server_settings s ON t.server_id = s.id 
                        WHERE t.id = ? AND t.is_enable = 1
                    """, (tariff_id,)) as cursor:
                        tariff_data = await cursor.fetchone()
                else:
                    async with conn.execute("""
                        SELECT t.*, s.* 
                        FROM tariff t 
                        JOIN server_settings s ON t.server_id = s.id 
                        WHERE t.id = ? AND t.is_enable = 1
                    """, (tariff_id,)) as cursor:
                        tariff_data = await cursor.fetchone()

                if tariff_data:
                    tariff_data = dict(tariff_data)

            if not tariff_data:
                logger.error(f"Тариф {tariff_id} не найден")
                return None

            end_date = datetime.now() + timedelta(days=tariff_data['left_day'])

            if tariff_data.get('protocol') == 'shadowsocks':
                vless_link = await xui_ss_manager.create_ss_user(
                    server_settings=tariff_data,
                    trial_settings=tariff_data,
                    telegram_id=user_id
                )
            else:
                vless_link = await xui_manager.create_trial_user(
                    server_settings=tariff_data,
                    trial_settings=tariff_data,
                    telegram_id=user_id
                )

            if not vless_link:
                logger.error(f"Ошибка при создании пользователя в X-UI для {user_id}")
                return None

            async with aiosqlite.connect(db.db_path) as conn:
                await conn.execute("""
                    INSERT INTO user_subscription 
                    (user_id, tariff_id, server_id, end_date, vless, is_active, payment_id)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                """, (
                    user_id, 
                    tariff_id, 
                    tariff_data['server_id'], 
                    end_date, 
                    vless_link,
                    payment_id
                ))
                await conn.commit()

                if bot:
                    async with conn.execute(
                        'SELECT pay_notify FROM bot_settings LIMIT 1'
                    ) as cursor:
                        notify_settings = await cursor.fetchone()

                    if notify_settings and notify_settings[0] != 0:
                        async with conn.execute(
                            'SELECT username FROM user WHERE telegram_id = ?',
                            (user_id,)
                        ) as cursor:
                            user_data = await cursor.fetchone()
                            username = user_data[0] if user_data else f"ID: {user_id}"

                        message_text = (
                            "🎉 Новая подписка! 🏆\n"
                            "<blockquote>"
                            f"👤 Пользователь: {username}\n"
                            f"💳 Тариф: {tariff_data['name']}\n"
                            f"📅 Дата активации: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                            "🚀 Подписка успешно оформлена!</blockquote>"
                        )

                        try:
                            await bot.send_message(
                                chat_id=notify_settings[0],
                                text=message_text,
                                parse_mode="HTML",
                                reply_markup=get_admin_keyboard()
                            )
                        except Exception as e:
                            logger.error(f"Ошибка при отправке уведомления о подписке: {e}")

            if not is_trial:
                tickets_count = self._calculate_tickets(tariff_data['left_day'])
                if tickets_count > 0:
                    active_raffle = await self._get_active_raffle()
                    if active_raffle:
                        if await db.add_raffle_tickets(
                            user_id=user_id,
                            telegram_id=user_id,
                            tickets_count=tickets_count,
                            raffle_id=active_raffle['id']
                        ):
                            logger.info(f"Начислено {tickets_count} билетов пользователю {user_id}")
                            
                            if bot:
                                try:
                                    await bot.send_message(
                                        chat_id=user_id,
                                        text=(
                                            f"✨ Поздравляем! Вам начислено <b>{tickets_count}</b> "
                                            f"{'билет' if tickets_count == 1 else 'билета' if 2 <= tickets_count <= 4 else 'билетов'} "
                                            "за покупку подписки! \n\n"
                                            "Спасибо за участие в розыгрыше! 🍀🎲\n"
                                            "Посмотреть все ваши билеты можно, нажав на кнопку <b>Розыгрыша</b> в меню ниже. 🔖"
                                        ),
                                        parse_mode="HTML",
                                        reply_markup= await get_allocation_tickets_keyboard()
                                    )
                                except Exception as e:
                                    logger.error(f"Ошибка при отправке уведомления о билетах пользователю: {e}")

            return {
                'vless': vless_link,
                'end_date': end_date,
                'tariff': tariff_data
            }

        except Exception as e:
            logger.error(f"Ошибка при создании подписки: {e}")
            return None

    def _calculate_tickets(self, days: int) -> int:
        """Расчет количества билетов в зависимости от срока подписки"""
        if days <= 31:
            return 1
        elif days <= 62:
            return 3
        elif days <= 180:
            return 9
        elif days <= 365:
            return 18
        else:
            return 60

    async def _get_active_raffle(self) -> Optional[Dict]:
        """Получение активного розыгрыша"""
        try:
            active_raffles = await db.get_active_raffles()
            return active_raffles[0] if active_raffles else None
        except Exception as e:
            logger.error(f"Ошибка при получении активного розыгрыша: {e}")
            return None

subscription_manager = SubscriptionManager()

async def process_successful_payment(message: Message):
    """Обработка успешного платежа"""
    try:
        subscription = await subscription_manager.create_subscription(
            user_id=message.from_user.id,
            tariff_id=tariff_id,
            bot=message.bot,    
            payment_id=payment_id
        )
    except Exception as e:
        logger.error(f"Ошибка при обработке успешного платежа: {e}") 
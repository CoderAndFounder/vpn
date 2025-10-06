from yookassa import Configuration, Payment
import uuid
from loguru import logger
from typing import Optional, Tuple
from handlers.database import db
import aiosqlite
from datetime import datetime
from handlers.admin.admin_kb import get_admin_keyboard

class YooKassaManager:
    def __init__(self):
        self.is_initialized = False

    async def init_yookassa(self) -> bool:
        """Инициализация YooKassa с настройками из базы данных"""
        try:
            settings = await db.get_yookassa_settings()
            if not settings or not settings[2] or not settings[3]:  
                logger.error("YooKassa settings are not configured")
                return False
            
            Configuration.account_id = settings[2]  
            Configuration.secret_key = settings[3]  
            self.is_initialized = True
            logger.info(f"YooKassa initialized with shop_id: {settings[2]}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing YooKassa: {e}")
            return False

    async def create_payment(self, amount: float, description: str, user_email: str = None, user_id: str = None, tariff_name: str = None, username: str = None) -> Tuple[Optional[str], Optional[str]]:
        """Создает платеж в YooKassa и возвращает ID платежа и URL для оплаты"""
        if not self.is_initialized and not await self.init_yookassa():
            return None, None
        
        try:
            metadata = {
                "transaction_id": str(uuid.uuid4()),
                "telegram_id": user_id,
                "username": username
            }
            
            if "Пополнение баланса" in description:
                metadata["balance_payment"] = "true"
            elif tariff_name:
                metadata["tariff_name"] = tariff_name

            payment = Payment.create({
                "amount": {
                    "value": str(amount),
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": "https://t.me/BURYAT_VPN_BOT"
                },
                "capture": True,
                "description": description,
                "metadata": metadata,
                "receipt": {
                    "customer": {
                        "email": user_email or "user@example.com"
                    },
                    "items": [
                        {
                            "description": description,
                            "quantity": "1",
                            "amount": {
                                "value": str(amount),
                                "currency": "RUB"
                            },
                            "vat_code": "1",
                            "payment_mode": "full_prepayment",
                            "payment_subject": "service"
                        }
                    ]
                }
            })
            
            return payment.id, payment.confirmation.confirmation_url
            
        except Exception as e:
            logger.error(f"Error creating YooKassa payment: {e}")
            return None, None

    async def check_payment(self, payment_id: str, bot = None) -> bool:
        """Проверяет статус платежа"""
        if not self.is_initialized and not await self.init_yookassa():
            return False
            
        try:
            payment = Payment.find_one(payment_id)
            logger.info(f"Payment {payment_id} status: {payment.status}")
            
            if payment.status == 'succeeded':
                logger.info(f"Payment {payment_id} status: {payment.status}")
                
                if 'balance_payment' in payment.metadata:
                    from handlers.user.user_balance import process_successful_balance_payment
                    await process_successful_balance_payment(
                        payment_id=payment.id,
                        amount=float(payment.amount.value),
                        user_id=int(payment.metadata.get('telegram_id')),
                        bot=bot
                    )
                else:
                    if bot:
                        async with aiosqlite.connect(db.db_path) as conn:
                            async with conn.execute(
                                'SELECT pay_notify FROM bot_settings LIMIT 1'
                            ) as cursor:
                                notify_settings = await cursor.fetchone()

                            if notify_settings and notify_settings[0] != 0:
                                message_text = (
                                    "🎉 Новая подписка! 🏆\n"
                                    "<blockquote>"
                                    f"👤 Пользователь: {payment.metadata.get('telegram_id')}\n"
                                    f"💳 Тариф: {payment.metadata.get('tariff_name')}\n"
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

                return True
            
        except Exception as e:
            logger.error(f"Error checking payment status: {e}")
            return False

yookassa_manager = YooKassaManager() 
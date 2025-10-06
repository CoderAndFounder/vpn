import aiohttp
import uuid
from loguru import logger
from typing import Optional, Tuple
from handlers.database import db
from datetime import datetime
import aiosqlite
from handlers.admin.admin_kb import get_admin_keyboard


class TBankManager:
    def __init__(self):
        self.is_initialized = False
        self.base_url = "https://ecom.tinkoff.ru/api/v2/"
        self.terminal_key = None
        self.password = None

    async def init_tbank(self) -> bool:
        """Инициализация настроек T-Bank из базы данных"""
        try:
            settings = await db.get_tbank_settings()  # аналог db.get_yookassa_settings()
            if not settings or not settings[2] or not settings[3]:
                logger.error("TBank settings are not configured")
                return False

            self.terminal_key = settings[2]
            self.password = settings[3]
            self.is_initialized = True
            logger.info(f"TBank initialized with terminal_key: {self.terminal_key}")
            return True

        except Exception as e:
            logger.error(f"Error initializing TBank: {e}")
            return False

    async def _post(self, endpoint: str, data: dict) -> Optional[dict]:
        """Отправка POST-запроса к T-Bank API"""
        if not self.is_initialized and not await self.init_tbank():
            return None

        url = f"{self.base_url}{endpoint}"
        data["TerminalKey"] = self.terminal_key

        import hashlib
        import json

        # Подпись формируется как SHA256 от JSON и password
        def _generate_token(payload):
            payload["Password"] = self.password
            sorted_items = sorted(payload.items())
            token_str = "".join(str(v) for k, v in sorted_items)
            return hashlib.sha256(token_str.encode()).hexdigest()

        data["Token"] = _generate_token(data.copy())

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=data) as response:
                result = await response.json()
                if not result.get("Success"):
                    logger.error(f"TBank API error at {endpoint}: {result}")
                return result

    async def create_payment(
        self,
        amount: float,
        description: str,
        user_email: str = None,
        user_id: str = None,
        tariff_name: str = None,
        username: str = None
    ) -> Tuple[Optional[str], Optional[str]]:
        """Создает платеж через T-Bank API"""
        try:
            order_id = str(uuid.uuid4())
            data = {
                "OrderId": order_id,
                "Amount": int(amount * 100),  # копейки
                "Description": description,
                "CustomerKey": str(user_id),
                "DATA": {
                    "telegram_id": user_id,
                    "username": username or "unknown",
                    "tariff_name": tariff_name or "none",
                },
                "SuccessURL": "https://t.me/BURYAT_VPN_BOT",
                "FailURL": "https://t.me/BURYAT_VPN_BOT",
                "NotificationURL": "https://your-server.com/tbank/callback"
            }

            result = await self._post("Init", data)
            if result and result.get("Success"):
                payment_id = result.get("PaymentId")
                payment_url = result.get("PaymentURL")
                return payment_id, payment_url

            return None, None

        except Exception as e:
            logger.error(f"Error creating TBank payment: {e}")
            return None, None

    async def check_payment(self, payment_id: str, bot=None) -> bool:
        """Проверяет статус платежа через T-Bank API"""
        try:
            data = {"PaymentId": payment_id}
            result = await self._post("GetState", data)

            if result and result.get("Status") == "CONFIRMED":
                logger.info(f"Payment {payment_id} succeeded")

                async with aiosqlite.connect(db.db_path) as conn:
                    async with conn.execute(
                        'SELECT pay_notify FROM bot_settings LIMIT 1'
                    ) as cursor:
                        notify_settings = await cursor.fetchone()

                    if notify_settings and notify_settings[0] != 0:
                        message_text = (
                            "🎉 Новая подписка! 🏆\n"
                            "<blockquote>"
                            f"👤 Пользователь: {result.get('OrderId')}\n"
                            f"💳 Тариф: {result.get('DATA', {}).get('tariff_name', 'N/A')}\n"
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
                            logger.error(f"Ошибка при отправке уведомления: {e}")

                return True

            else:
                logger.info(f"Payment {payment_id} status: {result.get('Status')}")
                return False

        except Exception as e:
            logger.error(f"Error checking TBank payment: {e}")
            return False


tbank_manager = TBankManager()

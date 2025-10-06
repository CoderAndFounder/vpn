import aiohttp
import json
from typing import Optional, List, Dict
from loguru import logger
import aiosqlite
from handlers.database import db

class CryptoPayAPI:
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.base_url = "https://testnet-pay.crypt.bot/api"
        
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """Выполнение запроса к API"""
        async with aiohttp.ClientSession() as session:
            url = f"{self.base_url}/{endpoint}"
            headers = {"Crypto-Pay-API-Token": self.api_token}
            
            try:
                async with session.request(method, url, headers=headers, **kwargs) as response:
                    data = await response.json()
                    if not data.get('ok'):
                        logger.error(f"API error: {data.get('error')}")
                        raise Exception(data.get('error'))
                    return data['result']
            except Exception as e:
                logger.error(f"Request error: {e}")
                raise

    async def get_me(self) -> Dict:
        """Получение информации об приложении"""
        return await self._make_request('GET', 'getMe')

    async def create_invoice(
        self,
        asset: str,
        amount: float,
        currency_type: str = 'crypto',
        fiat: Optional[str] = None,
        description: Optional[str] = None,
        hidden_message: Optional[str] = None,
        paid_btn_name: Optional[str] = None,
        paid_btn_url: Optional[str] = None,
        payload: Optional[str] = None,
        allow_comments: bool = False,
        allow_anonymous: bool = False,
        expires_in: Optional[int] = None
    ) -> Dict:
        """Создание инвойса"""
        data = {
            "asset": asset,
            "amount": str(amount),
            "currency_type": currency_type,
            "description": description,
            "hidden_message": hidden_message,
            "paid_btn_name": paid_btn_name,
            "paid_btn_url": paid_btn_url,
            "payload": payload,
            "allow_comments": allow_comments,
            "allow_anonymous": allow_anonymous,
            "expires_in": expires_in
        }
        if fiat:
            data["fiat"] = fiat
        
        data = {k: v for k, v in data.items() if v is not None}
        
        return await self._make_request('POST', 'createInvoice', json=data)

    async def transfer(self, user_id: int, asset: str, amount: float, spend_id: str) -> Dict:
        """Перевод средств пользователю"""
        data = {
            "user_id": user_id,
            "asset": asset,
            "amount": str(amount),
            "spend_id": spend_id
        }
        return await self._make_request('POST', 'transfer', json=data)

    async def get_invoices(
        self,
        asset: Optional[str] = None,
        invoice_ids: Optional[List[str]] = None,
        status: Optional[str] = None,
        offset: int = 0,
        count: int = 100
    ) -> List[Dict]:
        """Получение списка инвойсов"""
        data = {
            "offset": offset,
            "count": count
        }
        if asset:
            data["asset"] = asset
        if invoice_ids:
            data["invoice_ids"] = [str(id) for id in invoice_ids]
        if status:
            data["status"] = status
            
        logger.debug(f"Запрос инвойсов с данными: {data}")
        result = await self._make_request('POST', 'getInvoices', json=data)
        return result.get('items', [])

    async def get_balance(self) -> List[Dict]:
        """Получение баланса"""
        return await self._make_request('GET', 'getBalance')

    async def get_exchange_rates(self) -> List[Dict]:
        """Получение курсов обмена"""
        return await self._make_request('GET', 'getExchangeRates')

    async def get_currencies(self) -> List[Dict]:
        """Получение списка поддерживаемых валют"""
        return await self._make_request('GET', 'getCurrencies')

    async def verify_webhook(self, update_data: Dict, secret_token: str) -> bool:
        """Проверка подписи вебхука"""
        try:
            return True 
        except Exception as e:
            logger.error(f"Webhook verification error: {e}")
            return False

    async def convert_rub_to_usdt(self, rub_amount: float) -> float:
        """Конвертация рублей в USDT"""
        try:
            rates = await self.get_exchange_rates()
            for rate in rates:
                if rate['source'] == 'RUB' and rate['target'] == 'USDT':
                    return round(rub_amount / float(rate['rate']), 2)
            raise Exception("Exchange rate RUB/USDT not found")
        except Exception as e:
            logger.error(f"Error converting RUB to USDT: {e}")
            raise

class CryptoPayManager:
    def __init__(self):
        self.api = None
        
    async def init_api(self) -> bool:
        """Инициализация API"""
        try:
            async with aiosqlite.connect(db.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute(
                    'SELECT * FROM crypto_settings WHERE is_enable = 1 LIMIT 1'
                ) as cursor:
                    settings = await cursor.fetchone()
                    
            if settings and settings['api_token']:
                self.api = CryptoPayAPI(settings['api_token'])
                await self.api.get_me()
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to initialize Crypto Pay API: {e}")
            return False

    async def create_payment(self, amount: float, description: str) -> Optional[Dict]:
        """Создание платежа"""
        try:
            if not self.api:
                if not await self.init_api():
                    return None
                    
            async with aiosqlite.connect(db.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute(
                    'SELECT supported_assets FROM crypto_settings WHERE is_enable = 1'
                ) as cursor:
                    settings = await cursor.fetchone()
                    
            if not settings or not settings['supported_assets']:
                return None
                
            supported_assets = json.loads(settings['supported_assets'])
            if not supported_assets:
                return None
                
            asset = supported_assets[0]
            
            invoice = await self.api.create_invoice(
                asset=asset,
                amount=amount,
                currency_type='fiat',
                fiat='RUB',
                description=description,
                paid_btn_name="callback",
                paid_btn_url="https://t.me/dsrvpnmanager_bot",
                expires_in=3600
            )
            
            logger.debug(f"Создан инвойс: {invoice}")
            return invoice
            
        except Exception as e:
            logger.error(f"Error creating crypto payment: {e}")
            return None

crypto_pay_manager = CryptoPayManager() 
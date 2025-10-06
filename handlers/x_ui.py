from py3xui import Api
from py3xui.client import Client
from loguru import logger
from typing import Optional, Dict, Any
import aiohttp
from datetime import datetime, timedelta
import uuid
import random

class XUIManager:
    def __init__(self):
        self.clients = {}  

    async def get_client(self, server_settings: Dict) -> Optional[Api]:
        """Получение или создание клиента для сервера"""
        server_id = server_settings['id']
        
        if server_id in self.clients:
            return self.clients[server_id]
        
        try:
            logger.info(f"Создание клиента для сервера {server_id}")
            logger.info(f"URL: {server_settings['url']}")
            logger.info(f"Port: {server_settings['port']}")
            logger.info(f"Path: {server_settings['secret_path']}")
            
            url = server_settings['url']
            if not url.startswith('http'):
                url = f"https://{url}"
            url = f"{url}:{server_settings['port']}/{server_settings['secret_path']}"
            
            logger.info(f"API URL: {url}")
            
            client = Api(
                url,
                server_settings['username'],
                server_settings['password'],
                use_tls_verify=False
            )
            
            client.login()
            inbounds = client.inbound.get_list()
            logger.info(f"Подключение успешно. Найдено {len(inbounds)} inbounds")
            
            self.clients[server_id] = client
            return client
            
        except Exception as e:
            logger.error(f"Ошибка при создании клиента X-UI для сервера {server_id}: {e}")
            return None

    def _find_inbound(self, inbounds: list, inbound_id: int) -> Optional[Any]:
        """Поиск inbound по ID"""
        return next((i for i in inbounds if i.id == inbound_id), None)

    async def create_trial_user(self, server_settings: Dict, trial_settings: Dict, telegram_id: int) -> Optional[str]:
        """Создание пользователя"""
        try:
            logger.info(f"Начало создания пользователя для telegram_id: {telegram_id}")
            
            client = await self.get_client(server_settings)
            if not client:
                logger.error(f"Не удалось получить клиента для сервера {server_settings['id']}")
                return None

            end_time = datetime.now() + timedelta(days=trial_settings['left_day'])
            
            inbound_id = server_settings.get('inbound_id', 1)
            
            unique_id = ''.join([str(random.randint(0, 9)) for _ in range(5)])
            email = f"tg_{telegram_id}@{unique_id}"
            
            logger.info(f"Создание пользователя в inbound {inbound_id}")
            logger.info(f"Email: {email}")
            logger.info(f"Дата окончания: {end_time}")

            inbounds = client.inbound.get_list()
            logger.info(f"Подключение успешно. Найдено {len(inbounds)} inbounds")
            
            inbound = self._find_inbound(inbounds, inbound_id)
            if not inbound:
                logger.error(f"Inbound {inbound_id} не найден на сервере {server_settings['id']}")
                return None
            
            logger.debug(f"Текущий inbound: {inbound}")

            client_id = str(uuid.uuid4())
            new_client = Client(
                id=client_id,
                email=email,
                enable=True,
                flow="xtls-rprx-vision",
                tg_id=str(telegram_id),
                total_gb=0,  
                expiry_time=int(end_time.timestamp() * 1000),  
                limit_ip=0,
                reset=0,
                password="",
                method="",
                sub_id="",
                up=0,
                down=0,
                total=0,
                inbound_id=inbound_id
            )

            success = False
            try:
                logger.debug("Попытка создания клиента первым способом...")
                client.client.add(inbound_id, new_client)
                logger.info("Клиент успешно создан первым способом")
                success = True
            except Exception as e:
                logger.debug(f"Ошибка при добавлении клиента первым способом: {e}")
                try:
                    logger.debug("Попытка создания клиента вторым способом...")
                    client.client.add(inbound_id, [new_client])
                    logger.info("Клиент успешно создан вторым способом")
                    success = True
                except Exception as e:
                    logger.error(f"Ошибка при добавлении клиента вторым способом: {e}")

            if not success:
                logger.error(f"Не удалось создать клиента для пользователя {telegram_id}")
                return None

            logger.debug("Начало формирования ссылки для подключения")
            host = server_settings['url']
            if not host.startswith('http'):
                host = f"https://{host}"
            host = host.split('://')[1]  

            reality_settings = inbound.stream_settings.reality_settings
            
            params = {
                'type': 'tcp',
                'security': 'reality',
                'pbk': reality_settings['settings']['publicKey'],
                'fp': 'chrome',
                'sni': reality_settings['serverNames'][0],
                'sid': reality_settings['shortIds'][0],
                'spx': '/',
                'flow': 'xtls-rprx-vision'
            }
            
            params_str = '&'.join([f"{k}={v}" for k, v in params.items()])
            
            link = f"vless://{client_id}@{host}:{inbound.port}?{params_str}#{email}"
            
            logger.info(f"Ссылка для клиента успешно сгенерирована: {link}")
            return link

        except Exception as e:
            logger.error(f"Критическая ошибка при создании пользователя {telegram_id}: {e}")
            logger.exception("Полный стек ошибки:")
            return None

    async def delete_user(self, server_settings: Dict, telegram_id: int) -> bool:
        """Удаление пользователя"""
        try:
            client = await self.get_client(server_settings)
            if not client:
                return False

            inbound_id = server_settings.get('inbound_id', 1)
            email = f"tg_{telegram_id}_trial"
            
            success = client.client.remove(inbound_id, email)
            return success

        except Exception as e:
            logger.error(f"Ошибка при удалении пользователя {telegram_id}: {e}")
            return False

xui_manager = XUIManager()

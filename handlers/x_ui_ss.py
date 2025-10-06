from loguru import logger
from typing import Optional, Dict, Any, List
import aiohttp
from datetime import datetime, timedelta
import uuid
import random
import base64
import os
import secrets
import json
import string

class XUIShadowsocksManager:
    def __init__(self):
        self.sessions = {}  

    async def _login(self, server_settings: Dict) -> Optional[str]:
        """Авторизация на сервере и получение токена сессии"""
        server_id = server_settings.get('server_id', server_settings.get('id'))
        
        try:
            base_url = server_settings['url']
            logger.debug(f"Исходный URL: {base_url}")
            if not base_url.startswith('http'):
                base_url = f"https://{base_url}"
            if f":{server_settings['port']}" in base_url:
                base_url = f"{base_url}"
            else:
                base_url = f"{base_url}:{server_settings['port']}"
            logger.debug(f"Сформированный base_url: {base_url}")
            
            login_url = f"{base_url}/{server_settings['secret_path']}/login"
            logger.debug(f"URL для логина: {login_url}")
            
            login_data = {
                'username': server_settings['username'],
                'password': server_settings['password']
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    login_url,
                    json=login_data,
                    headers={
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    ssl=False
                ) as response:
                    response_text = await response.text()
                    logger.debug(f"Ответ сервера: {response.status}, {response_text}")
                    
                    if response.status != 200:
                        logger.error(f"Ошибка авторизации на сервере {server_id}: {response.status}")
                        return None
                    
                    cookies = response.cookies
                    logger.debug(f"Полученные cookies: {cookies}")
                    session_token = cookies.get('session') or cookies.get('3x-ui')
                    if not session_token:
                        logger.error(f"Не удалось получить токен сессии для сервера {server_id}")
                        return None
                    
                    self.sessions[server_id] = {
                        'token': session_token.value,
                        'base_url': f"{base_url}/{server_settings['secret_path']}",
                        'cookie_name': 'session' if cookies.get('session') else '3x-ui'
                    }
                    
                    logger.info(f"Успешная авторизация на сервере {server_id}")
                    return session_token.value
            
        except Exception as e:
            logger.error(f"Ошибка при авторизации на сервере {server_id}: {e}")
            return None

    async def _get_session(self, server_settings: Dict) -> Optional[Dict]:
        """Получение или создание сессии для сервера"""
        server_id = server_settings.get('server_id', server_settings.get('id'))
        
        if server_id in self.sessions:
            return self.sessions[server_id]
        
        token = await self._login(server_settings)
        if not token:
            return None
        
        return self.sessions[server_id]

    async def _get_inbounds(self, server_settings: Dict) -> Optional[List]:
        """Получение списка inbounds с сервера"""
        session_data = await self._get_session(server_settings)
        if not session_data:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{session_data['base_url']}/panel/api/inbounds/list",
                    headers={
                        'Accept': 'application/json',
                        'Cookie': f"{session_data['cookie_name']}={session_data['token']}"
                    },
                    ssl=False
                ) as response:
                    if response.status != 200:
                        logger.error(f"Ошибка получения списка inbounds: {response.status}")
                        return None
                    
                    data = await response.json()
                    if not data.get('success'):
                        logger.error(f"Ошибка в ответе API: {data.get('msg')}")
                        return None
                    
                    return data.get('obj', [])
            
        except Exception as e:
            logger.error(f"Ошибка при получении списка inbounds: {e}")
            return None

    async def _get_inbound(self, server_settings: Dict, inbound_id: int) -> Optional[Dict]:
        """Получение информации о конкретном inbound"""
        session_data = await self._get_session(server_settings)
        if not session_data:
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{session_data['base_url']}/panel/api/inbounds/get/{inbound_id}",
                    headers={
                        'Accept': 'application/json',
                        'Cookie': f"{session_data['cookie_name']}={session_data['token']}"
                    },
                    ssl=False
                ) as response:
                    if response.status != 200:
                        logger.error(f"Ошибка получения информации об inbound {inbound_id}: {response.status}")
                        return None
                    
                    data = await response.json()
                    if not data.get('success'):
                        logger.error(f"Ошибка в ответе API: {data.get('msg')}")
                        return None
                    
                    return data.get('obj')
            
        except Exception as e:
            logger.error(f"Ошибка при получении информации об inbound {inbound_id}: {e}")
            return None

    def _generate_ss_password(self) -> str:
        """Генерация пароля для Shadowsocks клиента"""
        random_bytes = secrets.token_bytes(32)
        return base64.b64encode(random_bytes).decode('utf-8')

    async def create_ss_user(self, server_settings: Dict, trial_settings: Dict, telegram_id: int) -> Optional[str]:
        """Создание пользователя Shadowsocks"""
        try:
            logger.info(f"Начало создания SS пользователя для telegram_id: {telegram_id}")
            
            server_id = server_settings.get('server_id', server_settings.get('id'))
            logger.debug(f"Используем ID сервера: {server_id}")
            
            session_data = await self._get_session(server_settings)
            if not session_data:
                logger.error(f"Не удалось получить сессию для сервера {server_id}")
                return None

            end_time = datetime.now() + timedelta(days=trial_settings['left_day'])
            
            inbound_id = server_settings.get('inbound_id', 1)
            
            email = f"tg_{telegram_id}@{random.randint(10000, 99999)}"
            
            inbound = await self._get_inbound(server_settings, inbound_id)
            if not inbound:
                logger.error(f"Не удалось получить информацию об inbound {inbound_id}")
                return None
            
            logger.debug(f"Найден inbound: {inbound}")
            
            try:
                settings = json.loads(inbound['settings'])
                logger.debug(f"Настройки inbound: {settings}")
                
                existing_emails = [client.get('email') for client in settings.get('clients', [])]
                logger.debug(f"Существующие email: {existing_emails}")
                if email in existing_emails:
                    logger.warning(f"Клиент с email {email} уже существует, генерируем новый email")
                    email = f"tg_{telegram_id}@{random.randint(10000, 99999)}"
                
                method = settings.get('method', '2022-blake3-aes-256-gcm')
                server_password = settings.get('password', '')
                
                logger.debug(f"Метод шифрования: {method}")
                logger.debug(f"Получен пароль сервера: {server_password}")
            except Exception as e:
                logger.error(f"Ошибка при парсинге настроек inbound: {e}")
                return None

            client_password = base64.b64encode(secrets.token_bytes(32)).decode()
            
            if ':' in server_password:
                full_password = server_password
            else:
                full_password = f"{server_password}:{client_password}"
            
            logger.debug(f"Сформирован полный пароль: {full_password}")

            new_client = {
                "id": str(uuid.uuid4()),
                "email": email,
                "enable": True,
                "tgId": str(telegram_id),
                "totalGB": 0,
                "expiryTime": int(end_time.timestamp() * 1000),
                "limitIp": 0,
                "reset": 0,
                "password": client_password,  
                "subId": "",
                "up": 0,
                "down": 0,
                "total": 0
            }

            logger.debug(f"Попытка добавить клиента: {new_client}")
            
            payload = {
                "id": inbound_id,
                "settings": json.dumps({"clients": [new_client]}, separators=(',', ':'))
            }
            
            logger.debug(f"Отправляемый payload: {payload}")
            
            clients = settings.get('clients', [])
            
            clients.append(new_client)
            
            settings['clients'] = clients

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{session_data['base_url']}/panel/api/inbounds/addClient",
                    headers={
                        'Accept': 'application/json',
                        'Content-Type': 'application/json',
                        'Cookie': f"{session_data['cookie_name']}={session_data['token']}"
                    },
                    json=payload,
                    ssl=False
                ) as response:
                    status = response.status
                    text = await response.text()
                    logger.debug(f"Статус ответа: {status}, URL: {session_data['base_url']}/panel/api/inbounds/addClient, Текст: {text}")
                    
                    data = json.loads(text) if text else {}
                    if status != 200 or not data.get('success', False):
                        error_msg = data.get('msg', 'Неизвестная ошибка')
                        logger.error(f"Ошибка при добавлении клиента: {error_msg}")
                        raise Exception(f"Ошибка при добавлении клиента: {error_msg}")
            
            logger.info("SS клиент успешно создан")

            host = server_settings['url']
            if '://' in host:
                host = host.split('://')[1]
           
            if ':' in host:
                host = host.split(':')[0]

            method = "2022-blake3-aes-256-gcm"  
            method_and_password = f"{method}:{full_password}"
            encoded_part = base64.b64encode(method_and_password.encode()).decode()

            encoded_email = email.replace('@', '%40')
            
            ss_link = f"ss://{encoded_part}@{host}:{inbound['port']}?type=tcp#SS-2022-{encoded_email}"
            
            logger.info(f"SS ссылка для клиента успешно сгенерирована: {ss_link}")
            return ss_link
            
        except Exception as e:
            logger.error(f"Ошибка при создании SS пользователя: {e}")
            return None

    async def delete_ss_user(self, server_settings: Dict, email: str) -> bool:
        """Удаление пользователя Shadowsocks"""
        try:
            session_data = await self._get_session(server_settings)
            if not session_data:
                logger.error("Не удалось получить сессию")
                return False

            inbound_id = server_settings.get('inbound_id', 1)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{session_data['base_url']}/panel/api/inbounds/list",
                    headers={'Cookie': f"{session_data['cookie_name']}={session_data['token']}"},
                    ssl=False
                ) as response:
                    data = await response.json()
                    inbounds = data.get('obj', [])
                    
                    target_inbound = next((i for i in inbounds if i['id'] == inbound_id), None)
                    if not target_inbound:
                        raise Exception(f"Inbound {inbound_id} не найден")
                    
                    settings = json.loads(target_inbound['settings'])
                    clients = settings.get('clients', [])
                    
                    email_prefix = email.rstrip('@')  
                    target_client = next((c for c in clients if c['email'].startswith(email_prefix)), None)
                    
                    if not target_client:
                        logger.warning(f"Клиент с email, начинающимся с {email_prefix}, не найден")
                        return False
                    
                    full_email = target_client['email']
                    logger.info(f"Найден полный email клиента: {full_email}")
                    
                    async with session.post(
                        f"{session_data['base_url']}/panel/api/inbounds/{inbound_id}/delClient/{full_email}",
                        headers={'Cookie': f"{session_data['cookie_name']}={session_data['token']}"},
                        ssl=False
                    ) as response:
                        status = response.status
                        text = await response.text()
                        logger.debug(f"Статус ответа: {status}, Текст: {text}")
                        
                        data = json.loads(text)
                        if status != 200 or not data.get('success', False):
                            error_msg = data.get('msg', 'Неизвестная ошибка')
                            raise Exception(f"Ошибка при удалении клиента: {error_msg}")
                
                logger.info(f"SS клиент {full_email} успешно удален")
                return True
            
        except Exception as e:
            logger.error(f"Ошибка при удалении SS пользователя: {e}")
            return False

xui_ss_manager = XUIShadowsocksManager() 
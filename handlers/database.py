import os
import aiosqlite
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, List, Union
from loguru import logger
from aiogram import Bot
from handlers.admin.admin_kb import get_admin_keyboard
import random
import string
import asyncio

os.makedirs('instance', exist_ok=True)
os.makedirs('handlers', exist_ok=True)

class Database:
    def __init__(self, db_path: str = 'instance/database.db'):
        self.db_path = db_path

    async def db_operation_with_retry(self, operation_func, max_attempts=5):
        """Выполнение операции с базой данных с повторными попытками при блокировке"""
        for attempt in range(1, max_attempts + 1):
            try:
                return await operation_func()
            except aiosqlite.OperationalError as e:
                if "database is locked" in str(e) and attempt < max_attempts:
                    wait_time = 0.1 * (2 ** (attempt - 1))  
                    logger.warning(f"База данных заблокирована, повторная попытка {attempt} через {wait_time:.2f}с")
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Ошибка базы данных после {attempt} попыток: {e}")
                    raise
            except Exception as e:
                logger.error(f"Неожиданная ошибка при работе с базой данных: {e}")
                raise

    async def init_db(self):
        """Инициализация базы данных"""
        async def _init_db_operation():
            async with aiosqlite.connect(self.db_path, timeout=20.0) as conn:
                 
                await conn.execute("PRAGMA journal_mode=WAL;")      
                await conn.execute("PRAGMA synchronous=NORMAL;")    
                await conn.execute("PRAGMA busy_timeout=2000;")     
                
                
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS bot_settings (
                        bot_token TEXT NOT NULL,
                        admin_id TEXT NOT NULL,
                        chat_id TEXT,
                        chanel_id TEXT,
                        is_enable BOOLEAN NOT NULL DEFAULT 1
                    )
                ''')
                
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS server_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        ip TEXT,
                        url TEXT NOT NULL,
                        port TEXT NOT NULL,
                        secret_path TEXT NOT NULL,
                        username TEXT NOT NULL,
                        password TEXT NOT NULL,
                        secretkey TEXT,
                        inbound_id INTEGER,
                        protocol TEXT DEFAULT 'vless',
                        is_enable BOOLEAN NOT NULL DEFAULT 1
                    )
                ''')
                
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS bot_message (
                        command TEXT PRIMARY KEY,
                        text TEXT NOT NULL,
                        image_path TEXT,
                        is_enable BOOLEAN NOT NULL DEFAULT 1
                    )
                ''')

                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS user (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT,
                        telegram_id INTEGER UNIQUE NOT NULL,
                        trial_period BOOLEAN DEFAULT 0,
                        is_enable BOOLEAN NOT NULL DEFAULT 1,
                        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        referral_code TEXT UNIQUE,
                        referral_count INTEGER DEFAULT 0,
                        referred_by TEXT
                    )
                ''')

                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS tariff (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        price DECIMAL(10,2) NOT NULL,
                        left_day INTEGER NOT NULL,
                        server_id INTEGER NOT NULL,
                        is_enable BOOLEAN NOT NULL DEFAULT 1,
                        FOREIGN KEY (server_id) REFERENCES server_settings(id)
                    )
                ''')

                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS trial_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        left_day INTEGER NOT NULL,
                        server_id INTEGER NOT NULL,
                        is_enable BOOLEAN NOT NULL DEFAULT 1,
                        FOREIGN KEY (server_id) REFERENCES server_settings(id)
                    )
                ''')

                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS user_subscription (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        tariff_id INTEGER NOT NULL,
                        server_id INTEGER NOT NULL,
                        start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        end_date TIMESTAMP NOT NULL,
                        vless TEXT,
                        is_active BOOLEAN NOT NULL DEFAULT 1,
                        FOREIGN KEY (user_id) REFERENCES user(id),
                        FOREIGN KEY (tariff_id) REFERENCES tariff(id),
                        FOREIGN KEY (server_id) REFERENCES server_settings(id)
                    )
                ''')

                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS yookassa_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT,
                        shop_id TEXT NOT NULL,
                        api_key TEXT NOT NULL,
                        description TEXT,
                        is_enable INTEGER DEFAULT 0
                    )
                ''')

                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS promocodes (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        promocod TEXT NOT NULL,
                        activation_limit INTEGER DEFAULT 1,
                        activation_total INTEGER DEFAULT 0,
                        percentage DECIMAL(5,2) NOT NULL,
                        is_enable BOOLEAN NOT NULL DEFAULT 1,
                        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')

                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS payments (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        tariff_id INTEGER NOT NULL,
                        price REAL NOT NULL,
                        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES user (id),
                        FOREIGN KEY (tariff_id) REFERENCES tariff (id)
                    )
                """)
                
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS support_info (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        message TEXT NOT NULL,
                        bot_version TEXT NOT NULL,
                        support_url TEXT NOT NULL
                    )
                ''')
                
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS notify_settings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        interval INTEGER NOT NULL,
                        type TEXT NOT NULL,
                        is_enable BOOLEAN NOT NULL DEFAULT 1
                    )
                ''')
                
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS payments_code (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pay_code TEXT UNIQUE NOT NULL,
                        sum DECIMAL(10,2) NOT NULL,
                        is_enable BOOLEAN NOT NULL DEFAULT 1,
                        create_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                ''')
                
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS crypto_settings (
                        api_token TEXT NOT NULL,
                        is_enable BOOLEAN DEFAULT 0,
                        min_amount DECIMAL(10,2) DEFAULT 1.00,
                        supported_assets TEXT,  -- JSON строка с поддерживаемыми криптовалютами
                        webhook_url TEXT,
                        webhook_secret TEXT
                    )
                ''')
                
                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS raffles (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        start_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        end_date TIMESTAMP,
                        status TEXT DEFAULT 'active',
                        winner_ticket_id INTEGER,
                        FOREIGN KEY (winner_ticket_id) REFERENCES raffle_tickets(id)
                    )
                ''')

                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS raffle_tickets (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        telegram_id INTEGER NOT NULL,
                        ticket_number TEXT UNIQUE NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        raffle_id INTEGER,
                        FOREIGN KEY (user_id) REFERENCES user(id),
                        FOREIGN KEY (raffle_id) REFERENCES raffles(id),
                        FOREIGN KEY (telegram_id) REFERENCES user(telegram_id)
                    )
                ''')

                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS user_balance (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        balance DECIMAL(10,2) DEFAULT 0.00,
                        last_update TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES user(telegram_id)
                    )
                ''')

                await conn.execute('''
                    CREATE TABLE IF NOT EXISTS balance_transactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        amount DECIMAL(10,2) NOT NULL,
                        type TEXT NOT NULL,
                        description TEXT,
                        payment_id TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES user(telegram_id)
                    )
                ''')

                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS referral_condition (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL,
                        description TEXT,
                        invitations INTEGER NOT NULL,
                        reward_sum DECIMAL(10,2) NOT NULL,
                        is_enable BOOLEAN NOT NULL DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await conn.commit()
               # logger.info("Таблица referral_condition успешно создана или уже существует")

                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS referral_progress (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        total_invites INTEGER DEFAULT 0,
                        last_reward_at TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES user(telegram_id)
                    )
                """)
                await conn.commit()
               # logger.info("Таблица referral_progress успешно создана или уже существует")

                await conn.execute("""
                    CREATE INDEX IF NOT EXISTS idx_referral_progress_user_id 
                    ON referral_progress(user_id)
                """)
                await conn.commit()
                logger.info("Индексы для таблиц рефералов успешно созданы")

                async with conn.execute("SELECT COUNT(*) FROM referral_condition") as cursor:
                    count = await cursor.fetchone()
                    if count[0] == 0:
                        await conn.execute("""
                            INSERT INTO referral_condition (name, description, invitations, reward_sum)
                            VALUES 
                            ('Начальный уровень', 'Пригласите 5 друзей и получите награду', 5, 50.00),
                            ('Продвинутый уровень', 'Пригласите 10 друзей и получите награду', 10, 150.00),
                            ('Профессионал', 'Пригласите 25 друзей и получите награду', 25, 500.00)
                        """)
                        await conn.commit()
                     #   logger.info("Добавлены тестовые условия реферальной программы")

                await conn.execute("""
                    CREATE TABLE IF NOT EXISTS referral_rewards_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        condition_id INTEGER NOT NULL,
                        reward_sum DECIMAL(10,2) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES user(telegram_id),
                        FOREIGN KEY (condition_id) REFERENCES referral_condition(id)
                    )
                """)
                await conn.commit()
               # logger.info("Таблица referral_rewards_history успешно создана или уже существует")

                await conn.commit()
                logger.info("База данных инициализирована")
        
        return await self.db_operation_with_retry(_init_db_operation)

    async def get_bot_settings(self) -> Optional[Dict]:
        """Получение настроек бота из базы данных"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT * FROM bot_settings LIMIT 1') as cursor:
                settings = await cursor.fetchone()
                if settings:
                    return {
                        'bot_token': settings[0],
                        'admin_id': settings[1].split(','),
                        'chat_id': settings[2],
                        'chanel_id': settings[3],
                        'is_enable': bool(settings[4])
                    }
                return None

    async def get_bot_message(self, command: str) -> Optional[Dict]:
        """Получение сообщения бота по команде"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute(
                'SELECT * FROM bot_message WHERE command = ? AND is_enable = 1', 
                (command,)
            ) as cursor:
                message = await cursor.fetchone()
                if message:
                    return {
                        'command': message[0],
                        'text': message[1],
                        'image_path': message[2],
                        'is_enable': bool(message[3])
                    }
                return None

    async def get_all_servers(self) -> List[Dict]:
        """Получение списка всех серверов"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute('SELECT * FROM server_settings') as cursor:
                servers = await cursor.fetchall()
                return [dict(server) for server in servers]

    async def register_user(self, telegram_id: int, username: str = None, bot = None) -> bool:
        """Регистрация нового пользователя"""
        try:
            current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    'SELECT id FROM user WHERE telegram_id = ?',
                    (telegram_id,)
                ) as cursor:
                    if await cursor.fetchone():
                        return True  
                
                while True:
                    referral_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                    
                    async with db.execute(
                        'SELECT id FROM user WHERE referral_code = ?',
                        (referral_code,)
                    ) as cursor:
                        if not await cursor.fetchone():
                            break
                
                await db.execute(
                    'INSERT INTO user (telegram_id, username, referral_code) VALUES (?, ?, ?)',
                    (telegram_id, username, referral_code)
                )
                await db.commit()

                await db.execute("""
                    INSERT INTO referral_progress (user_id, total_invites)
                    VALUES (?, 0)
                """, (telegram_id,))
                await db.commit()
                
                async with db.execute(
                    'SELECT reg_notify FROM bot_settings LIMIT 1'
                ) as cursor:
                    notify_settings = await cursor.fetchone()
                
                    
                if notify_settings and notify_settings[0] != 0 and bot:
                    
                    message_text = (
                        "🔔 Новая регистрация! 👤\n\n"
                        "🚀 Пользователь успешно зарегистрирован!\n"
                        "<blockquote>"
                        f"📌 ID: {telegram_id}\n"
                        f"👤 Username: {username or 'Не указан'}\n"
                        f"📅 Дата: {current_date}\n"
                        "</blockquote>"
                    )
                    
                    try:
                        await bot.send_message(
                            chat_id=notify_settings[0],
                            text=message_text,
                            parse_mode="HTML",
                            reply_markup=get_admin_keyboard()
                        )
                    except Exception as e:
                        logger.error(f"Ошибка при отправке уведомления о регистрации: {e}")
            
            logger.info(f"Зарегистрирован новый пользователь: {telegram_id}")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при регистрации пользователя {telegram_id}: {e}")
            return False

    async def get_user(self, telegram_id: int) -> Optional[Dict]:
        """Получение информации о пользователе"""
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                'SELECT * FROM user WHERE telegram_id = ?',
                (telegram_id,)
            ) as cursor:
                user = await cursor.fetchone()
                return dict(user) if user else None

    async def get_active_trial_settings(self) -> Optional[Dict]:
        """Получение активных настроек пробного периода"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute('''
                    SELECT t.*, s.name as server_name 
                    FROM trial_settings t 
                    JOIN server_settings s ON t.server_id = s.id
                    WHERE t.is_enable = 1 
                    LIMIT 1
                ''') as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка при получении настроек пробного периода: {e}")
            return None

    async def update_user_trial_status(self, telegram_id: int, used: bool = True) -> bool:
        """Обновление статуса использования пробного периода"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'UPDATE user SET trial_period = ? WHERE telegram_id = ?',
                    (used, telegram_id)
                )
                await db.commit()
                logger.info(f"Обновлен статус пробного периода для пользователя {telegram_id}: {used}")
                return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении статуса пробного периода для пользователя {telegram_id}: {e}")
            return False

    async def is_admin(self, user_id: int) -> bool:
        """Проверка является ли пользователь администратором"""
        settings = await self.get_bot_settings()
        if settings and settings['admin_id']:
            return str(user_id) in settings['admin_id']
        return False

    async def get_server_settings(self, server_id: int) -> Optional[Dict]:
        """Получение настроек сервера по ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    'SELECT * FROM server_settings WHERE id = ?',
                    (server_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка при получении настроек сервера {server_id}: {e}")
            return None

    async def get_connection(self):
        """Получение соединения с базой данных"""
        return await aiosqlite.connect(self.db_path)

    async def get_active_tariffs(self, server_id: Optional[int] = None) -> List[Dict]:
        """
        Получение списка активных тарифов с возможностью фильтрации по серверу
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    
                    query = """
                        SELECT t.*, s.name as server_name 
                        FROM tariff t 
                        JOIN server_settings s ON t.server_id = s.id 
                        WHERE t.is_enable = 1
                    """
                    params = []
                    
                    if server_id is not None:
                        query += " AND t.server_id = ?"
                        params.append(server_id)
                    
                    query += " ORDER BY t.id"
                    
                    async with conn.execute(query, params) as cursor:
                        tariffs = await cursor.fetchall()
                    
                    result = []
                    for tariff in tariffs:
                        result.append(dict(tariff))
                    return result
            except Exception as e:
                logger.error(f"Ошибка при получении активных тарифов: {e}")
                return []
        
        return await self.db_operation_with_retry(_operation)

    async def get_yookassa_settings(self):
        """Получение настроек YooKassa"""
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute("SELECT * FROM yookassa_settings LIMIT 1") as cursor:
                settings = await cursor.fetchone()
                return settings if settings else None

    async def update_yookassa_settings(self, name, shop_id, api_key, description, is_enable):
        """Обновление настроек YooKassa"""
        async with await self.get_connection() as db:
            await db.execute('''
                INSERT OR REPLACE INTO yookassa_settings (id, name, shop_id, api_key, description, is_enable)
                VALUES (1, ?, ?, ?, ?, ?)
            ''', (name, shop_id, api_key, description, is_enable))
            await db.commit()

    async def enable_yookassa(self, enable: bool):
        """Включение/выключение YooKassa"""
        async with await self.get_connection() as db:
            await db.execute("UPDATE yookassa_settings SET is_enable = ?", (int(enable),))
            await db.commit()

    async def add_promo_tariff(self, name: str, description: str, left_day: int, server_id: Optional[int] = None) -> bool:
        """
        Добавление нового промо-тарифа
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    await conn.execute("""
                        INSERT INTO tariff_promo (name, description, left_day, server_id, is_enable)
                        VALUES (?, ?, ?, ?, 1)
                    """, (name, description, left_day, server_id))
                    await conn.commit()
                    return True
            except Exception as e:
                logger.error(f"Ошибка при добавлении промо-тарифа: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def get_promo_tariffs(self) -> list:
        """Получение списка активных промо-тарифов"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute("""
                    SELECT tp.*, ss.name as server_name
                    FROM tariff_promo tp
                    JOIN server_settings ss ON tp.server_id = ss.id
                    WHERE tp.is_enable = 1
                """) as cursor:
                    return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка при получении списка промо-тарифов: {e}")
            return []

    async def delete_promo_tariff(self, tariff_id: int) -> bool:
        """Деактивация промо-тарифа"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    UPDATE tariff_promo 
                    SET is_enable = 0 
                    WHERE id = ?
                """, (tariff_id,))
                await conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка при удалении промо-тарифа: {e}")
            return False

    async def get_server_promo_inbound(self, server_id: int) -> int:
        """Получение promo inbound_id для сервера"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                async with conn.execute("""
                    SELECT inbound_id_promo 
                    FROM server_settings 
                    WHERE id = ?
                """, (server_id,)) as cursor:
                    result = await cursor.fetchone()
                    return result[0] if result else None
        except Exception as e:
            logger.error(f"Ошибка при получении promo inbound_id: {e}")
            return None

    async def set_reg_notify(self, chat_id: int) -> bool:
        """Установка ID чата для уведомлений о регистрации"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    UPDATE bot_settings 
                    SET reg_notify = ?
                """, (chat_id,))
                await conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка при установке ID чата для уведомлений о регистрации: {e}")
            return False

    async def set_pay_notify(self, chat_id: int) -> bool:
        """Установка ID чата для уведомлений о платежах"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    UPDATE bot_settings 
                    SET pay_notify = ?
                """, (chat_id,))
                await conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка при установке ID чата для уведомлений о платежах: {e}")
            return False

    async def get_notify_settings(self) -> dict:
        """Получение настроек уведомлений"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute("""
                    SELECT reg_notify, pay_notify 
                    FROM bot_settings 
                    LIMIT 1
                """) as cursor:
                    return dict(await cursor.fetchone())
        except Exception as e:
            logger.error(f"Ошибка при получении настроек уведомлений: {e}")
            return {}

    async def add_review(self, username: str, message: str) -> bool:
        """Добавление нового отзыва"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    INSERT INTO Reviews (username, message)
                    VALUES (?, ?)
                """, (username, message))
                await conn.commit()
            return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении отзыва: {e}")
            return False

    async def get_reviews(self, limit: int = 10) -> list:
        """Получение последних отзывов"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                async with conn.execute("""
                    SELECT * FROM Reviews 
                    ORDER BY date DESC 
                    LIMIT ?
                """, (limit,)) as cursor:
                    return await cursor.fetchall()
        except Exception as e:
            logger.error(f"Ошибка при получении отзывов: {e}")
            return []

    async def get_support_info(self) -> Optional[Dict]:
        """Получение информации о поддержке"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute('SELECT * FROM support_info ORDER BY id DESC LIMIT 1') as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка при получении информации о поддержке: {e}")
            return None

    async def update_support_info(self, message: str, bot_version: str, support_url: str) -> bool:
        """Обновление информации о поддержке"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute('''
                    INSERT INTO support_info (message, bot_version, support_url)
                    VALUES (?, ?, ?)
                ''', (message, bot_version, support_url))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при обновлении информации о поддержке: {e}")
            return False

    async def add_notify_setting(self, name: str, interval: int, type: str) -> bool:
        """Добавление новой настройки уведомлений"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE notify_settings 
                    SET is_enable = 0 
                    WHERE type = ? AND is_enable = 1
                """, (type,))
                
                await db.execute("""
                    INSERT INTO notify_settings (name, interval, type)
                    VALUES (?, ?, ?)
                """, (name, interval, type))
                
                await db.commit()
                logger.info(f"Добавлена новая настройка уведомлений: {name} (тип: {type})")
                return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении настройки уведомлений: {e}")
            return False

    async def get_notify_setting(self, setting_id: int) -> Optional[Dict]:
        """Получение настройки уведомлений по ID"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    'SELECT * FROM notify_settings WHERE id = ?',
                    (setting_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка при получении настройки уведомлений: {e}")
            return None

    async def get_all_notify_settings(self) -> List[Dict]:
        """Получение всех настроек уведомлений"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute('SELECT * FROM notify_settings') as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении всех настроек уведомлений: {e}")
            return []

    async def get_active_notify_settings(self) -> List[Dict]:
        """Получение активных настроек уведомлений"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    'SELECT * FROM notify_settings WHERE is_enable = 1'
                ) as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении активных настроек уведомлений: {e}")
            return []

    async def update_notify_setting(self, setting_id: int, name: str = None, 
                                  interval: int = None, type: str = None, 
                                  is_enable: bool = None) -> bool:
        """Обновление настройки уведомлений"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    'SELECT * FROM notify_settings WHERE id = ?',
                    (setting_id,)
                ) as cursor:
                    current = await cursor.fetchone()
                    if not current:
                        return False

                update_values = []
                update_fields = []
                if name is not None:
                    update_fields.append("name = ?")
                    update_values.append(name)
                if interval is not None:
                    update_fields.append("interval = ?")
                    update_values.append(interval)
                if type is not None:
                    update_fields.append("type = ?")
                    update_values.append(type)
                if is_enable is not None:
                    update_fields.append("is_enable = ?")
                    update_values.append(is_enable)

                if update_fields:
                    update_values.append(setting_id)
                    query = f"""
                        UPDATE notify_settings 
                        SET {', '.join(update_fields)}
                        WHERE id = ?
                    """
                    await db.execute(query, update_values)
                    await db.commit()
                    logger.info(f"Обновлена настройка уведомлений ID: {setting_id}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Ошибка при обновлении настройки уведомлений: {e}")
            return False

    async def delete_notify_setting(self, setting_id: int) -> bool:
        """Удаление настройки уведомлений"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'DELETE FROM notify_settings WHERE id = ?',
                    (setting_id,)
                )
                await db.commit()
                logger.info(f"Удалена настройка уведомлений ID: {setting_id}")
                return True
        except Exception as e:
            logger.error(f"Ошибка при удалении настройки уведомлений: {e}")
            return False

    async def enable_notify_setting(self, setting_id: int, enable: bool) -> bool:
        """Включение/выключение настройки уведомлений"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'UPDATE notify_settings SET is_enable = ? WHERE id = ?',
                    (enable, setting_id)
                )
                await db.commit()
                status = "включена" if enable else "выключена"
                logger.info(f"Настройка уведомлений ID: {setting_id} {status}")
                return True
        except Exception as e:
            logger.error(f"Ошибка при изменении статуса настройки уведомлений: {e}")
            return False

    async def update_notify_setting_by_name(self, name: str, is_enable: bool = None) -> bool:
        """Обновление настройки уведомлений по имени"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    'SELECT id FROM notify_settings WHERE name = ? AND is_enable = 1',
                    (name,)
                ) as cursor:
                    setting = await cursor.fetchone()
                    if not setting:
                        return False

                if is_enable is not None:
                    await db.execute(
                        'UPDATE notify_settings SET is_enable = ? WHERE name = ?',
                        (is_enable, name)
                    )
                    await db.commit()
                    status = "включена" if is_enable else "выключена"
                    logger.info(f"Настройка уведомлений '{name}' {status}")
                    return True
                return False
        except Exception as e:
            logger.error(f"Ошибка при обновлении настройки уведомлений по имени: {e}")
            return False

    async def get_expiring_subscriptions(self) -> List[Dict]:
        """Получение подписок, которые заканчиваются в течение 24 часов"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                
                now = datetime.now(timezone.utc)
                end_time = now + timedelta(hours=24)
                
                now_str = now.strftime('%Y-%m-%d %H:%M:%S.%f')
                end_time_str = end_time.strftime('%Y-%m-%d %H:%M:%S.%f')
                
                logger.debug(f"Проверка подписок между {now_str} и {end_time_str}")
                
                async with db.execute("""
                    SELECT * FROM user_subscription 
                    WHERE datetime(end_date) BETWEEN datetime(?) AND datetime(?)
                    AND is_active = 1
                """, (now_str, end_time_str)) as cursor:
                    rows = await cursor.fetchall()
                    subscriptions = [dict(row) for row in rows]
                    logger.debug(f"Найдено подписок: {len(subscriptions)}")
                    return subscriptions
        except Exception as e:
            logger.error(f"Ошибка при получении истекающих подписок: {e}")
            return []

    async def get_tariff(self, tariff_id: int) -> Optional[Dict]:
        """Получение информации о тарифе"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    'SELECT * FROM tariff WHERE id = ?',
                    (tariff_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка при получении тарифа: {e}")
            return None

    async def get_server(self, server_id: int) -> Optional[Dict]:
        """Получение информации о сервере"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    'SELECT * FROM server_settings WHERE id = ?',
                    (server_id,)
                ) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка при получении сервера: {e}")
            return None

    async def add_payment_code(self, pay_code: str, sum: float) -> bool:
        """Добавление нового кода оплаты"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO payments_code (pay_code, sum)
                    VALUES (?, ?)
                """, (pay_code, sum))
                await db.commit()
                logger.info(f"Добавлен новый код оплаты: {pay_code}")
                return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении кода оплаты: {e}")
            return False

    async def get_payment_code(self, pay_code: str) -> Optional[Dict]:
        """Получение информации о коде оплаты"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(
                    'SELECT * FROM payments_code WHERE pay_code = ? AND is_enable = 1',
                    (pay_code,)
                ) as cursor:
                    row = await cursor.fetchone()
                    return dict(row) if row else None
        except Exception as e:
            logger.error(f"Ошибка при получении кода оплаты: {e}")
            return None

    async def disable_payment_code(self, pay_code: str) -> bool:
        """Деактивация кода оплаты"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'UPDATE payments_code SET is_enable = 0 WHERE pay_code = ?',
                    (pay_code,)
                )
                await db.commit()
                logger.info(f"Код оплаты деактивирован: {pay_code}")
                return True
        except Exception as e:
            logger.error(f"Ошибка при деактивации кода оплаты: {e}")
            return False

    async def get_all_payment_codes(self) -> List[Dict]:
        """Получение списка всех кодов оплаты"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute('SELECT * FROM payments_code') as cursor:
                    rows = await cursor.fetchall()
                    return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении списка кодов оплаты: {e}")
            return []

    async def enable_payment_code(self, pay_code: str) -> bool:
        """Активация кода оплаты"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    'UPDATE payments_code SET is_enable = 1 WHERE pay_code = ?',
                    (pay_code,)
                )
                await db.commit()
                logger.info(f"Код оплаты активирован: {pay_code}")
                return True
        except Exception as e:
            logger.error(f"Ошибка при активации кода оплаты: {e}")
            return False

    async def get_active_codes_sum(self) -> float:
        """Получение суммы всех активных кодов оплаты"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    'SELECT SUM(sum) FROM payments_code WHERE is_enable = 1'
                ) as cursor:
                    result = await cursor.fetchone()
                    return float(result[0]) if result[0] is not None else 0.0
        except Exception as e:
            logger.error(f"Ошибка при получении суммы активных кодов: {e}")
            return 0.0

    async def get_used_codes_sum(self) -> float:
        """Получение суммы всех использованных кодов оплаты"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    'SELECT SUM(sum) FROM payments_code WHERE is_enable = 0'
                ) as cursor:
                    result = await cursor.fetchone()
                    return float(result[0]) if result[0] is not None else 0.0
        except Exception as e:
            logger.error(f"Ошибка при получении суммы использованных кодов: {e}")
            return 0.0

    async def is_yookassa_enabled(self) -> bool:
        """Проверка активности Юкассы"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    'SELECT is_enable FROM yookassa_settings WHERE is_enable = 1 LIMIT 1'
                ) as cursor:
                    result = await cursor.fetchone()
                    return bool(result[0]) if result else False
        except Exception as e:
            logger.error(f"Ошибка при проверке статуса Юкассы: {e}")
            return False

    async def is_crypto_enabled(self) -> bool:
        """Проверка активности Crypto Pay"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute(
                    'SELECT is_enable FROM crypto_settings WHERE is_enable = 1 LIMIT 1'
                ) as cursor:
                    result = await cursor.fetchone()
                    return bool(result[0]) if result else False
        except Exception as e:
            logger.error(f"Ошибка при проверке статуса Crypto Pay: {e}")
            return False        

    async def get_crypto_settings(self) -> Optional[Dict]:
        """
        Получение текущих настроек Crypto Pay
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    cursor = await conn.execute("""
                        SELECT api_token, is_enable, min_amount, supported_assets, webhook_url, webhook_secret
                        FROM crypto_settings
                        WHERE is_enable = 1
                        LIMIT 1
                    """)
                    settings = await cursor.fetchone()
                    return dict(settings) if settings else None
            except Exception as e:
                logger.error(f"Ошибка при получении настроек Crypto Pay: {e}")
                return None
        
        return await self.db_operation_with_retry(_operation)

    async def add_crypto_settings(self, api_token: str, min_amount: float, 
                                  supported_assets: str, webhook_url: Optional[str] = None, 
                                  webhook_secret: Optional[str] = None) -> bool:
        """
        Добавление новых настроек Crypto Pay (с деактивацией предыдущих)
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    
                    await conn.execute("""
                        UPDATE crypto_settings 
                        SET is_enable = 0 
                        WHERE is_enable = 1
                    """)
                    
                    await conn.execute("""
                        INSERT INTO crypto_settings 
                        (api_token, is_enable, min_amount, supported_assets, webhook_url, webhook_secret)
                        VALUES (?, 1, ?, ?, ?, ?)
                    """, (api_token, min_amount, supported_assets, webhook_url, webhook_secret))
                    
                    await conn.commit()
                    return True
            except Exception as e:
                logger.error(f"Ошибка при добавлении настроек Crypto Pay: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def toggle_crypto_settings(self, api_token: str, is_enable: bool) -> bool:
        """
        Включение или отключение настроек Crypto Pay
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    if is_enable:
                        await conn.execute("""
                            UPDATE crypto_settings 
                            SET is_enable = 0 
                            WHERE is_enable = 1
                        """)
                    
                    cursor = await conn.execute("""
                        UPDATE crypto_settings 
                        SET is_enable = ? 
                        WHERE api_token = ?
                        RETURNING *
                    """, (1 if is_enable else 0, api_token))
                    
                    updated = await cursor.fetchone()
                    if not updated:
                        logger.warning(f"Настройки Crypto Pay с API токеном {api_token} не найдены")
                        return False
                    
                    await conn.commit()
                    return True
            except Exception as e:
                logger.error(f"Ошибка при изменении статуса настроек Crypto Pay: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def execute_fetchone(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """Выполнение запроса с получением одной строки"""
        async def _execute_query():
            async with aiosqlite.connect(self.db_path, timeout=20.0) as db:
                db.row_factory = aiosqlite.Row
                async with db.execute(query, params) as cursor:
                    result = await cursor.fetchone()
                    return dict(result) if result else None
        
        try:
            return await self.db_operation_with_retry(_execute_query)
        except Exception as e:
            logger.error(f"Database error in execute_fetchone: {e}")
            return None

    async def create_raffle(self, name: str, description: str) -> bool:
        """Создание нового розыгрыша"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    INSERT INTO raffles (name, description, status)
                    VALUES (?, ?, 'active')
                """, (name, description))
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при создании розыгрыша: {e}")
            return False

    async def add_raffle_tickets(self, user_id: int, telegram_id: int, tickets_count: int, raffle_id: int) -> bool:
        """Добавление билетов пользователю"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                for _ in range(tickets_count):
                    ticket_number = f"T{random.randint(100000, 999999)}"
                    await conn.execute("""
                        INSERT INTO raffle_tickets 
                        (user_id, telegram_id, ticket_number, raffle_id)
                        VALUES (?, ?, ?, ?)
                    """, (user_id, telegram_id, ticket_number, raffle_id))
                await conn.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при добавлении билетов: {e}")
            return False

    async def get_user_tickets(self, telegram_id: int, raffle_id: int = None) -> List[Dict]:
        """Получение билетов пользователя"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                query = """
                    SELECT rt.*, r.name as raffle_name, u.username 
                    FROM raffle_tickets rt
                    JOIN raffles r ON rt.raffle_id = r.id
                    JOIN user u ON rt.telegram_id = u.telegram_id
                    WHERE rt.telegram_id = ?
                """
                params = [telegram_id]
                
                if raffle_id:
                    query += " AND rt.raffle_id = ?"
                    params.append(raffle_id)
                
                cursor = await conn.execute(query, params)
                tickets = await cursor.fetchall()
                return [dict(ticket) for ticket in tickets]
        except Exception as e:
            logger.error(f"Ошибка при получении билетов пользователя: {e}")
            return []

    async def get_active_raffles(self) -> List[Dict]:
        """Получение активных розыгрышей"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute("""
                    SELECT * FROM raffles 
                    WHERE status = 'active' 
                    AND (end_date IS NULL OR end_date > datetime('now'))
                """)
                raffles = await cursor.fetchall()
                return [dict(raffle) for raffle in raffles]
        except Exception as e:
            logger.error(f"Ошибка при получении активных розыгрышей: {e}")
            return []

    async def get_raffle_participants(self, raffle_id: int) -> List[Dict]:
        """Получение участников розыгрыша с их билетами"""
        try:
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute("""
                    SELECT 
                        u.telegram_id,
                        u.username,
                        COUNT(rt.id) as tickets_count,
                        (COUNT(rt.id) * 100.0 / (SELECT COUNT(*) FROM raffle_tickets WHERE raffle_id = ?)) as win_chance
                    FROM user u
                    JOIN raffle_tickets rt ON u.telegram_id = rt.telegram_id
                    WHERE rt.raffle_id = ?
                    GROUP BY u.telegram_id, u.username
                    ORDER BY tickets_count DESC
                """, (raffle_id, raffle_id))
                participants = await cursor.fetchall()
                return [dict(participant) for participant in participants]
        except Exception as e:
            logger.error(f"Ошибка при получении участников розыгрыша: {e}")
            return []

    async def deactivate_raffle(self) -> bool:
        """Деактивация текущего активного розыгрыша"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("""
                    UPDATE raffles 
                    SET status = 'inactive', 
                        end_date = datetime('now')
                    WHERE status = 'active'
                """)
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при деактивации розыгрыша: {e}")
            return False

    async def delete_all_raffle_tickets(self) -> bool:
        """Удаление всех билетов розыгрыша"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                await db.execute("DELETE FROM raffle_tickets")
                await db.commit()
                return True
        except Exception as e:
            logger.error(f"Ошибка при удалении билетов: {e}")
            return False

    async def get_tickets_report(self) -> List[Dict]:
        """Получение данных о билетах для отчета"""
        try:
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute("""
                    SELECT 
                        u.username,
                        u.telegram_id,
                        GROUP_CONCAT(rt.ticket_number) as tickets,
                        COUNT(rt.id) as tickets_count
                    FROM user u
                    JOIN raffle_tickets rt ON u.telegram_id = rt.telegram_id
                    GROUP BY u.telegram_id, u.username
                    ORDER BY tickets_count DESC
                """)
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            logger.error(f"Ошибка при получении данных для отчета: {e}")
            return []

    async def get_user_balance(self, user_id: int) -> float:
        """Получение баланса пользователя с повторными попытками"""
        async def _operation():
            async with aiosqlite.connect(self.db_path) as conn:
                async with conn.execute(
                    "SELECT balance FROM user_balance WHERE user_id = ?",
                    (user_id,)
                ) as cursor:
                    result = await cursor.fetchone()
                    return float(result[0]) if result else 0.0
        
        return await self.db_operation_with_retry(_operation)

    async def update_balance(self, user_id: int, amount: float, type: str, description: str = None, payment_id: str = None) -> bool:
        """Обновление баланса пользователя с повторными попытками"""
        async def _operation():
            async with aiosqlite.connect(self.db_path) as conn:
                try:
                    async with conn.execute(
                        "SELECT balance FROM user_balance WHERE user_id = ?",
                        (user_id,)
                    ) as cursor:
                        current_balance = await cursor.fetchone()

                    if current_balance:
                        await conn.execute(
                            """
                            UPDATE user_balance 
                            SET balance = balance + ?, last_update = CURRENT_TIMESTAMP 
                            WHERE user_id = ?
                            """,
                            (amount, user_id)
                        )
                    else:
                        await conn.execute(
                            "INSERT INTO user_balance (user_id, balance) VALUES (?, ?)",
                            (user_id, amount)
                        )

                    await conn.execute(
                        """
                        INSERT INTO balance_transactions 
                        (user_id, amount, type, description, payment_id) 
                        VALUES (?, ?, ?, ?, ?)
                        """,
                        (user_id, amount, type, description, payment_id)
                    )

                    await conn.commit()
                    return True
                except Exception as e:
                    logger.error(f"Ошибка при обновлении баланса: {e}")
                    return False

        return await self.db_operation_with_retry(_operation)

    async def get_balance_transactions(self, user_id: int, limit: int = None) -> List[Dict]:
        """Получение транзакций пользователя с повторными попытками"""
        async def _operation():
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                query = """
                    SELECT * FROM balance_transactions 
                    WHERE user_id = ? 
                    ORDER BY created_at DESC
                """
                if limit:
                    query += f" LIMIT {limit}"
                
                async with conn.execute(query, (user_id,)) as cursor:
                    return [dict(row) for row in await cursor.fetchall()]

        return await self.db_operation_with_retry(_operation)

    async def check_balance_sufficient(self, user_id: int, required_amount: float) -> bool:
        """Проверка достаточности средств с повторными попытками"""
        async def _operation():
            current_balance = await self.get_user_balance(user_id)
            return current_balance >= required_amount

        return await self.db_operation_with_retry(_operation)


    async def get_referral_conditions(self, only_active: bool = False) -> List[Dict]:
        """
        Получение настроек реферальной программы
        
        :param only_active: Возвращать только активные условия
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    
                    query = """
                        SELECT id, name, description, invitations, reward_sum, is_enable, created_at
                        FROM referral_condition
                    """
                    
                    if only_active:
                        query += " WHERE is_enable = 1"
                        
                    query += " ORDER BY invitations ASC"
                    
                    cursor = await conn.execute(query)
                    conditions = await cursor.fetchall()
                    
                    return [dict(row) for row in conditions]
            except Exception as e:
                logger.error(f"Ошибка при получении настроек реферальной программы: {e}")
                return []
        
        return await self.db_operation_with_retry(_operation)

    async def add_referral_condition(self, name: str, description: str, invitations: int, 
                                    reward_sum: float) -> int:
        """
        Добавление нового условия реферальной программы
        
        :return: ID нового условия или 0 при ошибке
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    cursor = await conn.execute("""
                        INSERT INTO referral_condition 
                        (name, description, invitations, reward_sum, is_enable)
                        VALUES (?, ?, ?, ?, 1)
                        RETURNING id
                    """, (name, description, invitations, reward_sum))
                    
                    result = await cursor.fetchone()
                    new_id = result[0] if result else 0
                    
                    await conn.commit()
                    return new_id
            except Exception as e:
                logger.error(f"Ошибка при добавлении условия реферальной программы: {e}")
                return 0
        
        return await self.db_operation_with_retry(_operation)

    async def toggle_referral_condition(self, condition_id: int, is_enable: bool) -> bool:
        """
        Включение или отключение условия реферальной программы
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    cursor = await conn.execute("""
                        SELECT 1 FROM referral_condition WHERE id = ?
                    """, (condition_id,))
                    
                    exists = await cursor.fetchone()
                    if not exists:
                        logger.warning(f"Условие реферальной программы с ID {condition_id} не найдено")
                        return False
                    
                    await conn.execute("""
                        UPDATE referral_condition 
                        SET is_enable = ? 
                        WHERE id = ?
                    """, (1 if is_enable else 0, condition_id))
                    
                    await conn.commit()
                    return True
            except Exception as e:
                logger.error(f"Ошибка при изменении статуса условия реферальной программы: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def get_user_referral_progress(self, user_id: int) -> Dict:
        """Получение прогресса реферальной программы пользователя"""
        async def _operation():
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute("""
                    SELECT rp.*, u.referral_count 
                    FROM referral_progress rp
                    JOIN user u ON u.telegram_id = rp.user_id
                    WHERE rp.user_id = ?
                """, (user_id,))
                result = await cursor.fetchone()
                return dict(result) if result else None
        
        return await self.db_operation_with_retry(_operation)

    async def create_referral_progress(self, user_id: int) -> bool:
        """Создание записи прогресса реферальной программы"""
        async def _operation():
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    INSERT INTO referral_progress (user_id, total_invites)
                    VALUES (?, 0)
                """, (user_id,))
                await conn.commit()
                return True
        
        return await self.db_operation_with_retry(_operation)

    async def update_referral_progress(self, user_id: int, total_invites: int) -> bool:
        """Обновление прогресса реферальной программы"""
        async def _operation():
            async with aiosqlite.connect(self.db_path) as conn:
                await conn.execute("""
                    UPDATE referral_progress 
                    SET total_invites = ?, 
                        last_reward_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """, (total_invites, user_id))
                await conn.commit()
                return True
        
        return await self.db_operation_with_retry(_operation)

    async def check_referral_reward(self, user_id: int) -> Optional[float]:
        """Проверка и начисление реферальной награды"""
        async def _operation():
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                
                cursor = await conn.execute("""
                    SELECT total_invites 
                    FROM referral_progress 
                    WHERE user_id = ?
                """, (user_id,))
                progress = await cursor.fetchone()
                
                if not progress:
                    return None
                    
                cursor = await conn.execute("""
                    SELECT * FROM referral_condition 
                    WHERE is_enable = 1 
                    AND invitations <= ?
                    ORDER BY invitations DESC
                """, (progress['total_invites'],))
                conditions = await cursor.fetchall()
                
                for condition in conditions:
                    cursor = await conn.execute("""
                        SELECT id FROM referral_rewards_history 
                        WHERE user_id = ? AND condition_id = ?
                    """, (user_id, condition['id']))
                    
                    if not await cursor.fetchone():  
                        await self.update_balance(
                            user_id=user_id,
                            amount=condition['reward_sum'],
                            type='referral_reward',
                            description=f"Награда за приглашение {condition['invitations']} пользователей"
                        )
                        
                        await conn.execute("""
                            INSERT INTO referral_rewards_history 
                            (user_id, condition_id, reward_sum) 
                            VALUES (?, ?, ?)
                        """, (user_id, condition['id'], condition['reward_sum']))
                        
                        await conn.commit()
                        return condition['reward_sum']
                
                return None
        
        return await self.db_operation_with_retry(_operation)

    async def get_user_by_referral_code(self, referral_code: str) -> Dict:
        """Получение пользователя по реферальному коду"""
        async def _operation():
            async with aiosqlite.connect(self.db_path) as conn:
                conn.row_factory = aiosqlite.Row
                cursor = await conn.execute("""
                    SELECT * FROM user WHERE referral_code = ?
                """, (referral_code,))
                result = await cursor.fetchone()
                return dict(result) if result else None
        
        return await self.db_operation_with_retry(_operation)

    async def get_all_users(self) -> List[Dict]:
        """
        Получение списка всех пользователей
        """
        try:
            conn = await self.get_connection()
            cursor = await conn.cursor()
            await cursor.execute("SELECT * FROM user")
            users = await cursor.fetchall()
            
            columns = [col[0] for col in cursor.description]
            result = []
            for user in users:
                user_dict = dict(zip(columns, user))
                result.append(user_dict)
            
            await cursor.close()
            await conn.close()
            return result
        except Exception as e:
            logger.error(f"Ошибка при получении всех пользователей: {e}")
            return []

    async def add_server(self, name: str, url: str, port: str, secret_path: str, 
                        username: str, password: str, inbound_id: int, 
                        protocol: str, ip: str) -> bool:
        """
        Добавление нового сервера
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    await conn.execute("""
                        INSERT INTO server_settings 
                        (name, url, port, secret_path, username, password, inbound_id, protocol, ip, is_enable)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                    """, (name, url, port, secret_path, username, password, inbound_id, protocol, ip))
                    await conn.commit()
                    return True
            except Exception as e:
                logger.error(f"Ошибка при добавлении сервера: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def get_all_tariffs(self, include_server_name: bool = True) -> List[Dict]:
        """
        Получение списка всех тарифов с информацией о серверах
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    if include_server_name:
                        async with conn.execute("""
                            SELECT t.*, s.name as server_name 
                            FROM tariff t 
                            JOIN server_settings s ON t.server_id = s.id 
                            ORDER BY t.id
                        """) as cursor:
                            tariffs = await cursor.fetchall()
                    else:
                        async with conn.execute("""
                            SELECT * FROM tariff ORDER BY id
                        """) as cursor:
                            tariffs = await cursor.fetchall()
                    
                    result = []
                    for tariff in tariffs:
                        result.append(dict(tariff))
                    return result
            except Exception as e:
                logger.error(f"Ошибка при получении всех тарифов: {e}")
                return []
        
        return await self.db_operation_with_retry(_operation)

    async def add_tariff(self, name: str, description: str, price: float, left_day: int, 
                        server_id: int) -> bool:
        """
        Добавление нового тарифа
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    await conn.execute("""
                        INSERT INTO tariff 
                        (name, description, price, left_day, server_id, is_enable)
                        VALUES (?, ?, ?, ?, ?, 1)
                    """, (name, description, price, left_day, server_id))
                    await conn.commit()
                    return True
            except Exception as e:
                logger.error(f"Ошибка при добавлении тарифа: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def disable_tariff(self, tariff_id: int) -> bool:
        """
        Отключение тарифного плана (установка is_enable = 0)
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    cursor = await conn.execute(
                        "SELECT id FROM tariff WHERE id = ? AND is_enable = 1",
                        (tariff_id,)
                    )
                    tariff = await cursor.fetchone()
                    
                    if not tariff:
                        return False
                        
                    await conn.execute(
                        "UPDATE tariff SET is_enable = 0 WHERE id = ?",
                        (tariff_id,)
                    )
                    await conn.commit()
                    return True
            except Exception as e:
                logger.error(f"Ошибка при отключении тарифа {tariff_id}: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def disable_tariff_by_name(self, tariff_name: str) -> bool:
        """
        Отключение тарифного плана по имени (установка is_enable = 0)
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    cursor = await conn.execute(
                        "SELECT name FROM tariff WHERE name = ? AND is_enable = 1",
                        (tariff_name,)
                    )
                    tariff = await cursor.fetchone()
                    
                    if not tariff:
                        return False
                        
                    await conn.execute(
                        "UPDATE tariff SET is_enable = 0 WHERE name = ?",
                        (tariff_name,)
                    )
                    await conn.commit()
                    return True
            except Exception as e:
                logger.error(f"Ошибка при отключении тарифа с именем {tariff_name}: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def get_user_subscriptions(self, telegram_id: int) -> List[Dict]:
        """
        Получение всех подписок пользователя по Telegram ID
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    
                    cursor = await conn.execute("""
                        SELECT 
                            us.id, us.user_id, us.tariff_id, us.server_id, 
                            us.start_date, us.end_date, us.vless, us.is_active, us.payment_id,
                            t.name as tariff_name, t.description as tariff_description, 
                            t.price as tariff_price, t.left_day as tariff_left_day,
                            s.name as server_name, s.url as server_url, s.protocol as server_protocol
                        FROM user_subscription us
                        JOIN tariff t ON us.tariff_id = t.id
                        JOIN server_settings s ON us.server_id = s.id
                        WHERE us.user_id = ?
                        ORDER BY us.end_date DESC
                    """, (telegram_id,))
                    
                    subscriptions = await cursor.fetchall()
                    
                    result = []
                    for sub in subscriptions:
                        result.append(dict(sub))
                    return result
                
            except Exception as e:
                logger.error(f"Ошибка при получении подписок пользователя {telegram_id}: {e}")
                return []
        
        return await self.db_operation_with_retry(_operation)

    async def get_api_key(self, key: str) -> Optional[Dict]:
        """
        Получение информации об API ключе по его значению
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    cursor = await conn.execute("""
                        SELECT * FROM api_key WHERE key = ? AND is_enable = 1
                    """, (key,))
                    result = await cursor.fetchone()
                    return dict(result) if result else None
            except Exception as e:
                logger.error(f"Ошибка при получении API ключа: {e}")
                return None
        
        return await self.db_operation_with_retry(_operation)

    async def add_api_key(self, name: str, key: str) -> bool:
        """
        Добавление нового API ключа
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    await conn.execute("""
                        INSERT INTO api_key (name, key, is_enable)
                        VALUES (?, ?, 1)
                    """, (name, key))
                    await conn.commit()
                    return True
            except Exception as e:
                logger.error(f"Ошибка при добавлении API ключа: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def disable_api_key(self, key_id: int) -> bool:
        """
        Отключение API ключа
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    await conn.execute("""
                        UPDATE api_key SET is_enable = 0 WHERE id = ?
                    """, (key_id,))
                    await conn.commit()
                    return True
            except Exception as e:
                logger.error(f"Ошибка при отключении API ключа {key_id}: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def get_all_api_keys(self) -> List[Dict]:
        """
        Получение списка всех API ключей
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    cursor = await conn.execute("""
                        SELECT * FROM api_key ORDER BY date DESC
                    """)
                    keys = await cursor.fetchall()
                    
                    result = []
                    for key in keys:
                        result.append(dict(key))
                    return result
            except Exception as e:
                logger.error(f"Ошибка при получении всех API ключей: {e}")
                return []
        
        return await self.db_operation_with_retry(_operation)

    async def enable_user(self, telegram_id: int) -> bool:
        """
        Разблокировка пользователя (установка is_enable = 1)
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    cursor = await conn.execute(
                        "SELECT telegram_id FROM user WHERE telegram_id = ? AND is_enable = 0",
                        (telegram_id,)
                    )
                    user = await cursor.fetchone()
                    
                    if not user:
                        return False
                        
                    await conn.execute(
                        "UPDATE user SET is_enable = 1 WHERE telegram_id = ?",
                        (telegram_id,)
                    )
                    await conn.commit()
                    return True
            except Exception as e:
                logger.error(f"Ошибка при разблокировке пользователя {telegram_id}: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)
    
    async def disable_user(self, telegram_id: int) -> bool:
        """
        Блокировка пользователя (установка is_enable = 0)
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    cursor = await conn.execute(
                        "SELECT telegram_id FROM user WHERE telegram_id = ? AND is_enable = 1",
                        (telegram_id,)
                    )
                    user = await cursor.fetchone()
                    
                    if not user:
                        return False
                        
                    await conn.execute(
                        "UPDATE user SET is_enable = 0 WHERE telegram_id = ?",
                        (telegram_id,)
                    )
                    await conn.commit()
                    return True
            except Exception as e:
                logger.error(f"Ошибка при блокировке пользователя {telegram_id}: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def get_user_payments(self, telegram_id: int, only_sum: bool = False) -> Union[List[Dict], Dict]:
        """
        Получение платежей пользователя по Telegram ID
        
        Args:
            telegram_id: Telegram ID пользователя
            only_sum: Если True, возвращает только общую сумму платежей
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    
                    if only_sum:
                        cursor = await conn.execute("""
                            SELECT SUM(price) as total 
                            FROM payments 
                            WHERE user_id = ?
                        """, (telegram_id,))
                        result = await cursor.fetchone()
                        total = result['total'] if result and result['total'] is not None else 0
                        return {"telegram_id": telegram_id, "total_payments": total}
                    else:
                        cursor = await conn.execute("""
                            SELECT p.*, t.name as tariff_name, t.description as tariff_description
                            FROM payments p
                            JOIN tariff t ON p.tariff_id = t.id
                            WHERE p.user_id = ?
                            ORDER BY p.date DESC
                        """, (telegram_id,))
                        payments = await cursor.fetchall()
                        
                        result = []
                        for payment in payments:
                            result.append(dict(payment))
                        return result
                
            except Exception as e:
                logger.error(f"Ошибка при получении платежей пользователя {telegram_id}: {e}")
                if only_sum:
                    return {"telegram_id": telegram_id, "total_payments": 0}
                else:
                    return []
        
        return await self.db_operation_with_retry(_operation)

    async def delete_server(self, server_id: int) -> Dict:
        """
        Удаление сервера и отключение связанных тарифов
        
        Args:
            server_id: ID сервера
            
        Returns:
            Dict с информацией о результате операции:
            {
                "success": bool,
                "server_name": str,
                "disabled_tariffs_count": int
            }
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    cursor = await conn.execute(
                        "SELECT name FROM server_settings WHERE id = ?",
                        (server_id,)
                    )
                    server = await cursor.fetchone()
                    if not server:
                        return {
                            "success": False,
                            "server_name": None,
                            "disabled_tariffs_count": 0
                        }
                    
                    server_name = server[0]
                    
                    await conn.execute(
                        "UPDATE tariff SET is_enable = 0 WHERE server_id = ?",
                        (server_id,)
                    )
                    
                    cursor = await conn.execute(
                        "SELECT COUNT(*) FROM tariff WHERE server_id = ?",
                        (server_id,)
                    )
                    disabled_tariffs_count = (await cursor.fetchone())[0]
                    
                    await conn.execute(
                        "DELETE FROM server_settings WHERE id = ?",
                        (server_id,)
                    )
                    await conn.commit()
                    
                    return {
                        "success": True,
                        "server_name": server_name,
                        "disabled_tariffs_count": disabled_tariffs_count
                    }
                    
            except Exception as e:
                logger.error(f"Ошибка при удалении сервера {server_id}: {e}")
                return {
                    "success": False,
                    "server_name": None,
                    "disabled_tariffs_count": 0
                }
        
        return await self.db_operation_with_retry(_operation)

    async def get_trial_settings(self, trial_id: Optional[int] = None) -> Union[List[Dict], Optional[Dict]]:
        """
        Получение настроек пробных тарифов.
        Если trial_id не указан, возвращает все активные пробные тарифы.
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    
                    if trial_id is not None:
                        cursor = await conn.execute("""
                            SELECT t.*, s.name as server_name
                            FROM trial_settings t
                            JOIN server_settings s ON t.server_id = s.id
                            WHERE t.id = ?
                        """, (trial_id,))
                        result = await cursor.fetchone()
                        return dict(result) if result else None
                    else:
                        cursor = await conn.execute("""
                            SELECT t.*, s.name as server_name
                            FROM trial_settings t
                            JOIN server_settings s ON t.server_id = s.id
                            WHERE t.is_enable = 1
                        """)
                        results = await cursor.fetchall()
                        return [dict(row) for row in results]
                        
            except Exception as e:
                logger.error(f"Ошибка при получении пробных тарифов: {e}")
                return [] if trial_id is None else None
        
        return await self.db_operation_with_retry(_operation)

    async def add_trial_settings(self, name: str, left_day: int, server_id: int) -> bool:
        """
        Добавление нового пробного тарифного плана
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    await conn.execute("""
                        INSERT INTO trial_settings (id, name, left_day, server_id, is_enable)
                        VALUES ((SELECT COALESCE(MAX(id), 100) + 1 FROM trial_settings), ?, ?, ?, 1)
                    """, (name, left_day, server_id))
                    await conn.commit()
                    return True
            except Exception as e:
                logger.error(f"Ошибка при добавлении пробного тарифа: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def update_trial_settings(self, trial_id: int, 
                                  name: Optional[str] = None,
                                  left_day: Optional[int] = None,
                                  server_id: Optional[int] = None) -> bool:
        """
        Обновление настроек пробного тарифного плана
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    update_fields = []
                    params = []
                    
                    if name is not None:
                        update_fields.append("name = ?")
                        params.append(name)
                    if left_day is not None:
                        update_fields.append("left_day = ?")
                        params.append(left_day)
                    if server_id is not None:
                        update_fields.append("server_id = ?")
                        params.append(server_id)
                    
                    if not update_fields:
                        return False
                    
                    params.append(trial_id)
                    
                    query = f"""
                        UPDATE trial_settings 
                        SET {', '.join(update_fields)}
                        WHERE id = ?
                    """
                    await conn.execute(query, params)
                    await conn.commit()
                    return True
                    
            except Exception as e:
                logger.error(f"Ошибка при обновлении пробного тарифа {trial_id}: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def disable_trial_settings(self, trial_id: int) -> bool:
        """
        Отключение пробного тарифного плана
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    await conn.execute("""
                        UPDATE trial_settings 
                        SET is_enable = 0 
                        WHERE id = ?
                    """, (trial_id,))
                    await conn.commit()
                    return True
            except Exception as e:
                logger.error(f"Ошибка при отключении пробного тарифа {trial_id}: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def get_all_promocodes(self) -> List[Dict]:
        """
        Получение списка всех активных промокодов
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    cursor = await conn.execute("""
                        SELECT promocod, activation_limit, activation_total, percentage
                        FROM promocodes
                        WHERE is_enable = 1
                        ORDER BY date DESC
                    """)
                    promocodes = await cursor.fetchall()
                    return [dict(row) for row in promocodes]
            except Exception as e:
                logger.error(f"Ошибка при получении списка промокодов: {e}")
                return []
        
        return await self.db_operation_with_retry(_operation)

    async def add_promocode(self, activation_limit: int, percentage: float) -> Optional[str]:
        """
        Добавление нового промокода
        
        Args:
            activation_limit: Лимит активаций
            percentage: Процент скидки
            
        Returns:
            str: Сгенерированный промокод в случае успеха, None в случае ошибки
        """
        async def _operation():
            try:
                while True:
                    promocode = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(12))
                    async with aiosqlite.connect(self.db_path) as conn:
                        cursor = await conn.execute(
                            "SELECT promocod FROM promocodes WHERE promocod = ?",
                            (promocode,)
                        )
                        if not await cursor.fetchone():
                            break
                
                async with aiosqlite.connect(self.db_path) as conn:
                    await conn.execute("""
                        INSERT INTO promocodes (promocod, activation_limit, percentage, is_enable)
                        VALUES (?, ?, ?, 1)
                    """, (promocode, activation_limit, percentage))
                    await conn.commit()
                    return promocode
            except Exception as e:
                logger.error(f"Ошибка при добавлении промокода: {e}")
                return None
        
        return await self.db_operation_with_retry(_operation)

    async def disable_promocode(self, promocode: str) -> bool:
        """
        Деактивация промокода
        
        Args:
            promocode: Промокод для деактивации
            
        Returns:
            bool: True если промокод успешно деактивирован, False в случае ошибки
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    await conn.execute(
                        "UPDATE promocodes SET is_enable = 0 WHERE promocod = ?",
                        (promocode,)
                    )
                    await conn.commit()
                    return True
            except Exception as e:
                logger.error(f"Ошибка при деактивации промокода {promocode}: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def get_total_users_count(self) -> int:
        """
        Получение общего количества пользователей
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    cursor = await conn.execute("SELECT COUNT(*) as total_users FROM user")
                    result = await cursor.fetchone()
                    return result[0] if result else 0
            except Exception as e:
                logger.error(f"Ошибка при получении количества пользователей: {e}")
                return 0
        
        return await self.db_operation_with_retry(_operation)

    async def get_total_subscriptions_count(self) -> int:
        """
        Получение общего количества подписок
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    cursor = await conn.execute("SELECT COUNT(*) as total_subscriptions FROM user_subscription")
                    result = await cursor.fetchone()
                    return result[0] if result else 0
            except Exception as e:
                logger.error(f"Ошибка при получении количества подписок: {e}")
                return 0
        
        return await self.db_operation_with_retry(_operation)

    async def get_most_popular_tariff(self) -> Optional[Dict]:
        """
        Получение самого популярного тарифа
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    cursor = await conn.execute("""
                        SELECT t.name, COUNT(*) as count
                        FROM user_subscription us
                        JOIN tariff t ON us.tariff_id = t.id
                        GROUP BY us.tariff_id
                        ORDER BY count DESC
                        LIMIT 1
                    """)
                    result = await cursor.fetchone()
                    return dict(result) if result else None
            except Exception as e:
                logger.error(f"Ошибка при получении популярного тарифа: {e}")
                return None
        
        return await self.db_operation_with_retry(_operation)

    async def get_last_payment(self) -> Optional[Dict]:
        """
        Получение информации о последнем платеже
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    cursor = await conn.execute("""
                        SELECT p.price, p.date as payment_date, u.username, u.telegram_id
                        FROM payments p
                        JOIN user u ON p.user_id = u.telegram_id
                        ORDER BY p.date DESC
                        LIMIT 1
                    """)
                    result = await cursor.fetchone()
                    return dict(result) if result else None
            except Exception as e:
                logger.error(f"Ошибка при получении последнего платежа: {e}")
                return None
        
        return await self.db_operation_with_retry(_operation)

    async def get_total_payments_amount(self) -> float:
        """
        Получение общей суммы платежей
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    cursor = await conn.execute('SELECT SUM(price) as total FROM payments')
                    result = await cursor.fetchone()
                    return result[0] if result and result[0] else 0
            except Exception as e:
                logger.error(f"Ошибка при получении общей суммы платежей: {e}")
                return 0
        
        return await self.db_operation_with_retry(_operation)

    async def get_top_buyer(self) -> Optional[Dict]:
        """
        Получение информации о самом активном покупателе
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    cursor = await conn.execute("""
                        SELECT u.username, u.telegram_id, COUNT(*) as purchase_count
                        FROM payments p
                        JOIN user u ON p.user_id = u.telegram_id
                        GROUP BY p.user_id
                        ORDER BY purchase_count DESC
                        LIMIT 1
                    """)
                    result = await cursor.fetchone()
                    return dict(result) if result else None
            except Exception as e:
                logger.error(f"Ошибка при получении топ покупателя: {e}")
                return None
        
        return await self.db_operation_with_retry(_operation)

    async def get_all_users_for_notify(self) -> List[Dict]:
        """
        Получение списка всех пользователей для рассылки
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    cursor = await conn.execute("""
                        SELECT telegram_id, username
                        FROM user
                        WHERE is_enable = 1
                    """)
                    users = await cursor.fetchall()
                    return [dict(row) for row in users]
            except Exception as e:
                logger.error(f"Ошибка при получении списка пользователей для рассылки: {e}")
                return []
        
        return await self.db_operation_with_retry(_operation)

    async def get_user_for_notify(self, telegram_id: int) -> Optional[Dict]:
        """
        Получение информации о пользователе для отправки уведомления
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    cursor = await conn.execute("""
                        SELECT telegram_id, username
                        FROM user
                        WHERE telegram_id = ? AND is_enable = 1
                    """, (telegram_id,))
                    result = await cursor.fetchone()
                    return dict(result) if result else None
            except Exception as e:
                logger.error(f"Ошибка при получении пользователя {telegram_id}: {e}")
                return None
        
        return await self.db_operation_with_retry(_operation)

    async def get_all_promo_tariffs(self) -> List[Dict]:
        """
        Получение списка всех промо-тарифов
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    cursor = await conn.execute("""
                        SELECT tp.*, s.name as server_name
                        FROM tariff_promo tp
                        LEFT JOIN server_settings s ON tp.server_id = s.id
                        WHERE tp.is_enable = 1
                        ORDER BY tp.id DESC
                    """)
                    tariffs = await cursor.fetchall()
                    return [dict(row) for row in tariffs]
            except Exception as e:
                logger.error(f"Ошибка при получении списка промо-тарифов: {e}")
                return []
        
        return await self.db_operation_with_retry(_operation)

    async def disable_promo_tariff(self, promo_id: int) -> bool:
        """
        Деактивация промо-тарифа
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    await conn.execute("""
                        UPDATE tariff_promo 
                        SET is_enable = 0 
                        WHERE id = ?
                    """, (promo_id,))
                    await conn.commit()
                    return True
            except Exception as e:
                logger.error(f"Ошибка при деактивации промо-тарифа {promo_id}: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def send_promo_tariff(self, promo_id: int, user_id: int) -> bool:
        """
        Отправка промо-тарифа пользователю
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    
                    cursor = await conn.execute("""
                        SELECT *
                        FROM tariff_promo
                        WHERE id = ? AND is_enable = 1
                    """, (promo_id,))
                    promo = await cursor.fetchone()
                    
                    if not promo:
                        logger.warning(f"Промо-тариф {promo_id} не найден или не активен")
                        return False
                    
                    promo_dict = dict(promo)
                    
                    await conn.execute("""
                        INSERT INTO user_subscription 
                        (user_id, tariff_id, server_id, start_date, end_date, is_active)
                        VALUES (?, ?, ?, datetime('now'), datetime('now', '+' || ? || ' days'), 1)
                    """, (user_id, promo_id, promo_dict['server_id'], promo_dict['left_day']))
                    
                    await conn.commit()
                    return True
                
            except Exception as e:
                logger.error(f"Ошибка при отправке промо-тарифа {promo_id} пользователю {user_id}: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def get_user_balance_info(self) -> Dict:
        """
        Получение информации о балансах пользователей
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    cursor = await conn.execute(
                        "SELECT COUNT(DISTINCT user_id) as users_count FROM user_balance"
                    )
                    users_count = await cursor.fetchone()
                    users_count = users_count[0] if users_count else 0
                    
                    cursor = await conn.execute(
                        "SELECT SUM(balance) as total_balance FROM user_balance"
                    )
                    total_balance = await cursor.fetchone()
                    total_balance = total_balance[0] if total_balance else 0
                    
                    return {
                        "users_count": users_count,
                        "total_balance": float(total_balance or 0)
                    }
            except Exception as e:
                logger.error(f"Ошибка при получении информации о балансах пользователей: {e}")
                return {
                    "users_count": 0,
                    "total_balance": 0.0
                }
        
        return await self.db_operation_with_retry(_operation)

    async def get_all_bot_messages(self) -> List[Dict]:
        """
        Получение всех сообщений бота
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    cursor = await conn.execute("""
                        SELECT command, text, image_path, is_enable
                        FROM bot_message
                        ORDER BY command
                    """)
                    messages = await cursor.fetchall()
                    return [dict(row) for row in messages]
            except Exception as e:
                logger.error(f"Ошибка при получении сообщений бота: {e}")
                return []
        
        return await self.db_operation_with_retry(_operation)

    async def update_bot_message(self, command: str, text: str, image_path: Optional[str] = None) -> bool:
        """
        Обновление сообщения бота
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    cursor = await conn.execute("""
                        SELECT 1 FROM bot_message WHERE command = ?
                    """, (command,))
                    exists = await cursor.fetchone()
                    
                    if not exists:
                        logger.warning(f"Сообщение с командой {command} не найдено")
                        return False
                    
                    if image_path is None:
                        await conn.execute("""
                            UPDATE bot_message 
                            SET text = ? 
                            WHERE command = ?
                        """, (text, command))
                    else:
                        await conn.execute("""
                            UPDATE bot_message 
                            SET text = ?, image_path = ? 
                            WHERE command = ?
                        """, (text, image_path, command))
                    
                    await conn.commit()
                    return True
            except Exception as e:
                logger.error(f"Ошибка при обновлении сообщения бота {command}: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def toggle_bot_message(self, command: str, is_enable: bool) -> bool:
        """
        Включение или отключение сообщения бота
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    cursor = await conn.execute("""
                        SELECT 1 FROM bot_message WHERE command = ?
                    """, (command,))
                    exists = await cursor.fetchone()
                    
                    if not exists:
                        logger.warning(f"Сообщение с командой {command} не найдено")
                        return False
                    
                    await conn.execute("""
                        UPDATE bot_message 
                        SET is_enable = ? 
                        WHERE command = ?
                    """, (1 if is_enable else 0, command))
                    
                    await conn.commit()
                    return True
            except Exception as e:
                logger.error(f"Ошибка при изменении статуса сообщения бота {command}: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def get_referral_rewards_history(self, user_id: Optional[int] = None, 
                                           limit: int = 100, offset: int = 0) -> List[Dict]:
        """
        Получение истории реферальных вознаграждений
        
        :param user_id: ID пользователя (опционально, для фильтрации)
        :param limit: Лимит записей
        :param offset: Смещение для пагинации
        :return: Список записей истории вознаграждений
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    
                    query = """
                        SELECT 
                            h.id,
                            h.user_id,
                            u.username,
                            h.condition_id,
                            rc.name as condition_name,
                            h.reward_sum,
                            h.created_at
                        FROM referral_rewards_history h
                        JOIN user u ON h.user_id = u.telegram_id
                        LEFT JOIN referral_condition rc ON h.condition_id = rc.id
                    """
                    
                    params = []
                    if user_id is not None:
                        query += " WHERE h.user_id = ?"
                        params.append(user_id)
                    
                    query += " ORDER BY h.created_at DESC LIMIT ? OFFSET ?"
                    params.extend([limit, offset])
                    
                    cursor = await conn.execute(query, params)
                    history = await cursor.fetchall()
                    
                    return [dict(row) for row in history]
            except Exception as e:
                logger.error(f"Ошибка при получении истории реферальных вознаграждений: {e}")
                return []
        
        return await self.db_operation_with_retry(_operation)

    async def add_user_subscription(self, user_id: int, tariff_id: int, server_id: int, 
                                  end_date: str, vless: str, payment_id: str = None) -> int:
        """
        Добавление подписки пользователя
        
        :return: ID новой подписки или 0 при ошибке
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    cursor = await conn.execute("""
                        INSERT INTO user_subscription 
                        (user_id, tariff_id, server_id, end_date, vless, payment_id, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, 1)
                        RETURNING id
                    """, (user_id, tariff_id, server_id, end_date, vless, payment_id))
                    
                    result = await cursor.fetchone()
                    new_id = result[0] if result else 0
                    
                    await conn.commit()
                    return new_id
            except Exception as e:
                logger.error(f"Ошибка при добавлении подписки пользователя: {e}")
                return 0
        
        return await self.db_operation_with_retry(_operation)

    async def add_user(self, telegram_id: int, username: str = "", 
                      trial_period: bool = False, referral_code: str = None, 
                      referred_by: str = None) -> int:
        """
        Добавление нового пользователя в базу данных
        
        :param telegram_id: Telegram ID пользователя
        :param username: Имя пользователя
        :param trial_period: Статус триального периода
        :param referral_code: Реферальный код пользователя (если есть)
        :param referred_by: Реферальный код пригласившего пользователя (если есть)
        :return: ID нового пользователя или 0 при ошибке
        """
        async def _operation():
            try:
                if not referral_code:
                    ref_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                else:
                    ref_code = referral_code
                    
                async with aiosqlite.connect(self.db_path) as conn:
                    cursor = await conn.execute("""
                        INSERT INTO user 
                        (telegram_id, username, trial_period, is_enable, referral_code, referral_count, referred_by)
                        VALUES (?, ?, ?, 1, ?, 0, ?)
                        RETURNING id
                    """, (telegram_id, username, 1 if trial_period else 0, ref_code, referred_by))
                    
                    result = await cursor.fetchone()
                    new_id = result[0] if result else 0
                    
                    await conn.commit()
                    logger.info(f"Добавлен новый пользователь: telegram_id={telegram_id}, id={new_id}")
                    return new_id
            except Exception as e:
                logger.error(f"Ошибка при добавлении пользователя {telegram_id}: {e}")
                return 0
        
        return await self.db_operation_with_retry(_operation)

    async def get_total_crypto_payments(self) -> float:
        """
        Получение общей суммы всех криптоплатежей
        
        :return: Общая сумма платежей
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    cursor = await conn.execute("""
                        SELECT SUM(amount) as total
                        FROM crypto_payments
                        WHERE status = 'paid'
                    """)
                    result = await cursor.fetchone()
                    return float(result[0]) if result[0] else 0.0
            except Exception as e:
                logger.error(f"Ошибка при получении общей суммы криптоплатежей: {e}")
                return 0.0
        
        return await self.db_operation_with_retry(_operation)

    async def get_user_crypto_payments(self, user_id: int) -> Dict:
        """
        Получение истории криптоплатежей пользователя и информации о пользователе
        
        :param user_id: Telegram ID пользователя
        :return: Словарь с информацией о пользователе и его платежах
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    
                    cursor = await conn.execute("""
                        SELECT username, telegram_id
                        FROM user
                        WHERE telegram_id = ?
                    """, (user_id,))
                    
                    user = await cursor.fetchone()
                    if not user:
                        return None
                    
                    cursor = await conn.execute("""
                        SELECT 
                            SUM(CASE WHEN status = 'paid' THEN amount ELSE 0 END) as total_paid,
                            COUNT(*) as total_transactions
                        FROM crypto_payments
                        WHERE user_id = ?
                    """, (user_id,))
                    
                    payment_stats = await cursor.fetchone()
                    
                    cursor = await conn.execute("""
                        SELECT 
                            cp.id,
                            cp.invoice_id,
                            cp.amount,
                            cp.asset,
                            cp.status,
                            cp.created_at,
                            cp.updated_at,
                            t.name as tariff_name,
                            t.left_day as tariff_days
                        FROM crypto_payments cp
                        LEFT JOIN tariff t ON cp.tariff_id = t.id
                        WHERE cp.user_id = ?
                        ORDER BY cp.created_at DESC
                    """, (user_id,))
                    
                    payments = await cursor.fetchall()
                    
                    return {
                        "user_info": dict(user),
                        "payment_stats": {
                            "total_paid_amount": float(payment_stats["total_paid"]) if payment_stats["total_paid"] else 0.0,
                            "total_transactions": payment_stats["total_transactions"]
                        },
                        "payments": [dict(row) for row in payments]
                    }
                    
            except Exception as e:
                logger.error(f"Ошибка при получении криптоплатежей пользователя {user_id}: {e}")
                return None
        
        return await self.db_operation_with_retry(_operation)

    async def get_all_payments(self) -> List[Dict]:
        """
        Получение списка всех платежей с информацией о пользователе и тарифе
        
        :return: Список словарей с информацией о платежах
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    cursor = await conn.execute("""
                        SELECT 
                            p.id,
                            p.user_id AS telegram_id,
                            u.username,
                            t.name AS tariff_name,
                            p.price,
                            p.date
                        FROM payments p
                        LEFT JOIN user u ON p.user_id = u.telegram_id
                        LEFT JOIN tariff t ON p.tariff_id = t.id
                        ORDER BY p.date DESC
                    """)
                    
                    payments = await cursor.fetchall()
                    return [dict(row) for row in payments]
            except Exception as e:
                logger.error(f"Ошибка при получении списка платежей: {e}")
                return []
        
        return await self.db_operation_with_retry(_operation)

    async def update_tariff(self, tariff_id: int, name: str = None, description: str = None, 
                           price: float = None, left_day: int = None, 
                           server_id: int = None, is_enable: bool = None) -> bool:
        """
        Обновление тарифного плана
        
        :param tariff_id: ID тарифа
        :param name: Новое название тарифа (опционально)
        :param description: Новое описание тарифа (опционально)
        :param price: Новая цена тарифа (опционально)
        :param left_day: Новое количество дней действия тарифа (опционально)
        :param server_id: Новый ID сервера (опционально)
        :param is_enable: Новый статус активности тарифа (опционально)
        :return: True если тариф успешно обновлен, иначе False
        """
        async def _operation():
            try:
                updates = []
                params = []
                
                if name is not None:
                    updates.append("name = ?")
                    params.append(name)
                
                if description is not None:
                    updates.append("description = ?")
                    params.append(description)
                
                if price is not None:
                    updates.append("price = ?")
                    params.append(price)
                
                if left_day is not None:
                    updates.append("left_day = ?")
                    params.append(left_day)
                
                if server_id is not None:
                    updates.append("server_id = ?")
                    params.append(server_id)
                
                if is_enable is not None:
                    updates.append("is_enable = ?")
                    params.append(1 if is_enable else 0)
                
                if not updates:
                    return True
                
                sql = f"UPDATE tariff SET {', '.join(updates)} WHERE id = ?"
                params.append(tariff_id)
                
                async with aiosqlite.connect(self.db_path) as conn:
                    cursor = await conn.execute("SELECT id FROM tariff WHERE id = ?", (tariff_id,))
                    tariff = await cursor.fetchone()
                    
                    if not tariff:
                        return False
                    
                    await conn.execute(sql, params)
                    await conn.commit()
                    
                    return True
            except Exception as e:
                logger.error(f"Ошибка при обновлении тарифа {tariff_id}: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def get_bot_settings_api(self) -> Dict:
        """
        Получение настроек бота
        
        :return: Словарь с настройками бота или None, если настройки не найдены
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    cursor = await conn.execute("""
                        SELECT 
                            bot_token,
                            admin_id,
                            chat_id,
                            chanel_id,
                            is_enable,
                            reg_notify,
                            pay_notify
                        FROM bot_settings
                        WHERE is_enable = 1
                        LIMIT 1
                    """)
                    
                    settings = await cursor.fetchone()
                    return dict(settings) if settings else None
            except Exception as e:
                logger.error(f"Ошибка при получении настроек бота: {e}")
                return None
        
        return await self.db_operation_with_retry(_operation)

    async def create_bot_settings(self, bot_token: str, admin_id: str, 
                                 chat_id: str = None, chanel_id: str = None,
                                 is_enable: bool = True, reg_notify: int = 0, 
                                 pay_notify: int = 0) -> bool:
        """
        Создание настроек бота
        
        :param bot_token: Токен бота
        :param admin_id: ID администратора
        :param chat_id: ID чата (опционально)
        :param chanel_id: ID канала (опционально)
        :param is_enable: Статус активности (по умолчанию True)
        :param reg_notify: Флаг уведомлений о регистрации (по умолчанию 0)
        :param pay_notify: Флаг уведомлений о платежах (по умолчанию 0)
        :return: True если настройки успешно созданы, иначе False
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    await conn.execute("""
                        UPDATE bot_settings SET is_enable = 0
                    """)
                    
                    await conn.execute("""
                        INSERT INTO bot_settings 
                        (bot_token, admin_id, chat_id, chanel_id, is_enable, reg_notify, pay_notify)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        bot_token, 
                        admin_id, 
                        chat_id, 
                        chanel_id, 
                        1 if is_enable else 0, 
                        reg_notify, 
                        pay_notify
                    ))
                    
                    await conn.commit()
                    return True
            except Exception as e:
                logger.error(f"Ошибка при создании настроек бота: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def update_bot_settings(self, bot_token: str = None, admin_id: str = None, 
                                 chat_id: str = None, chanel_id: str = None,
                                 is_enable: bool = None, reg_notify: int = None, 
                                 pay_notify: int = None) -> bool:
        """
        Обновление настроек бота
        
        :param bot_token: Новый токен бота (опционально)
        :param admin_id: Новый ID администратора (опционально)
        :param chat_id: Новый ID чата (опционально)
        :param chanel_id: Новый ID канала (опционально)
        :param is_enable: Новый статус активности (опционально)
        :param reg_notify: Новый флаг уведомлений о регистрации (опционально)
        :param pay_notify: Новый флаг уведомлений о платежах (опционально)
        :return: True если настройки успешно обновлены, иначе False
        """
        async def _operation():
            try:
                current_settings = await self.get_bot_settings_api()  
                if not current_settings:
                    return False
                
                updates = []
                params = []
                
                if bot_token is not None:
                    updates.append("bot_token = ?")
                    params.append(bot_token)
                
                if admin_id is not None:
                    updates.append("admin_id = ?")
                    params.append(admin_id)
                    
                if chat_id is not None:
                    updates.append("chat_id = ?")
                    params.append(chat_id)
                    
                if chanel_id is not None:
                    updates.append("chanel_id = ?")
                    params.append(chanel_id)
                    
                if is_enable is not None:
                    updates.append("is_enable = ?")
                    params.append(1 if is_enable else 0)
                    
                if reg_notify is not None:
                    updates.append("reg_notify = ?")
                    params.append(reg_notify)
                    
                if pay_notify is not None:
                    updates.append("pay_notify = ?")
                    params.append(pay_notify)
                
                if not updates:
                    return True
                
                sql = f"UPDATE bot_settings SET {', '.join(updates)} WHERE is_enable = 1"
                
                async with aiosqlite.connect(self.db_path) as conn:
                    await conn.execute(sql, params)
                    await conn.commit()
                    return True
                    
            except Exception as e:
                logger.error(f"Ошибка при обновлении настроек бота: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def delete_referral_condition(self, condition_id: int) -> bool:
        """
        Удаление условия реферальной программы из базы данных
        
        :param condition_id: ID условия реферальной программы
        :return: True если условие успешно удалено, иначе False
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    cursor = await conn.execute(
                        "SELECT id FROM referral_condition WHERE id = ?",
                        (condition_id,)
                    )
                    condition = await cursor.fetchone()
                    
                    if not condition:
                        logger.warning(f"Условие реферальной программы с ID {condition_id} не найдено")
                        return False
                    
                    await conn.execute(
                        "DELETE FROM referral_condition WHERE id = ?",
                        (condition_id,)
                    )
                    
                    await conn.commit()
                    logger.info(f"Условие реферальной программы с ID {condition_id} успешно удалено")
                    return True
                    
            except Exception as e:
                logger.error(f"Ошибка при удалении условия реферальной программы с ID {condition_id}: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def update_server(self, server_id: int, name: str = None, ip: str = None, 
                           port: str = None, inbound_id: int = None, 
                           is_enable: bool = None, inbound_id_promo: int = None) -> bool:
        """
        Обновление настроек сервера
        
        :param server_id: ID сервера
        :param name: Новое название сервера (опционально)
        :param ip: Новый IP-адрес сервера (опционально)
        :param port: Новый порт сервера (опционально)
        :param inbound_id: Новый ID входящего соединения (опционально)
        :param is_enable: Новый статус активности сервера (опционально)
        :param inbound_id_promo: Новый ID входящего соединения для промо (опционально)
        :return: True если сервер успешно обновлен, иначе False
        """
        async def _operation():
            try:
                updates = []
                params = []
                
                if name is not None:
                    updates.append("name = ?")
                    params.append(name)
                
                if ip is not None:
                    updates.append("ip = ?")
                    params.append(ip)
                
                if port is not None:
                    updates.append("port = ?")
                    params.append(port)
                
                if inbound_id is not None:
                    updates.append("inbound_id = ?")
                    params.append(inbound_id)
                
                if is_enable is not None:
                    updates.append("is_enable = ?")
                    params.append(1 if is_enable else 0)
                    
                if inbound_id_promo is not None:
                    updates.append("inbound_id_promo = ?")
                    params.append(inbound_id_promo)
                
                if not updates:
                    return True
                
                sql = f"UPDATE server_settings SET {', '.join(updates)} WHERE id = ?"
                params.append(server_id)
                
                async with aiosqlite.connect(self.db_path) as conn:
                    cursor = await conn.execute("SELECT id FROM server_settings WHERE id = ?", (server_id,))
                    server = await cursor.fetchone()
                    
                    if not server:
                        return False
                    
                    await conn.execute(sql, params)
                    await conn.commit()
                    
                    return True
            except Exception as e:
                logger.error(f"Ошибка при обновлении сервера {server_id}: {e}")
                return False
        
        return await self.db_operation_with_retry(_operation)

    async def get_servers_subscriptions_count(self) -> List[Dict]:
        """
        Получает статистику по количеству подписок на каждом сервере.
        
        Returns:
            List[Dict]: Список словарей с информацией о серверах и количестве подписок
        """
        async def _operation():
            query = """
                SELECT 
                    s.id as server_id,
                    s.name as server_name,
                    COUNT(us.id) as subscriptions_count
                FROM server_settings s
                LEFT JOIN user_subscription us ON s.id = us.server_id
                WHERE us.is_active = 1
                GROUP BY s.id, s.name
                ORDER BY s.id
            """
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(query)
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
        return await self.db_operation_with_retry(_operation)

    async def get_servers_total_earnings(self) -> List[Dict]:
        """
        Получает статистику по общей сумме заработка на каждом сервере.
        
        Returns:
            List[Dict]: Список словарей с информацией о серверах и общей суммой заработка
        """
        async def _operation():
            query = """
                SELECT 
                    ss.name AS server_name,
                    COUNT(us.id) AS total_subscriptions,
                    SUM(COALESCE(t.price, 0)) AS total_earnings
                FROM user_subscription us
                LEFT JOIN tariff t ON us.tariff_id = t.id
                JOIN server_settings ss ON us.server_id = ss.id
                GROUP BY ss.id, ss.name
                ORDER BY total_earnings DESC;

            """
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(query)
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
        return await self.db_operation_with_retry(_operation)

    async def get_subscriptions_due_in_next_10_days(self) -> List[Dict]:
        """
        Получает подписки, которые заканчиваются в течение ближайших 10 дней.
        
        Returns:
            List[Dict]: Список словарей с информацией о подписках
        """
        async def _operation():
            query = """
                SELECT 
                    us.user_id AS telegram_id,
                    ss.name AS server_name,
                    IFNULL(t.name, 'Тариф удален') AS tariff_name,
                    us.end_date,
                    DATE(us.end_date) AS end_date_formatted
                FROM user_subscription us
                LEFT JOIN server_settings ss ON us.server_id = ss.id
                LEFT JOIN tariff t ON us.tariff_id = t.id
                WHERE us.is_active = 1
                AND us.end_date BETWEEN DATETIME('now') AND DATETIME('now', '+10 days')
                ORDER BY us.end_date ASC;

            """
            async with aiosqlite.connect(self.db_path) as db:
                db.row_factory = aiosqlite.Row
                cursor = await db.execute(query)
                rows = await cursor.fetchall()
                return [dict(row) for row in rows]
                
        return await self.db_operation_with_retry(_operation)

    async def get_all_crypto_payments(self) -> List[Dict]:
        """
        Получение списка всех платежей с информацией о пользователе и тарифе
        
        :return: Список словарей с информацией о платежах
        """
        async def _operation():
            try:
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    cursor = await conn.execute("""
                SELECT 
                    u.username AS username,
                    u.telegram_id AS telegram_id,
                    t.name AS tariff_name,
                    cp.amount AS amount,
                    cp.created_at AS created_at
                FROM crypto_payments cp
                LEFT JOIN user u ON cp.user_id = u.telegram_id
                LEFT JOIN tariff t ON cp.tariff_id = t.id
                WHERE cp.status = 'paid'
                ORDER BY cp.created_at DESC;
                    """)
                    
                    payments = await cursor.fetchall()
                    return [dict(row) for row in payments]
            except Exception as e:
                logger.error(f"Ошибка при получении списка платежей: {e}")
                return []
        
        return await self.db_operation_with_retry(_operation)

    async def get_all_balance_transactions(self, skip: int = 0, limit: int = 100, type_filter: Optional[str] = None) -> Dict:
        """
        Получение всех транзакций баланса с пагинацией и опциональной фильтрацией по типу
        
        :param skip: Сколько записей пропустить (для пагинации)
        :param limit: Сколько записей вернуть (для пагинации)
        :param type_filter: Фильтр по типу транзакции (опционально)
        :return: Словарь со списком транзакций и общим количеством записей
        """
        async def _operation():
            try:
                query = """
                    SELECT 
                        bt.id,
                        u.username,
                        u.telegram_id,
                        bt.amount,
                        bt.type,
                        bt.description,
                        bt.payment_id,
                        bt.created_at
                    FROM balance_transactions bt
                    LEFT JOIN user u ON bt.user_id = u.telegram_id
                """
                
                params = []
                if type_filter:
                    query += " WHERE bt.type = ? "
                    params.append(type_filter)
                
                query += " ORDER BY bt.created_at DESC "
                
                count_query = "SELECT COUNT(*) as total FROM balance_transactions bt "
                if type_filter:
                    count_query += " WHERE bt.type = ? "
                
                query += " LIMIT ? OFFSET ? "
                params.extend([limit, skip])
                
                async with aiosqlite.connect(self.db_path) as conn:
                    conn.row_factory = aiosqlite.Row
                    
                    cursor = await conn.execute(count_query, params[:-2] if type_filter else [])
                    row = await cursor.fetchone()
                    total_count = row['total'] if row else 0
                    
                    cursor = await conn.execute(query, params)
                    rows = await cursor.fetchall()
                    transactions = [dict(row) for row in rows]
                    
                    return {
                        "transactions": transactions,
                        "total_count": total_count,
                        "limit": limit,
                        "offset": skip
                    }
            except Exception as e:
                logger.error(f"Ошибка при получении транзакций баланса: {e}")
                return None
                
        return await self.db_operation_with_retry(_operation)

db = Database()

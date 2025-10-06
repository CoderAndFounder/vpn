import aiosqlite
import asyncio
import string
import random
import os
from datetime import datetime

DB_PATH = "instance/database.db"

def generate_api_key(length=24):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

async def create_api_key_table():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute('''
        CREATE TABLE IF NOT EXISTS api_key (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            key TEXT UNIQUE NOT NULL,
            is_enable INTEGER DEFAULT 1,
            date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        await db.commit()
        print("Таблица api_key успешно создана!")

async def generate_and_save_key(name):
    api_key = generate_api_key()
    
    async with aiosqlite.connect(DB_PATH) as db:
        try:
            await db.execute(
                "INSERT INTO api_key (name, key) VALUES (?, ?)",
                (name, api_key)
            )
            await db.commit()
            print(f"Сгенерирован новый ключ: {api_key}")
        except aiosqlite.IntegrityError:
            print("Ошибка: Ключ с таким значением уже существует. Попробуйте снова.")

async def main():
    print("Менеджер API ключей")
    print("1. Добавить таблицу api_key")
    print("2. Сгенерировать ключ API")
    
    choice = input("Выберите действие (1/2): ")
    
    if choice == "1":
        await create_api_key_table()
    elif choice == "2":
        try:
            async with aiosqlite.connect(DB_PATH) as db:
                cursor = await db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='api_key'")
                table_exists = await cursor.fetchone()
                
            if not table_exists:
                print("Таблица api_key не существует. Сначала создайте таблицу (опция 1).")
                return
                
            name = input("Введите имя ключа: ")
            await generate_and_save_key(name)
        except Exception as e:
            print(f"Произошла ошибка: {e}")
    else:
        print("Неверный выбор. Пожалуйста, выберите 1 или 2.")

if __name__ == "__main__":
    asyncio.run(main())
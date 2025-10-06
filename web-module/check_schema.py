import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

# Получаем абсолютный путь к базе данных
db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database.db')
print(f"Путь к базе данных: {db_path}")

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Получаем схему таблицы promocodes
cursor.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='promocodes';")
result = cursor.fetchone()
if result:
    print("\nСхема таблицы promocodes:")
    print(result[0])
else:
    print("\nТаблица promocodes не найдена!")

conn.close()

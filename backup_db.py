import os
import sqlite3
from datetime import datetime

source_db = 'instance/database.db'
backup_dir = 'instance/backup'

if not os.path.exists(backup_dir):
    os.makedirs(backup_dir)

timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
backup_db = os.path.join(backup_dir, f'database-{timestamp}.db')

try:
    conn = sqlite3.connect(source_db)
    cursor = conn.cursor()
    cursor.execute(f"VACUUM INTO '{backup_db}'")
    conn.close()
    print(f'Резервная копия создана (VACUUM): {backup_db}')
except sqlite3.OperationalError:
    print("VACUUM INTO не поддерживается, используем метод с копированием файлов.")


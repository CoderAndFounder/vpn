import sqlite3
import os

def create_db_if_not_exists():
    if not os.path.exists('instance'):
        os.makedirs('instance')
    
    conn = sqlite3.connect('instance/database.db')
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bot_settings (
        bot_token TEXT NOT NULL,
        admin_id TEXT NOT NULL,
        chat_id TEXT,
        chanel_id TEXT,
        is_enable BOOLEAN NOT NULL DEFAULT 1,
        reg_notify INTEGER DEFAULT 0,
        pay_notify INTEGER DEFAULT 0
    )
    ''')
    conn.commit()
    conn.close()

def main():
    create_db_if_not_exists()
    
    bot_token = input('Введите токен бота: ')
    admin_id = input('Введите chat id администратора: ')
    
    conn = sqlite3.connect('instance/database.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT COUNT(*) FROM bot_settings')
    count = cursor.fetchone()[0]
    
    if count > 0:
        cursor.execute('''
        UPDATE bot_settings 
        SET bot_token = ?, admin_id = ?, reg_notify = 1, pay_notify = 1
        ''', (bot_token, admin_id))
    else:
        cursor.execute('''
        INSERT INTO bot_settings (bot_token, admin_id, reg_notify, pay_notify)
        VALUES (?, ?, 1, 1)
        ''', (bot_token, admin_id))
    
    conn.commit()
    conn.close()
    
    print('Настройки бота успешно сохранены в базе данных!')

if __name__ == '__main__':
    main() 
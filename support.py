import os
import asyncio
import aiosqlite
from datetime import datetime
import random
import string

DB_PATH = "instance/database.db"

async def connect_db():
    """Установка соединения с базой данных"""
    if not os.path.exists(DB_PATH):
        print(f"Ошибка: База данных {DB_PATH} не найдена.")
        return None
    
    try:
        conn = await aiosqlite.connect(DB_PATH)
        conn.row_factory = aiosqlite.Row
        return conn
    except Exception as e:
        print(f"Ошибка подключения к базе данных: {e}")
        return None

async def display_main_menu():
    """Отображение главного меню"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=============================")
    print("          ГЛАВНОЕ МЕНЮ          ")
    print("=============================")
    print()
    print("1. Пользователи  ")
    print("2. Настройки бота  ")
    print("3. Настройки Юкасса  ")
    print("4. Настройки Crypto Bot  ")
    print("5. Уведомления  ")
    print()
    print("0. Выйти  ")
    print()
    choice = input("Выберите пункт меню: ")
    return choice

async def display_users_menu():
    """Отображение меню работы с пользователями"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=============================")
    print("Меню работы с пользователями")
    print("=============================")
    print()
    print("1. Общая статистика")
    print("2. Найти пользователя")
    print("3. Добавить пользователя")
    print("4. Удалить пользователя")
    print("5. Редактировать пользователя")
    print()
    print("0. Назад")
    print()
    choice = input("Выберите пункт меню: ")
    return choice

async def show_user_stats(conn):
    """Отображение общей статистики пользователей"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=============================")
    print("      Общая статистика      ")
    print("=============================")
    
    try:
        query = """
        SELECT 
            COUNT(*) AS "Всего пользователей",
            COUNT(CASE WHEN referral_code IS NOT NULL AND referral_code <> '' THEN 1 END) AS "С реферальным кодом",
            COUNT(CASE WHEN referral_code IS NULL OR referral_code = '' THEN 1 END) AS "Без реферального кода"
        FROM user;
        """
        
        async with conn.execute(query) as cursor:
            row = await cursor.fetchone()
            
            if row:
                columns = row.keys()
                values = [str(row[col]) for col in columns]
                
                col_widths = [max(len(col), len(val)) for col, val in zip(columns, values)]
                
                header = "|"
                for col, width in zip(columns, col_widths):
                    header += f" {col.center(width)} |"
                print(header)
                
                separator = "+"
                for width in col_widths:
                    separator += "-" * (width + 2) + "+"
                print(separator)
                
                data_row = "|"
                for val, width in zip(values, col_widths):
                    data_row += f" {val.center(width)} |"
                print(data_row)
    except Exception as e:
        print(f"Ошибка при получении статистики: {e}")
    
    print("\n1. Вернуться в меню пользователей")
    print("2. Заполнить реф. коды")
    print("3. Вернуться в главное меню")
    print("0. Выйти из программы")
    
    while True:
        choice = input("\nВыберите действие: ")
        if choice == "1":
            return  
        elif choice == "2":
            try:
                update_query = """
                UPDATE user
                SET referral_code =
                    substr('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', abs(random()) % 36 + 1, 1) ||
                    substr('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', abs(random()) % 36 + 1, 1) ||
                    substr('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', abs(random()) % 36 + 1, 1) ||
                    substr('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', abs(random()) % 36 + 1, 1) ||
                    substr('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', abs(random()) % 36 + 1, 1) ||
                    substr('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', abs(random()) % 36 + 1, 1) ||
                    substr('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', abs(random()) % 36 + 1, 1) ||
                    substr('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', abs(random()) % 36 + 1, 1)
                WHERE referral_code IS NULL OR referral_code = '';
                """
                
                async with conn.execute("SELECT COUNT(*) as count FROM user WHERE referral_code IS NULL OR referral_code = ''") as cursor:
                    before_count = (await cursor.fetchone())['count']
                
                await conn.execute(update_query)
                await conn.commit()
                
                async with conn.execute("SELECT COUNT(*) as count FROM user WHERE referral_code IS NULL OR referral_code = ''") as cursor:
                    after_count = (await cursor.fetchone())['count']
                
                updated_rows = before_count - after_count
                print(f"\nУспешно обновлено записей: {updated_rows}")
                input("\nНажмите Enter для продолжения...")
                return  
                
            except Exception as e:
                print(f"\nОшибка при заполнении реферальных кодов: {e}")
                input("\nНажмите Enter для продолжения...")
                return  
        elif choice == "3":
            return "main"  
        elif choice == "0":
            print("Выход из программы...")
            exit(0)
        else:
            print("Неверный выбор. Попробуйте снова.")

async def find_user(conn):
    """Поиск пользователя по ID или username"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=============================")
    print("       Поиск пользователя      ")
    print("=============================")
    
    search_term = input("Введите имя пользователя если оно известно или telegram id: ")
    
    try:
        is_telegram_id = search_term.isdigit()
        
        if is_telegram_id:
            query = "SELECT * FROM user WHERE telegram_id = ?"
            params = (int(search_term),)
        else:
            query = "SELECT * FROM user WHERE username LIKE ?"
            params = (f"%{search_term}%",)
        
        async with conn.execute(query, params) as cursor:
            user = await cursor.fetchone()
            
        if user:
            os.system('cls' if os.name == 'nt' else 'clear')
            print("=============================")
            print("     Результаты поиска     ")
            print("=============================")
            
            print("\nПользователь:", user['username'] if 'username' in user.keys() and user['username'] else "Не указан")
            print("Telegram ID:", user['telegram_id'])
            
            balance_query = "SELECT * FROM user_balance WHERE user_id = ?"
            async with conn.execute(balance_query, (user['telegram_id'],)) as cursor:
                balance_row = await cursor.fetchone()
                
                if balance_row:
                    balance_field = None
                    for key in balance_row.keys():
                        if key in ['balance', 'value', 'total', 'sum', 'money']:
                            balance_field = key
                            break
                    
                    if balance_field:
                        balance = balance_row[balance_field]
                    else:
                        for key in balance_row.keys():
                            if isinstance(balance_row[key], (int, float)) and key != 'user_id' and key != 'id':
                                balance = balance_row[key]
                                break
                        else:
                            balance = str(dict(balance_row))
                else:
                    balance = 0
                    
                print(f"Баланс: {balance}")
            
            subscriptions_query = """
            SELECT us.*, t.name as tariff_name, s.name as server_name
            FROM user_subscription us
            LEFT JOIN tariff t ON us.tariff_id = t.id
            LEFT JOIN server_settings s ON us.server_id = s.id
            WHERE us.user_id = ? AND us.is_active = 1
            """
            
            print("\nАктивные подписки:")
            
            async with conn.execute(subscriptions_query, (user['telegram_id'],)) as cursor:
                subscriptions = await cursor.fetchall()
                
                if subscriptions:
                    for idx, sub in enumerate(subscriptions, 1):
                        end_date = sub['end_date'] if 'end_date' in sub.keys() else "Бессрочно"
                        tariff_name = sub['tariff_name'] if 'tariff_name' in sub.keys() and sub['tariff_name'] else "Неизвестный тариф"
                        server_name = sub['server_name'] if 'server_name' in sub.keys() and sub['server_name'] else "Неизвестный сервер"
                        vless = sub['vless'] if 'vless' in sub.keys() and sub['vless'] else "Нет данных"
                        
                        print(f"{idx}. Тариф: {tariff_name}")
                        print(f"   Сервер: {server_name}")
                        print(f"   Действует до: {end_date}")
                        print(f"   VLESS: {vless}")
                        print()
                else:
                    print("Нет активных подписок")
        else:
            print("\nПользователь не найден.")
            
        print("\n1. Вернуться в меню пользователей")
        print("2. Вернуться в главное меню")
        print("0. Выйти из программы")
        
        while True:
            choice = input("\nВыберите пункт меню: ")
            if choice == "1":
                return  
            elif choice == "2":
                return "main"  
            elif choice == "0":
                print("Выход из программы...")
                exit(0)
            else:
                print("Неверный выбор. Попробуйте снова.")
                
    except Exception as e:
        print(f"Ошибка при поиске пользователя: {e}")
        print("\nНажмите Enter для возврата в меню...")
        input()

async def add_user(conn):
    """Добавление нового пользователя"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=============================")
    print("  Добавление пользователя  ")
    print("=============================")
    
    username = input("Введите имя пользователя: ")
    
    while True:
        telegram_id_input = input("Введите Telegram ID: ")
        if telegram_id_input.isdigit():
            telegram_id = int(telegram_id_input)
            break
        else:
            print("Ошибка: Telegram ID должен быть числом. Попробуйте снова.")
    
    try:
        async with conn.execute("SELECT telegram_id FROM user WHERE telegram_id = ?", (telegram_id,)) as cursor:
            existing_user = await cursor.fetchone()
            
        if existing_user:
            print(f"\nПользователь с Telegram ID {telegram_id} уже существует!")
        else:
            def generate_ref_code():
                chars = string.ascii_uppercase + string.digits
                return ''.join(random.choice(chars) for _ in range(8))
            
            while True:
                referral_code = generate_ref_code()
                async with conn.execute("SELECT referral_code FROM user WHERE referral_code = ?", (referral_code,)) as cursor:
                    if not await cursor.fetchone():
                        break
            
            query = """
            INSERT INTO user (username, telegram_id, is_enable, referral_code)
            VALUES (?, ?, 1, ?)
            """
            await conn.execute(query, (username, telegram_id, referral_code))
            await conn.commit()
            
            os.system('cls' if os.name == 'nt' else 'clear')
            print("=============================")
            print("  Добавление пользователя  ")
            print("=============================")
            print("\nПользователь успешно добавлен!")
            print(f"\nИмя пользователя: {username}")
            print(f"Telegram ID: {telegram_id}")
            print(f"Реферальный код: {referral_code}")
            print("\nДобавить баланс пользователю можно из меню редактирования пользователя")
    except Exception as e:
        print(f"\nОшибка при добавлении пользователя: {e}")
    
    print("\n1. Вернуться в меню пользователей")
    print("2. Вернуться в главное меню")
    print("0. Выйти из программы")
    
    while True:
        choice = input("\nВыберите действие: ")
        if choice == "1":
            return  
        elif choice == "2":
            return "main"  
        elif choice == "0":
            print("Выход из программы...")
            exit(0)
        else:
            print("Неверный выбор. Попробуйте снова.")

async def delete_user(conn):
    """Удаление пользователя"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=============================")
    print("     Удаление пользователя     ")
    print("=============================")
    
    search_term = input("Введите имя пользователя или Telegram ID: ")
    
    try:
        is_telegram_id = search_term.isdigit()
        
        if is_telegram_id:
            query = "SELECT * FROM user WHERE telegram_id = ?"
            params = (int(search_term),)
        else:
            query = "SELECT * FROM user WHERE username LIKE ?"
            params = (f"%{search_term}%",)
            
        async with conn.execute(query, params) as cursor:
            user = await cursor.fetchone()
            
        if not user:
            print("\nПользователь не найден.")
        else:
            print("\nНайден пользователь для удаления:")
            print(f"Имя пользователя: {user['username'] if user['username'] else 'Не указано'}")
            print(f"Telegram ID: {user['telegram_id']}")
            print(f"Реферальный код: {user['referral_code'] if user['referral_code'] else 'Отсутствует'}")
            
            subscriptions_query = "SELECT COUNT(*) as count FROM user_subscription WHERE user_id = ?"
            async with conn.execute(subscriptions_query, (user['telegram_id'],)) as cursor:
                result = await cursor.fetchone()
                subs_count = result['count'] if result else 0
                
            print(f"Активных подписок: {subs_count}")
            
            confirm = input(f"\nВы уверены, что хотите удалить пользователя и все его подписки? (да/нет): ")
            
            if confirm.lower() in ["да", "yes"]:
                if subs_count > 0:
                    delete_subs_query = "DELETE FROM user_subscription WHERE user_id = ?"
                    await conn.execute(delete_subs_query, (user['telegram_id'],))
                    print(f"Удалено подписок: {subs_count}")
                
                delete_user_query = "DELETE FROM user WHERE telegram_id = ?"
                await conn.execute(delete_user_query, (user['telegram_id'],))
                
                await conn.commit()
                
                print("\nПользователь и все его подписки успешно удалены!")
            else:
                print("\nУдаление отменено.")
        
        print("\n1. Вернуться в меню пользователей")
        print("2. Вернуться в главное меню")
        print("0. Выйти из программы")
        
        while True:
            choice = input("\nВыберите действие: ")
            if choice == "1":
                return  
            elif choice == "2":
                return "main"  
            elif choice == "0":
                print("Выход из программы...")
                exit(0)
            else:
                print("Неверный выбор. Попробуйте снова.")
                
    except Exception as e:
        print(f"Ошибка при удалении пользователя: {e}")
        print("\nНажмите Enter для продолжения...")
        input()
        return

async def edit_user(conn):
    """Редактирование пользователя"""
    os.system('cls' if os.name == 'nt' else 'clear')
    print("=============================")
    print("   Редактирование пользователя   ")
    print("=============================")
    
    search_term = input("Введите имя пользователя или Telegram ID: ")
    
    try:
        is_telegram_id = search_term.isdigit()
        
        if is_telegram_id:
            query = "SELECT * FROM user WHERE telegram_id = ?"
            params = (int(search_term),)
        else:
            query = "SELECT * FROM user WHERE username LIKE ?"
            params = (f"%{search_term}%",)
            
        async with conn.execute(query, params) as cursor:
            user = await cursor.fetchone()
            
        if not user:
            print("\nПользователь не найден.")
        else:
            while True:
                os.system('cls' if os.name == 'nt' else 'clear')
                print("================================")
                print("   Редактирование пользователя   ")
                print("================================")
                
                print(f"\nИмя пользователя: {user['username'] if user['username'] else 'Не указано'}")
                print(f"Telegram ID: {user['telegram_id']}")
                print(f"Реферальный код: {user['referral_code'] if user['referral_code'] else 'Отсутствует'}")
                print(f"Статус: {'Активен' if user['is_enable'] else 'Заблокирован'}")
                
                balance_query = "SELECT balance FROM user_balance WHERE user_id = ?"
                async with conn.execute(balance_query, (user['telegram_id'],)) as cursor:
                    balance_row = await cursor.fetchone()
                    balance = balance_row['balance'] if balance_row else 0
                    print(f"Баланс: {balance}")
                
                subscriptions_query = "SELECT COUNT(*) as count FROM user_subscription WHERE user_id = ? AND is_active = 1"
                async with conn.execute(subscriptions_query, (user['telegram_id'],)) as cursor:
                    result = await cursor.fetchone()
                    subs_count = result['count'] if result else 0
                    print(f"Активных подписок: {subs_count}")
                
                print("\nДействия:")
                
                if user['is_enable']:
                    print(f"1. \033[91mЗаблокировать пользователя\033[0m")  
                else:
                    print(f"1. \033[92mРазблокировать пользователя\033[0m")  

                    
                print("2. Добавить баланс")
                print("\n0. Вернуться в меню пользователей")
                
                choice = input("\nВыберите действие: ")
                
                if choice == "0":
                    return  
                
                elif choice == "1":
                    new_status = 0 if user['is_enable'] else 1
                    status_query = "UPDATE user SET is_enable = ? WHERE telegram_id = ?"
                    await conn.execute(status_query, (new_status, user['telegram_id']))
                    await conn.commit()
                    
                    async with conn.execute("SELECT * FROM user WHERE telegram_id = ?", (user['telegram_id'],)) as cursor:
                        user = await cursor.fetchone()
                        
                    print(f"\nСтатус пользователя изменен на: {'Активен' if new_status else 'Заблокирован'}")
                    input("\nНажмите Enter для продолжения...")
                
                elif choice == "2":
                    while True:
                        try:
                            amount_input = input("\nВведите сумму для добавления на баланс пользователю: ")
                            amount = float(amount_input)
                            if amount <= 0:
                                print("Сумма должна быть положительной.")
                                continue
                            break
                        except ValueError:
                            print("Пожалуйста, введите корректное число.")
                    
                    check_balance_query = "SELECT * FROM user_balance WHERE user_id = ?"
                    async with conn.execute(check_balance_query, (user['telegram_id'],)) as cursor:
                        existing_balance = await cursor.fetchone()
                    
                    if existing_balance:
                        update_query = """
                        UPDATE user_balance 
                        SET balance = balance + ?, last_update = CURRENT_TIMESTAMP 
                        WHERE user_id = ?
                        """
                        await conn.execute(update_query, (amount, user['telegram_id']))
                    else:
                        insert_query = """
                        INSERT INTO user_balance (user_id, balance) 
                        VALUES (?, ?)
                        """
                        await conn.execute(insert_query, (user['telegram_id'], amount))
                    
                    transaction_query = """
                    INSERT INTO balance_transactions (user_id, amount, type, description) 
                    VALUES (?, ?, 'deposit', 'Добавление баланса технической поддержкой')
                    """
                    await conn.execute(transaction_query, (user['telegram_id'], amount))
                    
                    await conn.commit()
                    
                    print(f"\nБаланс пользователя успешно увеличен на {amount}")
                    input("\nНажмите Enter для продолжения...")
                else:
                    print("\nНеверный выбор. Попробуйте снова.")
                    input("\nНажмите Enter для продолжения...")
                    
        print("\n1. Вернуться в меню пользователей")
        print("2. Вернуться в главное меню")
        print("0. Выйти из программы")
        
        while True:
            choice = input("\nВыберите действие: ")
            if choice == "1":
                return  
            elif choice == "2":
                return "main"  
            elif choice == "0":
                print("Выход из программы...")
                exit(0)
            else:
                print("Неверный выбор. Попробуйте снова.")
                
    except Exception as e:
        print(f"Ошибка при редактировании пользователя: {e}")
        print("\nНажмите Enter для продолжения...")
        input()
        return

async def handle_users_menu(conn):
    """Обработка меню пользователей"""
    while True:
        choice = await display_users_menu()
        
        if choice == "0":
            return  
        elif choice == "1":
            result = await show_user_stats(conn)
            if result == "main":
                return  
        elif choice == "2":
            result = await find_user(conn)
            if result == "main":
                return  
        elif choice == "3":
            result = await add_user(conn)
            if result == "main":
                return  
        elif choice == "4":
            result = await delete_user(conn)
            if result == "main":
                return  
        elif choice == "5":
            result = await edit_user(conn)
            if result == "main":
                return  
        else:
            print("Неверный выбор. Попробуйте снова.")
            await asyncio.sleep(1)

async def main():
    """Основная функция приложения"""
    conn = await connect_db()
    if not conn:
        print("Невозможно продолжить без подключения к базе данных.")
        return
    
    try:
        while True:
            choice = await display_main_menu()
            
            if choice == "0":
                print("Выход из программы...")
                break
            elif choice == "1":
                await handle_users_menu(conn)
            elif choice in ["2", "3", "4", "5"]:
                print("Этот раздел находится в разработке.")
                input("Нажмите Enter для продолжения...")
            else:
                print("Неверный выбор. Попробуйте снова.")
                await asyncio.sleep(1)
    finally:
        if conn:
            await conn.close()
            print("Соединение с базой данных закрыто.")

if __name__ == "__main__":
    asyncio.run(main()) 
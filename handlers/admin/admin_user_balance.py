from aiogram import Router, F
from aiogram.types import CallbackQuery, BufferedInputFile
from handlers.database import Database
from handlers.admin.admin_kb import get_admin_show_users_balance_keyboard, get_admin_add_users_balance_keyboard
import aiosqlite
from loguru import logger
from datetime import datetime
import io
from aiogram.fsm.context import FSMContext
from aiogram.types import Message
from handlers.admin.admin_states import AdminUserBalanceState

router = Router()

@router.callback_query(F.data == "admin_show_users_balance")
async def show_users_balance(callback: CallbackQuery):
    """Показать информацию о балансах пользователей"""
    try:
        db = Database()
        
        async with aiosqlite.connect(db.db_path) as conn:
            async with conn.execute(
                "SELECT COUNT(DISTINCT user_id) as users_count FROM user_balance"
            ) as cursor:
                users_count = await cursor.fetchone()
                users_count = users_count[0] if users_count else 0
            
            async with conn.execute(
                "SELECT SUM(balance) as total_balance FROM user_balance"
            ) as cursor:
                total_balance = await cursor.fetchone()
                total_balance = total_balance[0] if total_balance else 0
        
        await callback.message.delete()
        
        await callback.message.answer(
            "<b>Депозиты</b>\n"
            "<blockquote>\n"
            f"Депозиты есть у <b>{users_count}</b> пользователей\n"
            f"Всего депозитов на сумму: <b>{total_balance:.2f}</b> руб.\n"
            "</blockquote>",
            parse_mode="HTML",
            reply_markup=get_admin_show_users_balance_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка при получении информации о балансах: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при получении информации о балансах.\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=get_admin_show_users_balance_keyboard()
        )

@router.callback_query(F.data == "admin_get_all_transactions")
async def get_all_transactions(callback: CallbackQuery):
    """Отправить файл со всеми транзакциями"""
    try:
        db = Database()
        
        buffer = io.StringIO()
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
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
                ORDER BY bt.created_at DESC
            """
            
            async with conn.execute(query) as cursor:
                transactions = await cursor.fetchall()
                
            for tx in transactions:
                status = "Пополнение" if tx['type'] == 'deposit' else \
                        "Списание" if tx['type'] == 'subscription_payment' else \
                        "Возврат" if tx['type'] == 'refund' else tx['type']
                
                buffer.write("------------------------\n")
                buffer.write(f"ID: {tx['id']}\n")
                buffer.write(f"Username: {tx['username'] or 'Не указан'}\n")
                buffer.write(f"telegram_id: {tx['telegram_id']}\n")
                buffer.write(f"Сумма: {tx['amount']} руб.\n")
                buffer.write(f"Статус: {status}\n")
                buffer.write(f"Описание: {tx['description'] or 'Нет описания'}\n")
                buffer.write(f"Идентификатор платежа: {tx['payment_id'] or 'Нет'}\n")
                buffer.write(f"Дата: {datetime.fromisoformat(tx['created_at']).strftime('%Y-%m-%d %H:%M:%S')}\n")
                buffer.write("------------------------\n\n")
        
        file_content = buffer.getvalue()
        buffer.close()
        
        filename = f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        
        file = BufferedInputFile(
            file_content.encode('utf-8'),
            filename=filename
        )
        
        await callback.message.answer_document(
            document=file,
            caption="📄 Файл со всеми транзакциями",
            reply_markup=get_admin_show_users_balance_keyboard()
        )
        
        await callback.answer("Файл с транзакциями сформирован")
        
    except Exception as e:
        logger.error(f"Ошибка при формировании файла транзакций: {e}")
        await callback.message.answer(
            "❌ Произошла ошибка при формировании файла транзакций.\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=get_admin_show_users_balance_keyboard()
        )

@router.callback_query(F.data == "admin_find_user")
async def find_user_start(callback: CallbackQuery, state: FSMContext):
    """Начало поиска пользователя"""
    try:
        await callback.message.delete()
        
        await callback.message.answer(
            "Введите имя пользователя или telegram id для поиска"
        )
        
        await state.set_state(AdminUserBalanceState.waiting_for_user_input)
        
    except Exception as e:
        logger.error(f"Ошибка при запуске поиска пользователя: {e}")
        await callback.message.answer(
            "❌ Произошла ошибка.\nПожалуйста, попробуйте позже.",
            reply_markup=get_admin_show_users_balance_keyboard()
        )

@router.message(AdminUserBalanceState.waiting_for_user_input)
async def process_user_search(message: Message, state: FSMContext):
    """Обработка поиска пользователя"""
    try:
        db = Database()
        search_query = message.text.strip()
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            
            query = """
                SELECT u.*, ub.balance 
                FROM user u
                LEFT JOIN user_balance ub ON u.telegram_id = ub.user_id
                WHERE u.telegram_id = ? OR LOWER(u.username) = LOWER(?)
            """
            
            async with conn.execute(query, (
                search_query if search_query.isdigit() else -1,
                search_query
            )) as cursor:
                user = await cursor.fetchone()
            
            if user:
                display_name = user['username'] or f"ID: {user['telegram_id']}"
                balance = user['balance'] or 0.00
                
                await message.answer(
                    f"Пользователь <b>{display_name}</b> найден!\n\n"
                    f"telegram_id: {user['telegram_id']}\n"
                    f"Баланс пользователя: <b>{balance:.2f}</b> руб.",
                    parse_mode="HTML",
                    reply_markup=get_admin_add_users_balance_keyboard()
                )
            else:
                await message.answer(
                    "❌ Пользователь не найден",
                    reply_markup=get_admin_show_users_balance_keyboard()
                )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при поиске пользователя: {e}")
        await message.answer(
            "❌ Произошла ошибка при поиске пользователя.\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=get_admin_show_users_balance_keyboard()
        )
        await state.clear() 
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from handlers.database import Database
from handlers.admin.admin_kb import get_admin_add_users_balance_keyboard, get_admin_balance_back_edit_keyboard
from handlers.user.user_kb import get_user_balance_keyboard, get_user_edit_balance_keyboard
import aiosqlite
from loguru import logger
from datetime import datetime
import re
from aiogram.fsm.context import FSMContext
from handlers.admin.admin_states import AdminBalanceState

router = Router()

def get_add_balance_keyboard(user_id: int) -> InlineKeyboardBuilder:
    """Создание клавиатуры с суммами пополнения"""
    keyboard = InlineKeyboardBuilder()
    amounts = [100, 250, 500, 750, 1000, 1500, 2000, 2500]
    
    for amount in amounts:
        keyboard.button(
            text=f"{amount} руб.",
            callback_data=f"add_balance:{user_id}:{amount}"
        )
    
    keyboard.button(text="🔙 Назад", callback_data="admin_show_users_balance")
    keyboard.adjust(2)  
    return keyboard.as_markup()

@router.callback_query(F.data == "admin_add_users_balance")
async def show_add_balance_menu(callback: CallbackQuery):
    """Показ меню добавления баланса"""
    try:
        db = Database()
        
        message_text = callback.message.text
        user_id = None
        
        if "telegram_id:" in message_text:
            user_id = message_text.split("telegram_id:")[1].split()[0].strip()
        elif "ID:" in message_text:
            user_id = message_text.split("ID:")[1].split()[0].strip()
        else:
            username_match = re.search(r'<b>(.*?)</b>', message_text)
            if username_match:
                username = username_match.group(1)
                async with aiosqlite.connect(db.db_path) as conn:
                    async with conn.execute(
                        "SELECT telegram_id FROM user WHERE username = ?",
                        (username,)
                    ) as cursor:
                        result = await cursor.fetchone()
                        user_id = result[0] if result else None
        
        if not user_id:
            await callback.answer("Ошибка: пользователь не найден")
            return
            
        async with aiosqlite.connect(db.db_path) as conn:
            async with conn.execute(
                "SELECT username FROM user WHERE telegram_id = ?",
                (user_id,)
            ) as cursor:
                user = await cursor.fetchone()
                username = user[0] if user else f"ID: {user_id}"
        
        await callback.message.delete()
        
        await callback.message.answer(
            "💰 Добавление баланса\n\n"
            f"Вы собираетесь пополнить баланс пользователю <b>{username}</b>.\n"
            "Пожалуйста, выберите сумму для зачисления. 💳✨",
            parse_mode="HTML",
            reply_markup=get_add_balance_keyboard(int(user_id))
        )
        
    except Exception as e:
        logger.error(f"Ошибка при показе меню добавления баланса: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка.\nПожалуйста, попробуйте позже.",
            reply_markup=get_admin_add_users_balance_keyboard()
        )

@router.callback_query(F.data.startswith("add_balance:"))
async def process_balance_add(callback: CallbackQuery):
    """Обработка добавления баланса"""
    try:
        _, user_id, amount = callback.data.split(":")
        user_id = int(user_id)
        amount = float(amount)
        
        db = Database()
        logger.info(f"Начало пополнения баланса администратором для пользователя {user_id} на сумму {amount} руб.")
        
        async with aiosqlite.connect(db.db_path) as conn:
            async with conn.execute(
                "SELECT username FROM user WHERE telegram_id = ?",
                (user_id,)
            ) as cursor:
                user = await cursor.fetchone()
                username = user[0] if user else f"ID: {user_id}"
            
            async with conn.execute(
                "SELECT balance FROM user_balance WHERE user_id = ?",
                (user_id,)
            ) as cursor:
                current_balance = await cursor.fetchone()
            
            if current_balance:
                logger.info(f"Обновление существующего баланса пользователя {user_id}. "
                          f"Текущий баланс: {current_balance[0]}, сумма пополнения: {amount}")
                await conn.execute(
                    """
                    UPDATE user_balance 
                    SET balance = balance + ?, last_update = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                    """,
                    (amount, user_id)
                )
            else:
                logger.info(f"Создание нового баланса для пользователя {user_id} с суммой {amount}")
                await conn.execute(
                    """
                    INSERT INTO user_balance (user_id, balance) 
                    VALUES (?, ?)
                    """,
                    (user_id, amount)
                )
            
            await conn.execute(
                """
                INSERT INTO balance_transactions 
                (user_id, amount, type, description) 
                VALUES (?, ?, 'deposit', 'Пополнение баланса администратором')
                """,
                (user_id, amount)
            )
            
            await conn.commit()
            logger.info(f"Баланс пользователя {user_id} успешно пополнен на {amount} руб.")
            
            try:
                await callback.bot.send_message(
                    chat_id=user_id,
                    text="💰 Ваш баланс пополнен администратором!\n\n"
                         f"Сумма пополнения: <b>{amount:.2f}</b> руб.",
                    parse_mode="HTML",
                    reply_markup=get_user_edit_balance_keyboard()
                )
                logger.info(f"Уведомление о пополнении баланса отправлено пользователю {user_id}")
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")
            
            await callback.message.edit_text(
                "✅ Баланс успешно пополнен!\n\n"
                f"Пользователь: <b>{username}</b>\n"
                f"Сумма: <b>{amount:.2f}</b> руб.",
                parse_mode="HTML",
                reply_markup=get_admin_balance_back_edit_keyboard()
            )
            
    except Exception as e:
        logger.error(f"Ошибка при пополнении баланса пользователя {user_id}: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при пополнении баланса.\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=get_admin_add_users_balance_keyboard()
        )

@router.callback_query(F.data == "admin_reset_users_balance")
async def start_reset_balance(callback: CallbackQuery, state: FSMContext):
    """Начало процесса обнуления баланса"""
    try:
        message_text = callback.message.text
        user_id = None
        
        if "telegram_id:" in message_text:
            user_id = message_text.split("telegram_id:")[1].split()[0].strip()
        elif "ID:" in message_text:
            user_id = message_text.split("ID:")[1].split()[0].strip()
        else:
            username_match = re.search(r'<b>(.*?)</b>', message_text)
            if username_match:
                username = username_match.group(1)
                async with aiosqlite.connect(db.db_path) as conn:
                    async with conn.execute(
                        "SELECT telegram_id FROM user WHERE username = ?",
                        (username,)
                    ) as cursor:
                        result = await cursor.fetchone()
                        user_id = result[0] if result else None
        
        if not user_id:
            await callback.answer("Ошибка: пользователь не найден")
            return
            
        await state.update_data(user_id=user_id)
        
        await callback.message.delete()
        
        await callback.message.answer(
            "📝 Укажите причину обнуления баланса\n\n"
            "Пожалуйста, введите причину списания средств."
        )
        
        await state.set_state(AdminBalanceState.waiting_for_reset_reason)
        
        logger.info(f"Начат процесс обнуления баланса для пользователя {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при начале процесса обнуления баланса: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка.\nПожалуйста, попробуйте позже.",
            reply_markup=get_admin_add_users_balance_keyboard()
        )

@router.message(AdminBalanceState.waiting_for_reset_reason)
async def process_reset_balance(message: Message, state: FSMContext):
    """Обработка причины обнуления баланса"""
    try:
        state_data = await state.get_data()
        user_id = state_data.get('user_id')
        reason = message.text.strip()
        
        db = Database()
        logger.info(f"Проверка баланса пользователя {user_id} для обнуления")
        
        async with aiosqlite.connect(db.db_path) as conn:
            async with conn.execute(
                """
                SELECT ub.balance, u.username 
                FROM user_balance ub 
                LEFT JOIN user u ON u.telegram_id = ub.user_id 
                WHERE ub.user_id = ?
                """,
                (user_id,)
            ) as cursor:
                result = await cursor.fetchone()
                
            if not result:
                logger.info(f"У пользователя {user_id} нет баланса для обнуления")
                await message.answer(
                    "ℹ️ У пользователя нет баланса для обнуления",
                    reply_markup=get_admin_add_users_balance_keyboard()
                )
                await state.clear()
                return
                
            current_balance = result[0]
            username = result[1] or f"ID: {user_id}"
            
            if current_balance <= 0:
                logger.info(f"Попытка обнулить нулевой баланс пользователя {user_id}")
                await message.answer(
                    f"ℹ️ Баланс пользователя <b>{username}</b> уже равен нулю.\n"
                    "Обнуление не требуется.",
                    parse_mode="HTML",
                    reply_markup=get_admin_balance_back_edit_keyboard()
                )
                await state.clear()
                return
            
            await conn.execute(
                """
                INSERT INTO balance_transactions 
                (user_id, amount, type, description) 
                VALUES (?, ?, 'reset', ?)
                """,
                (user_id, -current_balance, f"Обнуление баланса администратором. Причина: {reason}")
            )
            
            await conn.execute(
                """
                UPDATE user_balance 
                SET balance = 0, last_update = CURRENT_TIMESTAMP 
                WHERE user_id = ?
                """,
                (user_id,)
            )
            
            await conn.commit()
            logger.info(f"Баланс пользователя {user_id} успешно обнулен. Было списано: {current_balance:.2f} руб.")
            
            try:
                await message.bot.send_message(
                    chat_id=user_id,
                    text=(
                        "❗️ Ваш баланс был обнулен администратором\n\n"
                        f"Причина: {reason}\n"
                        f"Списано: {current_balance:.2f} руб."
                    ),
                    parse_mode="HTML",
                    reply_markup=get_user_balance_keyboard()
                )
                logger.info(f"Уведомление об обнулении баланса отправлено пользователю {user_id}")
            except Exception as e:
                logger.error(f"Ошибка при отправке уведомления пользователю {user_id}: {e}")
            
            await message.answer(
                "✅ Баланс успешно обнулен!\n\n"
                f"Пользователь: <b>{username}</b>\n"
                f"Списано: <b>{current_balance:.2f}</b> руб.\n"
                f"Причина: {reason}",
                parse_mode="HTML",
                reply_markup=get_admin_balance_back_edit_keyboard()
            )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при обнулении баланса: {e}")
        await message.answer(
            "❌ Произошла ошибка при обнулении баланса.\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=get_admin_add_users_balance_keyboard()
        )
        await state.clear() 
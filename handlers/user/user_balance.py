from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from handlers.database import Database
from handlers.user.user_kb import get_user_balance_keyboard
from datetime import datetime
from handlers.yookassa import yookassa_manager
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
from aiogram.filters import StateFilter
import aiosqlite

class BalanceState(StatesGroup):
    waiting_for_amount = State()

router = Router()

@router.callback_query(F.data == "lk_my_balance")
async def show_user_balance(callback: CallbackQuery):
    """Показать баланс пользователя"""
    try:
        db = Database()
        logger.info(f"Запрос баланса от пользователя {callback.from_user.id}")
        
        current_balance = await db.get_user_balance(callback.from_user.id)
        logger.info(f"Текущий баланс пользователя {callback.from_user.id}: {current_balance:.2f} руб.")
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            query = """
                SELECT amount, type, description, created_at
                FROM balance_transactions
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT 5
            """
            
            async with conn.execute(query, (callback.from_user.id,)) as cursor:
                transactions = await cursor.fetchall()
            
            logger.info(f"Получено {len(transactions)} последних транзакций для пользователя {callback.from_user.id}")
            
            message_text = (
                f"💰 <b>Ваш баланс:</b> {current_balance:.2f} руб.\n\n"
                "📋 <b>Последние операции:</b>\n"
            )
            
            if transactions:
                for tx in transactions:
                    operation_type = "➕" if tx['type'] == 'deposit' else \
                                   "➖" if tx['type'] == 'subscription_payment' else \
                                   "♻️" if tx['type'] == 'refund' else "❓"
                    
                    date = datetime.fromisoformat(tx['created_at']).strftime('%d.%m.%Y %H:%M')
                    
                    message_text += (
                        f"<blockquote>"
                        f"{operation_type} {abs(tx['amount']):.2f} руб. - "
                        f"{tx['description']}\n"
                        f"<code>{date}</code>\n"
                        f"</blockquote>\n"
                    )
                    
                logger.info(f"История транзакций успешно сформирована для пользователя {callback.from_user.id}")
            else:
                message_text += "\nИстория операций пуста"
                logger.info(f"У пользователя {callback.from_user.id} нет истории транзакций")
            
            can_edit = (
                hasattr(callback.message, 'text') and 
                callback.message.text is not None
            )
            
            if can_edit:
                try:
                    await callback.message.edit_text(
                        message_text,
                        parse_mode="HTML",
                        reply_markup=get_user_balance_keyboard()
                    )
                    logger.info(f"Сообщение успешно отредактировано для пользователя {callback.from_user.id}")
                except Exception as edit_error:
                    logger.debug(f"Не удалось отредактировать сообщение: {edit_error}")
                    can_edit = False
            
            if not can_edit:
                await callback.message.answer(
                    message_text,
                    parse_mode="HTML",
                    reply_markup=get_user_balance_keyboard()
                )
                try:
                    await callback.message.delete()
                except Exception as del_error:
                    logger.debug(f"Не удалось удалить старое сообщение: {del_error}")
            
            logger.info(f"Отправлено новое сообщение с балансом для пользователя {callback.from_user.id}")
            
    except Exception as e:
        logger.error(f"Ошибка при показе баланса пользователя {callback.from_user.id}: {e}")
        try:
            await callback.message.answer(
                "❌ Произошла ошибка при получении информации о балансе.\n"
                "Пожалуйста, попробуйте позже.",
                reply_markup=get_user_balance_keyboard()
            )
        except Exception as answer_error:
            logger.error(f"Ошибка при отправке сообщения об ошибке: {answer_error}")

def get_balance_amount_keyboard() -> InlineKeyboardBuilder:
    """Создание клавиатуры для выбора суммы пополнения"""
    keyboard = InlineKeyboardBuilder()
    
    amounts = ["100", "250", "500", "1000"]
    for amount in amounts:
        keyboard.button(
            text=f"{amount} руб.", 
            callback_data=f"add_balance_{amount}"
        )
    
    keyboard.button(
        text="Другая сумма",
        callback_data="add_balance_custom"
    )
    
    keyboard.button(
        text="🔙 Назад",
        callback_data="lk_my_balance"
    )
    
    keyboard.adjust(2)
    return keyboard.as_markup()

@router.callback_query(F.data == "start_add_balance")
async def start_add_balance(callback: CallbackQuery):
    """Начало процесса пополнения баланса"""
    await callback.message.edit_text(
        "💰 Пополнение баланса\n\n"
        "Вы собираетесь пополнить баланс через платежную систему <b>ЮKassa</b>.\n"
        "Пожалуйста, выберите сумму для создания счета. 💰✅",
        parse_mode="HTML",
        reply_markup=get_balance_amount_keyboard()
    )

@router.callback_query(F.data.startswith("add_balance_"))
async def process_balance_amount(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора суммы пополнения"""
    amount_str = callback.data.replace("add_balance_", "")
    
    if amount_str == "custom":
        await callback.message.edit_text(
            "Введите сумму для пополнения в рублях (минимум 10 рублей):",
            reply_markup=get_user_balance_keyboard()
        )
        await state.set_state(BalanceState.waiting_for_amount)
        return

    await create_payment(callback, float(amount_str))

@router.message(StateFilter(BalanceState.waiting_for_amount), flags={"long_operation": "typing"})
async def process_custom_amount(message: Message, state: FSMContext):
    """Обработка введенной пользователем суммы"""
    try:
        amount = float(message.text)
        if amount < 10:
            await message.answer(
                "❌ Минимальная сумма пополнения - 10 рублей",
                reply_markup=get_balance_amount_keyboard()
            )
            return
        
        await state.clear()
        await create_payment(message, amount)
        
    except ValueError:
        await message.answer(
            "❌ Пожалуйста, введите корректную сумму",
            reply_markup=get_balance_amount_keyboard()
        )

async def create_payment(event, amount: float):
    """Создание платежа в ЮKassa"""
    description = f"Пополнение баланса для пользователя @{event.from_user.username or event.from_user.id}"
    
    payment_id, payment_url = await yookassa_manager.create_payment(
        amount=amount,
        description=description,
        user_id=str(event.from_user.id),
        username=event.from_user.username
    )
    
    if payment_id and payment_url:
        db = Database()
        await db.update_balance(
            user_id=event.from_user.id,
            amount=0,
            type='pending',
            description=f"Ожидание пополнения на сумму {amount} руб.",
            payment_id=payment_id
        )
        
        message_text = (
            "✅ Счет на оплату создан!\n\n"
            f"Сумма: {amount} руб.\n"
            "Для оплаты перейдите по ссылке ниже 👇"
        )
        
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(
                message_text,
                reply_markup=InlineKeyboardBuilder()
                .button(text="💰 Оплатить", url=payment_url)
                .button(text="🕵️‍♂️ Проверить оплату", callback_data=f"check_balance_payment:{payment_id}")
                .button(text="🔙 Назад", callback_data="lk_my_balance")
                .adjust(1)
                .as_markup()
            )
        else:
            await event.answer(
                message_text,
                reply_markup=InlineKeyboardBuilder()
                .button(text="💰 Оплатить", url=payment_url)
                .button(text="🕵️‍♂️ Проверить оплату", callback_data=f"check_balance_payment:{payment_id}")
                .button(text="🔙 Назад", callback_data="lk_my_balance")
                .adjust(1)
                .as_markup()
            )
    else:
        error_text = "❌ Ошибка при создании платежа. Попробуйте позже."
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(
                error_text,
                reply_markup=get_user_balance_keyboard()
            )
        else:
            await event.answer(
                error_text,
                reply_markup=get_user_balance_keyboard()
            )

@router.callback_query(F.data.startswith("check_balance_payment:"))
async def check_payment_status(callback: CallbackQuery, state: FSMContext):
    """Проверка статуса платежа"""
    try:
        payment_id = callback.data.split(":")[1]
        
        if await yookassa_manager.check_payment(payment_id, callback.bot):
            await show_user_balance(callback)
            return
            
        await callback.message.edit_text(
            "❌ Оплата еще не поступила.\n\n"
            "Если вы уже оплатили, подождите немного и нажмите кнопку проверки снова.",
            reply_markup=InlineKeyboardBuilder()
            .button(text="🕵️‍♂️ Проверить оплату", callback_data=f"check_balance_payment:{payment_id}")
            .button(text="🔙 Назад", callback_data="lk_my_balance")
            .adjust(1)
            .as_markup()
        )
        await callback.answer("Платеж в обработке. Пожалуйста, подождите.")
            
    except Exception as e:
        logger.error(f"Ошибка при проверке платежа: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при проверке платежа.\n"
            "Пожалуйста, попробуйте позже или обратитесь в поддержку.",
            reply_markup=get_user_balance_keyboard()
        )

async def process_successful_balance_payment(payment_id: str, amount: float, user_id: int, bot):
    """Обработка успешного платежа для пополнения баланса"""
    db = Database()
    
    if await db.update_balance(
        user_id=user_id,
        amount=amount,
        type='deposit',
        description=f"Пополнение баланса на сумму {amount} руб.",
        payment_id=payment_id
    ):
        try:
            await bot.send_message(
                chat_id=user_id,
                text=(
                    "✅ Баланс успешно пополнен!\n\n"
                    f"Сумма пополнения: {amount} руб.\n"
                    "Спасибо за использование нашего сервиса! 🙏"
                ),
                reply_markup=get_user_balance_keyboard()
            )
        except Exception as e:
            logger.error(f"Ошибка при отправке уведомления о пополнении баланса: {e}") 
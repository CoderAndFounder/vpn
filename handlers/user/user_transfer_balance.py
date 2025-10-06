from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from handlers.database import Database
from handlers.user.user_kb import get_user_balance_keyboard, get_user_success_transfer_keyboard, get_user_cancel_transfer_keyboard
from loguru import logger
from aiogram.fsm.context import FSMContext
from handlers.user.user_state import TransferState
import aiosqlite

router = Router()

def get_transfer_keyboard(show_send_button: bool = False) -> InlineKeyboardBuilder:
    """Создание клавиатуры для перевода средств"""
    keyboard = InlineKeyboardBuilder()
    
    if show_send_button:
        keyboard.button(text="📤 Отправить", callback_data="send_balance")
    
    keyboard.button(text="❌ Отмена", callback_data="lk_my_balance")
    keyboard.adjust(1)
    return keyboard.as_markup()

@router.callback_query(F.data == "start_transfer_balance")
async def show_transfer_menu(callback: CallbackQuery):
    """Показ меню перевода средств"""
    try:
        db = Database()
        logger.info(f"Запрос на перевод средств от пользователя {callback.from_user.id}")
        
        current_balance = await db.get_user_balance(callback.from_user.id)
        logger.info(f"Текущий баланс пользователя {callback.from_user.id}: {current_balance:.2f} руб.")
        
        await callback.message.delete()
        
        if current_balance > 0:
            await callback.message.answer(
                "💳 Операция перевода средств\n\n"
                "Вы можете отправить средства другому пользователю.\n"
                f"💰 Доступно для перевода: <b>{current_balance:.2f}</b> руб.\n\n"
                "Нажмите на кнопку <b>Отправить</b> после чего введите <i><b>имя пользователя</b></i> "
                "или <i><b>Telegram ID</b></i> или нажмите кнопку <b>Отмена</b> для отмены операции",
                parse_mode="HTML",
                reply_markup=get_transfer_keyboard(show_send_button=True)
            )
            logger.info(f"Показано меню перевода для пользователя {callback.from_user.id}")
        else:
            await callback.message.answer(
                "💳 Операция перевода средств\n\n"
                "❌ У Вас недостаточно средств на балансе, операция перевода недоступна.",
                reply_markup=get_transfer_keyboard(show_send_button=False)
            )
            logger.info(f"Отказано в переводе средств пользователю {callback.from_user.id} (недостаточно средств)")
            
    except Exception as e:
        logger.error(f"Ошибка при показе меню перевода средств: {e}")
        await callback.message.answer(
            "❌ Произошла ошибка при проверке баланса.\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=get_user_balance_keyboard()
        ) 

def get_confirm_transfer_keyboard() -> InlineKeyboardBuilder:
    """Создание клавиатуры для подтверждения перевода"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Подтвердить", callback_data="confirm_transfer")
    keyboard.button(text="❌ Отмена", callback_data="cancel_transfer")
    keyboard.adjust(1)
    return keyboard.as_markup()

@router.callback_query(F.data == "send_balance")
async def start_transfer(callback: CallbackQuery, state: FSMContext):
    """Начало процесса перевода"""
    try:
        await callback.message.delete()
        await callback.message.answer("Введите сумму для перевода:", reply_markup=get_user_cancel_transfer_keyboard())
        await state.set_state(TransferState.waiting_for_amount)
        logger.info(f"Пользователь {callback.from_user.id} начал процесс перевода")
    except Exception as e:
        logger.error(f"Ошибка при старте перевода: {e}")
        await callback.message.answer(
            "❌ Произошла ошибка.\nПожалуйста, попробуйте позже.",
            reply_markup=get_user_balance_keyboard()
        )

@router.message(TransferState.waiting_for_amount)
async def process_transfer_amount(message: Message, state: FSMContext):
    """Обработка введенной суммы"""
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return

        db = Database()
        current_balance = await db.get_user_balance(message.from_user.id)
        
        if amount > current_balance:
            await message.answer(
                "❌ Недостаточно средств на балансе\n"
                f"Доступно: {current_balance:.2f} руб.",
            )
            await state.clear()
            return

        await state.update_data(amount=amount)
        await message.answer("Введите имя пользователя или Telegram ID получателя:", reply_markup=get_user_cancel_transfer_keyboard())
        await state.set_state(TransferState.waiting_for_recipient)
        
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректную сумму")
    except Exception as e:
        logger.error(f"Ошибка при обработке суммы: {e}")
        await message.answer(
            "❌ Произошла ошибка.\nПожалуйста, попробуйте позже.",
            reply_markup=get_user_balance_keyboard()
        )
        await state.clear()

@router.message(TransferState.waiting_for_recipient)
async def process_transfer_recipient(message: Message, state: FSMContext):
    """Обработка получателя перевода"""
    try:
        db = Database()
        recipient_id = None
        search_query = message.text.strip()
        
        async with aiosqlite.connect(db.db_path) as conn:
            async with conn.execute(
                "SELECT telegram_id, username FROM user WHERE telegram_id = ? OR LOWER(username) = LOWER(?)",
                (search_query if search_query.isdigit() else -1, search_query)
            ) as cursor:
                recipient = await cursor.fetchone()

        if not recipient:
            await message.answer(
                "❌ Получатель не найден.\nПожалуйста, проверьте правильность ввода.",
                reply_markup=get_transfer_keyboard(show_send_button=True)
            )
            await state.clear()
            return

        recipient_id, recipient_username = recipient
        if recipient_id == message.from_user.id:
            await message.answer(
                "❌ Нельзя выполнить перевод самому себе",
                reply_markup=get_transfer_keyboard(show_send_button=True)
            )
            await state.clear()
            return

        state_data = await state.get_data()
        amount = state_data['amount']
        
        await state.update_data(recipient_id=recipient_id)
        
        await message.answer(
            f"Вы собираетесь отправить: <b>{amount:.2f}</b> руб.\n"
            f"Получатель: <b>{recipient_username or f'ID: {recipient_id}'}</b>\n\n"
            "Нажмите подтвердить, чтобы выполнить отправку",
            parse_mode="HTML",
            reply_markup=get_confirm_transfer_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка при обработке получателя: {e}")
        await message.answer(
            "❌ Произошла ошибка.\nПожалуйста, попробуйте позже.",
            reply_markup=get_user_balance_keyboard()
        )
        await state.clear()

@router.callback_query(F.data == "confirm_transfer")
async def confirm_transfer(callback: CallbackQuery, state: FSMContext):
    """Подтверждение перевода"""
    try:
        state_data = await state.get_data()
        amount = state_data['amount']
        recipient_id = state_data['recipient_id']
        
        db = Database()
        
        current_balance = await db.get_user_balance(callback.from_user.id)
        if amount > current_balance:
            await callback.message.edit_text(
                "❌ Недостаточно средств на балансе",
                reply_markup=get_user_balance_keyboard()
            )
            await state.clear()
            return

        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute("BEGIN TRANSACTION")
            try:
                await db.update_balance(
                    user_id=callback.from_user.id,
                    amount=-amount,
                    type='transfer_out',
                    description=f"Перевод пользователю {recipient_id}"
                )
                
                await db.update_balance(
                    user_id=recipient_id,
                    amount=amount,
                    type='transfer_in',
                    description=f"Перевод от пользователя {callback.from_user.id}"
                )
                
                await conn.commit()
                
                await callback.message.edit_text(
                    "✅ Перевод успешно выполнен!",
                    reply_markup=get_user_balance_keyboard()
                )
                
                try:
                    await callback.bot.send_message(
                        chat_id=recipient_id,
                        parse_mode="HTML",
                        text=f"🎉 Вам поступил перевод\n\n"
                             f"💰 На сумму <b>{amount:.2f}</b> руб.\n"
                             f"👤 От пользователя: <b>{callback.from_user.username}</b>",
                        reply_markup=get_user_success_transfer_keyboard()
                    )
                except Exception as e:
                    logger.error(f"Ошибка при отправке уведомления получателю: {e}")
                
            except Exception as e:
                await conn.rollback()
                raise e
                
    except Exception as e:
        logger.error(f"Ошибка при выполнении перевода: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при выполнении перевода.\n"
            "Пожалуйста, попробуйте позже.",
            reply_markup=get_user_balance_keyboard()
        )
    finally:
        await state.clear()

@router.callback_query(F.data == "cancel_transfer")
async def cancel_transfer(callback: CallbackQuery, state: FSMContext):
    """Отмена перевода"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Перевод отменен",
        reply_markup=get_user_balance_keyboard()
    ) 
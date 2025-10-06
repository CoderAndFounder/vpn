from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
from handlers.database import db
from handlers.admin.admin_kb import get_admin_keyboard

router = Router()

class AdminAnswerState(StatesGroup):
    waiting_for_message = State()

@router.callback_query(F.data == "admin_answer_message")
async def start_answer(callback: CallbackQuery, state: FSMContext):
    """Начало процесса ответа на сообщение"""
    try:
        if not await db.is_admin(callback.from_user.id):
            await callback.answer("У вас нет прав для выполнения этого действия")
            return

        message_text = callback.message.text
        try:
            id_line = [line for line in message_text.split('\n') if line.startswith('ID: ')][0]
            user_id = int(id_line.replace('ID: ', ''))
        except (IndexError, ValueError):
            await callback.answer("Не удалось определить ID получателя", show_alert=True)
            return

        await state.update_data(user_id=user_id)
        
        await callback.message.answer("Введите сообщение для отправки пользователю:")
        await state.set_state(AdminAnswerState.waiting_for_message)
        
    except Exception as e:
        logger.error(f"Ошибка при начале ответа на сообщение: {e}")
        await callback.answer("Произошла ошибка при обработке команды", show_alert=True)

@router.message(AdminAnswerState.waiting_for_message)
async def process_answer(message: Message, state: FSMContext):
    """Обработка ответа администратора"""
    try:
        data = await state.get_data()
        user_id = data.get('user_id')

        if not user_id:
            await message.answer("Ошибка: не найден ID получателя")
            await state.clear()
            return

        try:
            await message.bot.send_message(
                chat_id=user_id,
                text=f"📬 Ответ службы поддержки:\n\n{message.text}"
            )
            
            await message.answer(
                "✅ Сообщение успешно доставлено",
                reply_markup=get_admin_keyboard()
            )
            logger.info(f"Отправлен ответ пользователю {user_id} от администратора {message.from_user.id}")
            
        except Exception as e:
            await message.answer(
                f"❌ Сообщение не доставлено, ошибка: {str(e)}",
                reply_markup=get_admin_keyboard()
            )
            logger.error(f"Ошибка при отправке ответа пользователю {user_id}: {e}")
        
        finally:
            await state.clear()
            
    except Exception as e:
        logger.error(f"Ошибка при обработке ответа администратора: {e}")
        await message.answer(
            f"❌ Произошла ошибка: {str(e)}",
            reply_markup=get_admin_keyboard()
        )
        await state.clear() 
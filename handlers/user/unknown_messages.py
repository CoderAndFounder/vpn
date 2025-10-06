from aiogram import Router, F
from aiogram.types import Message
from loguru import logger
from handlers.user.user_kb import get_unknown_command_keyboard

router = Router()

@router.message(F.text)
async def unknown_message(message: Message):
    """Обработчик неизвестных сообщений"""
    try:
        await message.answer(
            "К сожалению, мы не смогли распознать ваше сообщение 😔. "
            "Если вам нужна помощь, нажмите кнопку 📞 <b>Техподдержка</b> и отправьте нам сообщение. "
            "Мы свяжемся с вами в ближайшее время! 💬✨",
            reply_markup=get_unknown_command_keyboard(),
            parse_mode="HTML"
        )
        logger.info(f"Получено неизвестное сообщение от пользователя {message.from_user.id}: {message.text}")
    except Exception as e:
        logger.error(f"Ошибка при обработке неизвестного сообщения: {e}") 
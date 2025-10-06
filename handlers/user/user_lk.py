from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InputMediaPhoto
from loguru import logger
import os

from handlers.database import db
from handlers.user.user_kb import get_lk_keyboard, get_start_keyboard
from handlers.commands import start_command

router = Router()

async def show_lk(message: Message, edit: bool = False):
    """Показать личный кабинет"""
    try:
        lk_message = await db.get_bot_message("user_lk")
        if not lk_message:
            text = "Личный кабинет"
        else:
            text = lk_message['text']

        keyboard = get_lk_keyboard()

        # Проверяем наличие изображения
        if lk_message and lk_message['image_path'] and os.path.exists(lk_message['image_path']):
            photo = FSInputFile(lk_message['image_path'])
            if edit and isinstance(message, Message):
                await message.edit_media(
                    media=photo,
                    caption=text,
                    parse_mode="HTML",
                    reply_markup=keyboard
                )
            else:
                await message.answer_photo(
                    photo=photo,
                    caption=text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
        else:
            if edit and isinstance(message, Message):
                await message.edit_text(
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            else:
                await message.answer(
                    text=text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )

        logger.info(f"Открыт личный кабинет пользователем: {message.from_user.id}")

    except Exception as e:
        logger.error(f"Ошибка при отображении личного кабинета: {e}")
        error_text = "Произошла ошибка при открытии личного кабинета"
        if edit:
            await message.edit_text(error_text)
        else:
            await message.answer(error_text)

@router.callback_query(F.data == "start_lk")
async def process_lk_button(callback: CallbackQuery):
    """Обработчик кнопки Личный кабинет"""
    try:
        await callback.message.delete()
        await show_lk(callback.message)
    except Exception as e:
        logger.error(f"Ошибка при переходе в личный кабинет: {e}")
        await callback.answer("Произошла ошибка при открытии личного кабинета")

@router.callback_query(F.data == "lk_back_to_start")
async def process_back_to_start(callback: CallbackQuery):
    """Обработчик кнопки Назад в личном кабинете"""
    try:
        start_message = await db.get_bot_message("start")
        if not start_message:
            text = "Добро пожаловить!"
        else:
            text = start_message['text']

        inline_keyboard = await get_start_keyboard()

        if start_message and start_message['image_path'] and os.path.exists(start_message['image_path']):
            photo = FSInputFile(start_message['image_path'])
            await callback.message.edit_media(
                media=InputMediaPhoto(
                    media=photo,
                    caption=text,
                    parse_mode="HTML"
                ),
                reply_markup=inline_keyboard
            )
        else:
            await callback.message.edit_text(
                text=text,
                reply_markup=inline_keyboard,
                parse_mode="HTML"
            )

        logger.info(f"Возврат в главное меню из личного кабинета пользователем: {callback.from_user.id}")
    except Exception as e:
        logger.error(f"Ошибка при возврате в главное меню: {e}")
        await callback.answer("Произошла ошибка при возврате в главное меню")

from aiogram import Router, F
from aiogram.types import CallbackQuery
from loguru import logger

from handlers.user.user_kb import get_user_instructions_keyboard, get_back_keyboard

router = Router()

@router.callback_query(F.data == "lk_instructions")
async def show_instructions_menu(callback: CallbackQuery):
    """Отображение меню инструкций"""
    logger.info(f"Получен callback: {callback.data}")
    try:
        await callback.message.delete()
        
        await callback.message.answer(
            "📖 Выберите интересующий вас раздел чтобы получить руководство по подключению 📡",
            reply_markup=get_user_instructions_keyboard()
        )

    except Exception as e:
        logger.error(f"Ошибка при отображении меню инструкций: {e}")
        await callback.message.answer(
            "Произошла ошибка при загрузке инструкций. Попробуйте позже."
        ) 

@router.callback_query(F.data == "instructions_android")
async def show_android_instructions(callback: CallbackQuery):
    """Отображение инструкций для Android"""

    logger.info(f"Получен callback: {callback.data}")
    try:
        await callback.message.delete()
        
        await callback.message.answer(
        f"📱 <b>Инструкции для Android</b>\n\n"
        f"<blockquote>"
        f"1. Заходим в Play Market\n"
        f"2. Устанавливаем Hiddify\n"
        f"3. Заходим в приложение\n"
        f"4. Нажимаем '+'  \n"
        f"5. Выбираем 'Добавить из буфера' (перед этим, надо скопировать ключ который выдал бот 'можно просто нажатием на ключ')\n"
        f"6. Готово!\n"
        f"</blockquote>",
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )

    except Exception as e:
        logger.error(f"Ошибка при отображении инструкций для Android: {e}")
        await callback.message.answer(
            "Произошла ошибка при загрузке инструкций. Попробуйте позже."
        )

@router.callback_query(F.data == "instructions_ios")
async def show_ios_instructions(callback: CallbackQuery):
    """Отображение инструкций для iOS"""

    logger.info(f"Получен callback: {callback.data}")
    try:
        await callback.message.delete()
        
        await callback.message.answer(
        f"📱 <b>Инструкции для IOS</b>\n\n"
        f"<blockquote>"
        f"1. Заходим в App Store\n"
        f"2. Устанавливаем v2raytun\n"
        f"3. Заходим в приложение\n"
        f"4. Нажимаем '+'  \n"
        f"5. Выбираем 'Добавить из буфера' (перед этим, надо скопировать ключ который выдал бот 'можно просто нажатием на ключ')\n"
        f"6. Готово!\n"
        f"</blockquote>",
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )

    except Exception as e:
        logger.error(f"Ошибка при отображении инструкций для IOS: {e}")
        await callback.message.answer(
            "Произошла ошибка при загрузке инструкций. Попробуйте позже."
        )

@router.callback_query(F.data == "instructions_windows")
async def show_windows_instructions(callback: CallbackQuery):
    """Отображение инструкций для Windows"""
    logger.info(f"Получен callback: {callback.data}")
    try:
        await callback.message.delete()
        
        await callback.message.answer(
        f"💻 <b>Инструкции для Windows</b>\n\n"
        f"<blockquote>"
        f"1. Скачивай <a href='https://github.com/hiddify/hiddify-config/releases/download/v2.0.1/hiddify-config-v2.0.1-windows-x64.exe'>файл</a> \n"
        f"2. Устанавливай на ПК и нажимаем 'начать'\n"
        f"3. 'Новый профиль'\n"
        f"4. Выбираем 'Добавить из буфера' (перед этим, надо скопировать ключ который выдал бот 'можно просто нажатием на ключ')  \n"
        f"5. Нажимаем 'Параметры конфигурации'\n"
        f"6. Выбираем 'Регион (другой)'\n"
        f"7. Переходим в <b><pre>C:\ProgramData\Microsoft\Windows\Start Menu\Programs</pre></b> На ярлыке ставим запуск от имени администратора, или каждый раз запускать вручную от администратора\n"
        f"8. Переходим в главную, нажимаем справа 2 ползунка и выбираем режим 'VPN' \n"
        f"9. Готово!\n"
        f"</blockquote>",
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )

    except Exception as e:
        logger.error(f"Ошибка при отображении инструкций для Android: {e}")
        await callback.message.answer(
            "Произошла ошибка при загрузке инструкций. Попробуйте позже."
        )

@router.callback_query(F.data == "instructions_macos")
async def show_macos_instructions(callback: CallbackQuery):
    """Отображение инструкций для MacOS"""
    logger.info(f"Получен callback: {callback.data}")

    try:
        await callback.message.delete()
        
        await callback.message.answer(
        f"💻 <b>Инструкции для MacOS</b>\n\n"
        f"<blockquote>"
        f"1. Заходим в App Store  \n"
        f"2. Устанавливаем Hiddify \n"
        f"3. Заходим в приложение \n"
        f"4. Нажимаем '+'  \n"
        f"5. Выбираем 'Добавить из буфера' (перед этим, надо скопировать ключ который выдал бот 'можно просто нажатием на ключ')\n"
        f"6. Готово!\n"
        f"</blockquote>",
        parse_mode="HTML",
        reply_markup=get_back_keyboard()
    )

    except Exception as e:
        logger.error(f"Ошибка при отображении инструкций для Android: {e}")
        await callback.message.answer(
            "Произошла ошибка при загрузке инструкций. Попробуйте позже."
        )

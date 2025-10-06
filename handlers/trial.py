from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from loguru import logger
import os

from handlers.database import db
from handlers.user.user_kb import get_trial_keyboard, get_trial_vless_keyboard, get_no_subscriptions_keyboard
from handlers.commands import start_command
from handlers.x_ui import xui_manager
from handlers.buy_subscribe import subscription_manager

router = Router()

async def get_active_trial_settings():
    """Получение активных настроек пробного периода"""
    async with db.connect() as conn:
        async with conn.execute(
            'SELECT * FROM trial_settings WHERE is_enable = 1 LIMIT 1'
        ) as cursor:
            trial = await cursor.fetchone()
            return dict(trial) if trial else None

@router.callback_query(F.data == "start_trial")
async def process_trial_button(callback: CallbackQuery):
    """Обработчик кнопки Пробный период"""
    try:
        await callback.message.delete()
        
        user = await db.get_user(callback.from_user.id)
        if not user:
            logger.error(f"Пользователь не найден: {callback.from_user.id}")
            await callback.message.answer("Произошла ошибка. Попробуйте позже.")
            return

        if user.get('trial_period'):
            text = "Вы уже пользовались пробным периодом, пожалуйста купите подписку на сервис"
            await callback.message.answer(
                text=text,
                reply_markup=get_trial_keyboard(show_connect=False)
            )
            logger.info(f"Пользователь уже использовал пробный период: {callback.from_user.id}")
            return

        trial_settings = await db.get_active_trial_settings()
        if not trial_settings:
            text = "К сожалению сейчас пробный период недоступен"
            await callback.message.answer(
                text=text,
                reply_markup=get_trial_keyboard(show_connect=False)
            )
            logger.info("Пробный период недоступен")
            return

        base_text = (
            "<b>Пробный период!</b>\n\n"
            "<blockquote>"
            f"<b>Наименование:</b> {trial_settings.get('name', 'Не указано')}\n"
            f"<b>Пробных дней:</b> {trial_settings.get('left_day', 0)}\n"
            f"<b>Сервер:</b> {trial_settings.get('server_name', 'Не указан')}\n"
            "</blockquote>\n"
        )

        message_data = await db.get_bot_message('trial_success')
        
        if message_data and message_data['image_path'] and os.path.exists(message_data['image_path']):
            full_text = base_text + message_data['text']
            await callback.message.answer_photo(
                photo=FSInputFile(message_data['image_path']),
                caption=full_text,
                reply_markup=get_trial_keyboard(show_connect=True),
                parse_mode="HTML"
            )
        else:
            text = base_text + "Хотите попробовать самый лучший сервис в мире? Жми кнопку подключить"
            await callback.message.answer(
                text=text,
                reply_markup=get_trial_keyboard(show_connect=True)
            )

        logger.info(f"Показано предложение пробного периода пользователю: {callback.from_user.id}")

    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки пробного периода: {e}")
        await callback.message.answer("Произошла ошибка. Попробуйте позже.")

@router.callback_query(F.data == "trial_connect")
async def process_trial_connect(callback: CallbackQuery):
    """Обработчик кнопки Подключить пробный период"""
    try:
        user = await db.get_user(callback.from_user.id)
        if not user:
            logger.error(f"Пользователь не найден: {callback.from_user.id}")
            await callback.message.answer("Произошла ошибка. Попробуйте позже.")
            return

        if user.get('trial_period'):
            text = "Вы уже пользовались пробным периодом, пожалуйста купите подписку на сервис"
            await callback.message.answer(
                text=text,
                reply_markup=get_trial_keyboard(show_connect=False)
            )
            return

        trial_settings = await db.get_active_trial_settings()
        if not trial_settings:
            await callback.message.answer(
                "К сожалению сейчас пробный период недоступен",
                reply_markup=get_trial_keyboard(show_connect=False)
            )
            return

        server_settings = await db.get_server_settings(trial_settings['server_id'])
        if not server_settings:
            await callback.message.answer(
                "Ошибка при получении настроек сервера",
                reply_markup=get_trial_keyboard(show_connect=False)
            )
            return

        subscription = await subscription_manager.create_subscription(
            user_id=callback.from_user.id,
            tariff_id=trial_settings['id'],
            is_trial=True
        )

        if not subscription:
            logger.error("Ошибка при создании подписки в базе данных")
            await callback.message.answer(
                "Произошла ошибка при активации пробного периода. Попробуйте позже.",
                reply_markup=get_trial_keyboard(show_connect=False)
            )
            return

        vless_link = subscription['vless']

        await db.update_user_trial_status(callback.from_user.id, True)

        text = (
            "🎉 Поздравляем! Ваш пробный период активирован!\n\n"
            f"Срок действия: {trial_settings['left_day']} дней\n"
            "Для подключения используйте следующую ссылку:\n\n"
            f"`{vless_link}`\n\n"
            "⚠️ Сохраните эту ссылку, она потребуется для настройки приложения.\n"
            "Инструкции по настройке вы можете найти в разделе Настройки."
        )
        
        await callback.message.answer(
            text=text,
            reply_markup=get_no_subscriptions_keyboard(),
            parse_mode="Markdown"
        )
        logger.info(f"Активирован пробный период для пользователя: {callback.from_user.id}")

    except Exception as e:
        logger.error(f"Ошибка при активации пробного периода: {e}")
        await callback.message.answer(
            "Произошла ошибка при активации пробного периода. Попробуйте позже.",
            reply_markup=get_trial_keyboard(show_connect=False)
        )

@router.callback_query(F.data == "trial_back")
async def process_trial_back(callback: CallbackQuery):
    """Обработчик кнопки Назад в меню пробного периода"""
    try:
        await callback.message.delete()
        await start_command(callback.message)
        logger.info(f"Возврат в главное меню из пробного периода: {callback.from_user.id}")
    except Exception as e:
        logger.error(f"Ошибка при возврате в главное меню: {e}")
        await callback.message.answer("Произошла ошибка при возврате в главное меню")

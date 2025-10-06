from aiogram import Router, F, types
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from loguru import logger
import os
import sys
import asyncio

from handlers.database import db
from handlers.admin.admin_kb import get_admin_user_sub_notify_keyboard

router = Router()

class NotifySettingsStates(StatesGroup):
    """Состояния для настройки уведомлений"""
    waiting_for_name = State()
    waiting_for_interval = State()

class DisableNotifyStates(StatesGroup):
    """Состояния для выключения уведомлений"""
    waiting_for_name_off = State()

@router.callback_query(F.data == "admin_user_sub_notification")
async def process_user_sub_notification(callback: CallbackQuery):
    """Обработчик кнопки пользовательских уведомлений"""
    try:
        notify_settings = await db.get_active_notify_settings()
        
        settings_info = []
        if notify_settings:
            for setting in notify_settings:
                name = setting['name']
                is_enable = "Включено" if setting['is_enable'] == 1 else "Выключено"
                interval = setting['interval']
                settings_info.append(f"📝 <b>Наименование:</b> {name}\n🔔 <b>Статус:</b> {is_enable}\n🕛 <b>Интервал:</b> {interval}")
        else:
            settings_info.append("📝 <b>Наименование:</b> Нет данных\n🔔 <b>Статус:</b> Выключено\n🕛 <b>Интервал:</b> Нет данных")

        message_text = (
            "✨ <b>Меню настроек оповещений пользователя</b> ✨\n\n"
            "📢 Здесь вы можете настроить уведомления для важных событий:\n"
            "- Оповещение об окончании подписки\n\n"
            "<b>Текущие настройки:</b>\n"
            "<blockquote>"
            f"{'\n'.join(settings_info)}\n"
            "</blockquote>"
        )

        await callback.message.edit_text(
            text=message_text,
            reply_markup=get_admin_user_sub_notify_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()

    except Exception as e:
        logger.error(f"Ошибка при обработке пользовательских уведомлений: {e}")
        await callback.answer("Произошла ошибка при получении настроек уведомлений", show_alert=True)

@router.callback_query(F.data == "admin_edit_user_notify")
async def process_edit_user_notify(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки изменения настроек уведомлений"""
    try:
        await callback.message.delete()
        
        await callback.message.answer(
            "Введите наименование для планировщика",
            parse_mode="HTML"
        )
        
        await state.set_state(NotifySettingsStates.waiting_for_name)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при обработке изменения настроек уведомлений: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@router.message(NotifySettingsStates.waiting_for_name)
async def process_notify_name(message: Message, state: FSMContext):
    """Обработчик ввода наименования планировщика"""
    try:
        await state.update_data(notify_name=message.text)
        
        await message.delete()
        
        await message.answer(
            f"⏳ <b>Введите интервал проверки в минутах</b> ⏳\n"
            f"<blockquote>"
            f"Если указать 120, бот будет каждые 2 часа проверять подписки пользователей.\n"
            f"📢 Если до окончания подписки остается менее суток, бот будет отправлять уведомление каждые 2 часа."
            f"</blockquote>",
            parse_mode="HTML"
        )
        
        await state.set_state(NotifySettingsStates.waiting_for_interval)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке наименования планировщика: {e}")
        await message.answer("Произошла ошибка при сохранении наименования")
        await state.clear()

@router.message(NotifySettingsStates.waiting_for_interval)
async def process_notify_interval(message: Message, state: FSMContext):
    """Обработчик ввода интервала планировщика"""
    try:
        try:
            interval = int(message.text)
            if interval <= 0:
                raise ValueError("Интервал должен быть положительным числом")
        except ValueError:
            await message.answer("Пожалуйста, введите корректное число минут")
            return
            
        data = await state.get_data()
        notify_name = data.get('notify_name')
        
        success = await db.add_notify_setting(
            name=notify_name,
            interval=interval,
            type='subscription_check'
        )
        
        await message.delete()
        
        if success:
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin_user_sub_notification")]
            ])
            
            await message.answer(
                f"✅ Оповещение \"{notify_name}\" успешно добавлено!\n"
                f"Бот будет автоматически перезапущен для применения настроек...",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
            
            await state.clear()
            
            await asyncio.sleep(2)
            
            logger.info("Перезапуск приложения для применения новых настроек планировщика")
            python = sys.executable
            os.execv(python, [python] + sys.argv)
            
        else:
            await message.answer("❌ Произошла ошибка при сохранении настроек")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при обработке интервала планировщика: {e}")
        await message.answer("Произошла ошибка при сохранении настроек")
        await state.clear()

@router.callback_query(F.data == "admin_off_user_notify")
async def process_off_user_notify(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки выключения уведомлений"""
    try:
        active_settings = await db.get_active_notify_settings()
        
        settings_info = []
        for setting in active_settings:
            type_text = "Проверка подписок" if setting['type'] == 'subscription_check' else "Другая проверка"
            settings_info.append(f"📝 <b>Наименование:</b> {setting['name']}\n💫 <b>Тип:</b> {type_text}")
        
        if not settings_info:
            settings_info = ["Нет активных планировщиков"]
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔙 Отмена", callback_data="admin_user_sub_notification")]
        ])
        
        message_text = (
            "Введите наименование планировщика для выключения\n"
            "<blockquote>\n"
            "Активные планировщики:\n"
            f"{chr(10).join(settings_info)}\n"
            "</blockquote>"
        )
        
        await callback.message.delete()
        
        await callback.message.answer(
            text=message_text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        
        await state.set_state(DisableNotifyStates.waiting_for_name_off)
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при обработке выключения уведомлений: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@router.message(DisableNotifyStates.waiting_for_name_off)
async def process_disable_notify_name(message: Message, state: FSMContext):
    """Обработчик ввода наименования планировщика для выключения"""
    try:
        success = await db.update_notify_setting_by_name(message.text, is_enable=False)
        
        await message.delete()
        
        if success:
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🔙 Назад", callback_data="admin_user_sub_notification")]
            ])
            
            await message.answer(
                f"✅ Планировщик \"{message.text}\" успешно выключен!",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="admin_off_user_notify")]
            ])
            await message.answer(
                "❌ Планировщик с таким именем не найден или уже выключен",
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при выключении планировщика: {e}")
        await message.answer("Произошла ошибка при выключении планировщика")
        await state.clear()

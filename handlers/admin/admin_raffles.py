from aiogram import Router, F
from aiogram.types import CallbackQuery, FSInputFile, Message
from handlers.database import Database
from handlers.admin.admin_kb import get_admin_show_raffles_keyboard, get_admin_confirm_delete_raffle_keyboard, get_admin_users_keyboard_cancel
from datetime import datetime
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
import os
from aiogram.fsm.context import FSMContext
from handlers.admin.admin_states import RaffleState

router = Router()

@router.callback_query(F.data == "admin_show_raffles")
async def show_raffles(callback: CallbackQuery):
    """Показать активные розыгрыши"""
    db = Database()
    
    raffle = await db.execute_fetchone(
        "SELECT name, description, start_date FROM raffles WHERE status = 'active' ORDER BY start_date DESC LIMIT 1"
    )
    
    await callback.message.delete()
    
    if not raffle:
        await callback.message.answer(
            "В данный момент нет активных розыгрышей",
            reply_markup=get_admin_show_raffles_keyboard()
        )
        return
    
    start_date = datetime.strptime(raffle['start_date'], "%Y-%m-%d %H:%M:%S").strftime("%d.%m.%Y %H:%M")
    
    message_text = (
        "Активный розыгрыш\n"
        "<blockquote>"
        f"<b>Наименование:</b> {raffle['name']}\n"
        f"<b>Описание:</b> {raffle['description']}\n"
        f"<b>Дата создания:</b> {start_date}\n"
        "</blockquote>"
    )
    
    await callback.message.answer(
        message_text,
        parse_mode="HTML",
        reply_markup=get_admin_show_raffles_keyboard()
    )

@router.callback_query(F.data == "admin_delete_raffle")
async def delete_raffle_confirm(callback: CallbackQuery):
    """Подтверждение удаления розыгрыша"""
    await callback.message.edit_text(
        "Вы действительно хотите удалить текущий розыгрыш? 🎟️"
        "Кнопка с розыгрышем в главном меню пользователя также будет отключена. ❌",
        reply_markup=get_admin_confirm_delete_raffle_keyboard()
    )

@router.callback_query(F.data == "admin_confirm_delete_raffle")
async def delete_raffle(callback: CallbackQuery):
    """Удаление розыгрыша"""
    db = Database()
    
    if await db.deactivate_raffle():
        await callback.message.edit_text(
            "✅ Розыгрыш успешно удален!\n\n"
            "<b>Перед созданием нового розыгрыша, удалите все билеты</b>\n",
            parse_mode="HTML",
            reply_markup=get_admin_show_raffles_keyboard()
        )
    else:
        await callback.message.edit_text(
            "❌ Ошибка при удалении розыгрыша!\n"
            "<i>Пожалуйста, попробуйте позже</i>",
            parse_mode="HTML",
            reply_markup=get_admin_show_raffles_keyboard()
        )

def get_admin_confirm_delete_tickets_keyboard() -> InlineKeyboardBuilder:
    """Создание клавиатуры для подтверждения удаления билетов"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Подтвердить", callback_data="admin_confirm_delete_tickets")
    keyboard.button(text="❌ Отмена", callback_data="admin_show_raffles")
    keyboard.adjust(2)
    return keyboard.as_markup()

@router.callback_query(F.data == "admin_delete_tickets")
async def delete_tickets_confirm(callback: CallbackQuery):
    """Подтверждение удаления билетов"""
    await callback.message.edit_text(
        "⚠️ <b>Внимание!</b> Все билеты из базы данных будут удалены.\n"
        "<i>Это действие необратимо!</i>",
        parse_mode="HTML",
        reply_markup=get_admin_confirm_delete_tickets_keyboard()
    )

@router.callback_query(F.data == "admin_confirm_delete_tickets")
async def delete_tickets(callback: CallbackQuery):
    """Удаление всех билетов"""
    db = Database()
    
    if await db.delete_all_raffle_tickets():
        await callback.message.edit_text(
            "✅ Все билеты успешно удалены!",
            parse_mode="HTML",
            reply_markup=get_admin_show_raffles_keyboard()
        )
    else:
        await callback.message.edit_text(
            "❌ Ошибка при удалении билетов!\n"
            "<i>Пожалуйста, попробуйте позже</i>",
            parse_mode="HTML",
            reply_markup=get_admin_show_raffles_keyboard()
        )

@router.callback_query(F.data == "admin_save_tickets_to_file")
async def save_tickets_to_file(callback: CallbackQuery):
    """Сохранение билетов в файл"""
    db = Database()
    tickets_data = await db.get_tickets_report()
    
    if not tickets_data:
        await callback.message.edit_text(
            "❌ Нет данных о билетах",
            reply_markup=get_admin_show_raffles_keyboard()
        )
        return

    filename = f"raffle_tickets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    with open(filename, 'w', encoding='utf-8') as f:
        for user in tickets_data:
            f.write("-" * 50 + "\n")
            f.write(f"Имя пользователя: {user['username'] or 'Не указано'}\n")
            f.write(f"Телеграм ID: {user['telegram_id']}\n")
            f.write(f"Номера билетов: {user['tickets']}\n")
            f.write(f"Всего билетов: {user['tickets_count']}\n")
        f.write("-" * 50 + "\n")

    try:
        await callback.message.answer_document(
            FSInputFile(filename),
            caption="📄 Отчет по билетам розыгрыша",
            reply_markup=get_admin_users_keyboard_cancel()
        )
        os.remove(filename)
    except Exception as e:
        logger.error(f"Ошибка при отправке файла: {e}")
        await callback.message.edit_text(
            "❌ Ошибка при создании отчета",
            reply_markup=get_admin_users_keyboard_cancel()
        )

@router.callback_query(F.data == "admin_add_raffle")
async def add_raffle_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления розыгрыша"""
    await callback.message.edit_text(
        "Введите наименование для розыгрыша.\n"
        "Это наименование будет отображаться на кнопке в главном меню пользователя. 🎰✨"
    )
    await state.set_state(RaffleState.waiting_for_name)

@router.message(RaffleState.waiting_for_name)
async def process_raffle_name(message: Message, state: FSMContext):
    """Обработка введенного имени розыгрыша"""
    await state.update_data(raffle_name=message.text)
    
    await message.answer(
        "Введите описание для розыгрыша.\n"
        "Описание будет отображаться вместе с билетами пользователя в меню розыгрышей. 📝"
    )
    await state.set_state(RaffleState.waiting_for_description)

@router.message(RaffleState.waiting_for_description)
async def process_raffle_description(message: Message, state: FSMContext):
    """Обработка введенного описания розыгрыша"""
    data = await state.get_data()
    raffle_name = data.get("raffle_name")
    
    db = Database()
    if await db.create_raffle(raffle_name, message.text):
        await message.answer(
            "✅ Розыгрыш успешно создан!\n\n"
            f"<b>Наименование:</b> {raffle_name}\n"
            f"<b>Описание:</b> {message.text}",
            parse_mode="HTML",
            reply_markup=get_admin_show_raffles_keyboard()
        )
    else:
        await message.answer(
            "❌ Ошибка при создании розыгрыша!\n"
            "<i>Пожалуйста, попробуйте позже</i>",
            parse_mode="HTML",
            reply_markup=get_admin_show_raffles_keyboard()
        )
    
    await state.clear() 
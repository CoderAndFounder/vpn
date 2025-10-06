from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
from handlers.database import db
from handlers.admin.admin_kb import get_admin_referral_keyboard, get_admin_keyboard
from handlers.admin.admin_states import ReferralStates
import aiosqlite

router = Router()

@router.callback_query(F.data == "admin_show_referral")
async def show_referral_menu(event):
    """Показать меню управления реферальной программой"""
    try:
        conditions = await db.get_referral_conditions()
        
        message_text = "💰 Управление реферальной программой\n\n"
        message_text += "Текущие условия программы:\n"
        
        if conditions:
            for condition in conditions:
                status = "✅ Активно" if condition['is_enable'] else "❌ Отключено"
                message_text += (
                    f"\n<b>{condition['name']}</b> [{status}]\n"
                    f"<blockquote>"
                    f"Описание: {condition['description']}\n"
                    f"Требуется приглашений: {condition['invitations']}\n"
                    f"Награда: {condition['reward_sum']} руб.\n"
                    f"</blockquote>"
                )
        else:
            message_text += "\n❌ Нет настроенных условий"
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute("""
                SELECT 
                    COUNT(DISTINCT user_id) as total_users,
                    SUM(reward_sum) as total_rewards
                FROM referral_rewards_history
            """)
            stats = await cursor.fetchone()
            
            message_text += (
                f"\n📊 Статистика программы:\n"
                f"<blockquote>"
                f"Получили награды: {stats['total_users'] or 0} пользователей\n"
                f"Выплачено наград: {stats['total_rewards'] or 0:.2f} руб.\n"
                f"</blockquote>"
            )
        
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(
                message_text,
                reply_markup=get_admin_referral_keyboard(),
                parse_mode="HTML"
            )
        else:  
            await event.answer(
                message_text,
                reply_markup=get_admin_referral_keyboard(),
                parse_mode="HTML"
            )
        
    except Exception as e:
        logger.error(f"Ошибка при показе меню реферальной программы: {e}")
        error_text = "❌ Произошла ошибка при загрузке меню реферальной программы"
        
        if isinstance(event, CallbackQuery):
            await event.message.edit_text(error_text, reply_markup=get_admin_keyboard())
        else:
            await event.answer(error_text, reply_markup=get_admin_keyboard())

@router.callback_query(F.data == "admin_add_referral_condition")
async def start_add_condition(callback: CallbackQuery, state: FSMContext):
    """Начать добавление нового условия"""
    await callback.message.edit_text(
        "Введите название условия реферальной программы:",
        reply_markup=None
    )
    await state.set_state(ReferralStates.ADD_NAME)

@router.message(StateFilter(ReferralStates.ADD_NAME))
async def add_condition_name(message: Message, state: FSMContext):
    """Сохранить название и запросить описание"""
    await state.update_data(name=message.text)
    await message.answer("Введите описание условия:")
    await state.set_state(ReferralStates.ADD_DESCRIPTION)

@router.message(StateFilter(ReferralStates.ADD_DESCRIPTION))
async def add_condition_description(message: Message, state: FSMContext):
    """Сохранить описание и запросить количество приглашений"""
    await state.update_data(description=message.text)
    await message.answer("Введите необходимое количество приглашений (число):")
    await state.set_state(ReferralStates.ADD_INVITATIONS)

@router.message(StateFilter(ReferralStates.ADD_INVITATIONS))
async def add_condition_invitations(message: Message, state: FSMContext):
    """Сохранить количество приглашений и запросить сумму награды"""
    try:
        invitations = int(message.text)
        if invitations <= 0:
            raise ValueError("Количество должно быть положительным")
        
        await state.update_data(invitations=invitations)
        await message.answer("Введите сумму награды (число):")
        await state.set_state(ReferralStates.ADD_REWARD)
    except ValueError:
        await message.answer("Ошибка! Введите положительное целое число.")

@router.message(StateFilter(ReferralStates.ADD_REWARD))
async def add_condition_reward(message: Message, state: FSMContext):
    """Сохранить сумму награды и создать условие"""
    try:
        reward = float(message.text)
        if reward <= 0:
            raise ValueError("Сумма должна быть положительной")
        
        data = await state.get_data()
        
        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute("""
                INSERT INTO referral_condition (name, description, invitations, reward_sum)
                VALUES (?, ?, ?, ?)
            """, (data['name'], data['description'], data['invitations'], reward))
            await conn.commit()
        
        await state.clear()
        await message.answer(
            "✅ Новое условие реферальной программы успешно добавлено!",
            reply_markup=get_admin_referral_keyboard()
        )
        
        await show_referral_menu(message)
        
    except ValueError:
        await message.answer("Ошибка! Введите положительное число.")

@router.callback_query(F.data == "admin_edit_referral_condition")
async def start_edit_condition(callback: CallbackQuery, state: FSMContext):
    """Показать список условий для редактирования"""
    conditions = await db.get_referral_conditions()
    
    if not conditions:
        await callback.message.edit_text(
            "❌ Нет доступных условий для редактирования",
            reply_markup=get_admin_referral_keyboard()
        )
        return
    
    keyboard = InlineKeyboardBuilder()
    for condition in conditions:
        keyboard.button(
            text=f"{condition['name']} ({condition['invitations']} приг., {condition['reward_sum']} руб.)",
            callback_data=f"edit_condition_{condition['id']}"
        )
    keyboard.button(text="🔙 Назад", callback_data="admin_show_referral")
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        "Выберите условие для редактирования:",
        reply_markup=keyboard.as_markup()
    )

@router.callback_query(F.data.startswith("edit_condition_"))
async def select_edit_field(callback: CallbackQuery, state: FSMContext):
    """Выбор поля для редактирования"""
    condition_id = int(callback.data.split('_')[2])
    await state.update_data(condition_id=condition_id)
    
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Название", callback_data="edit_field_name")
    keyboard.button(text="Описание", callback_data="edit_field_description")
    keyboard.button(text="Кол-во приглашений", callback_data="edit_field_invitations")
    keyboard.button(text="Сумма награды", callback_data="edit_field_reward")
    #keyboard.button(text="Статус", callback_data="edit_field_status")
    keyboard.button(text="🔙 Назад", callback_data="admin_edit_referral_condition")
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        "Выберите поле для редактирования:",
        reply_markup=keyboard.as_markup()
    )

@router.callback_query(F.data.startswith("edit_field_"))
async def edit_field_value(callback: CallbackQuery, state: FSMContext):
    """Запросить новое значение для поля"""
    field = callback.data.split('_')[2]
    await state.update_data(edit_field=field)
    
    if field == "status":
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="✅ Включить", callback_data="set_status_1")
        keyboard.button(text="❌ Отключить", callback_data="set_status_0")
        keyboard.button(text="🔙 Назад", callback_data="admin_edit_referral_condition")
        keyboard.adjust(1)
        
        await callback.message.edit_text(
            "Выберите новый статус:",
            reply_markup=keyboard.as_markup()
        )
    else:
        field_names = {
            "name": "название",
            "description": "описание",
            "invitations": "количество приглашений",
            "reward": "сумму награды"
        }
        await callback.message.edit_text(
            f"Введите новое {field_names[field]}:",
            reply_markup=None
        )
        await state.set_state(ReferralStates.EDIT_VALUE)

@router.callback_query(F.data == "admin_delete_referral_condition")
async def start_delete_condition(callback: CallbackQuery, state: FSMContext):
    """Показать список условий для удаления"""
    conditions = await db.get_referral_conditions()
    
    if not conditions:
        await callback.message.edit_text(
            "❌ Нет доступных условий для удаления",
            reply_markup=get_admin_referral_keyboard()
        )
        return
    
    keyboard = InlineKeyboardBuilder()
    for condition in conditions:
        keyboard.button(
            text=f"❌ {condition['name']}", 
            callback_data=f"delete_condition_{condition['id']}"
        )
    keyboard.button(text="🔙 Назад", callback_data="admin_show_referral")
    keyboard.adjust(1)
    
    await callback.message.edit_text(
        "⚠️ Выберите условие для удаления:\n"
        "<i>Внимание: это действие нельзя отменить!</i>",
        reply_markup=keyboard.as_markup(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("delete_condition_"))
async def confirm_delete_condition(callback: CallbackQuery):
    """Удалить выбранное условие"""
    condition_id = int(callback.data.split('_')[2])
    
    async with aiosqlite.connect(db.db_path) as conn:
        await conn.execute(
            "DELETE FROM referral_condition WHERE id = ?",
            (condition_id,)
        )
        await conn.commit()
    
    await callback.message.edit_text(
        "✅ Условие успешно удалено!",
        reply_markup=get_admin_referral_keyboard()
    )
    
    await show_referral_menu(callback)

@router.message(StateFilter(ReferralStates.EDIT_VALUE))
async def process_edit_value(message: Message, state: FSMContext):
    """Обработка нового значения поля"""
    try:
        data = await state.get_data()
        condition_id = data['condition_id']
        field = data['edit_field']
        value = message.text

        if field == "invitations":
            value = int(value)
            if value <= 0:
                raise ValueError("Количество должно быть положительным")
            db_field = "invitations"
        elif field == "reward":
            value = float(value)
            if value <= 0:
                raise ValueError("Сумма должна быть положительной")
            db_field = "reward_sum"
        elif field == "name":
            if not value.strip():
                raise ValueError("Название не может быть пустым")
            db_field = "name"
        elif field == "description":
            db_field = "description"
        else:
            raise ValueError("Неизвестное поле")

        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute(f"""
                UPDATE referral_condition 
                SET {db_field} = ?
                WHERE id = ?
            """, (value, condition_id))
            await conn.commit()

        await state.clear()
        await message.answer(
            "✅ Значение успешно обновлено!",
            reply_markup=get_admin_referral_keyboard()
        )
        
        await show_referral_menu(message)

    except ValueError as e:
        await message.answer(f"❌ Ошибка: {str(e)}")
    except Exception as e:
        logger.error(f"Ошибка при обновлении значения: {e}")
        await message.answer(
            "❌ Произошла ошибка при обновлении значения",
            reply_markup=get_admin_referral_keyboard()
        )

@router.callback_query(F.data.startswith("set_status_"))
async def update_condition_status(callback: CallbackQuery, state: FSMContext):
    """Обновление статуса условия"""
    try:
        data = await state.get_data()
        condition_id = data['condition_id']
        new_status = int(callback.data.split('_')[2])  # 0 или 1

        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute("""
                UPDATE referral_condition 
                SET is_enable = ?
                WHERE id = ?
            """, (new_status, condition_id))
            await conn.commit()

        await state.clear()
        await callback.message.edit_text(
            "✅ Статус успешно обновлен!",
            reply_markup=get_admin_referral_keyboard()
        )
        
        await show_referral_menu(callback)

    except Exception as e:
        logger.error(f"Ошибка при обновлении статуса: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при обновлении статуса",
            reply_markup=get_admin_referral_keyboard()
        )


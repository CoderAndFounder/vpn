from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
import aiosqlite

from handlers.database import db
from handlers.admin.admin_kb import get_servers_keyboard

router = Router()

class ServerDeleteStates(StatesGroup):
    waiting_for_confirmation = State()

async def get_server_list_keyboard():
    """Создание клавиатуры со списком серверов"""
    keyboard = InlineKeyboardBuilder()
    
    async with aiosqlite.connect(db.db_path) as conn:
        conn.row_factory = aiosqlite.Row
        cursor = await conn.execute(
            "SELECT id, name FROM server_settings WHERE is_enable = 1"
        )
        servers = await cursor.fetchall()
    
    for server in servers:
        keyboard.button(
            text=server['name'],
            callback_data=f"delete_server:{server['id']}"
        )
    
    keyboard.button(text="🔙 Отмена", callback_data="servers_back_to_admin")
    keyboard.adjust(1)
    return keyboard.as_markup()

def get_confirmation_keyboard(server_id: int):
    """Создание клавиатуры подтверждения удаления"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(
        text="✅ Подтвердить",
        callback_data=f"confirm_delete_server:{server_id}"
    )
    keyboard.button(
        text="❌ Отмена",
        callback_data="cancel_delete_server"
    )
    keyboard.adjust(2)
    return keyboard.as_markup()

@router.callback_query(F.data == "delete_server")
async def start_server_delete(callback: CallbackQuery):
    """Начало процесса удаления сервера"""
    try:
        if not await db.is_admin(callback.from_user.id):
            await callback.answer("У вас нет прав для выполнения этого действия")
            return

        await callback.message.edit_text(
            "🗑 Выберите сервер для удаления:",
            reply_markup=await get_server_list_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка при начале удаления сервера: {e}")
        await callback.message.edit_text(
            "Произошла ошибка. Попробуйте позже.",
            reply_markup=get_servers_keyboard()
        )

@router.callback_query(F.data.startswith("delete_server:"))
async def confirm_server_delete(callback: CallbackQuery, state: FSMContext):
    """Подтверждение удаления выбранного сервера"""
    try:
        server_id = int(callback.data.split(':')[1])
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            cursor = await conn.execute(
                "SELECT name FROM server_settings WHERE id = ?",
                (server_id,)
            )
            server = await cursor.fetchone()
            
            if not server:
                await callback.answer("Сервер не найден", show_alert=True)
                return
            
            await state.update_data(server_id=server_id, server_name=server['name'])
            
            await callback.message.edit_text(
                f"❗️ Вы выбрали сервер «{server['name']}» для удаления\n"
                "⚠️ Это действие нельзя отменить!\n"
                "Все связанные тарифы будут отключены.",
                reply_markup=get_confirmation_keyboard(server_id)
            )
            
            await state.set_state(ServerDeleteStates.waiting_for_confirmation)
            
    except Exception as e:
        logger.error(f"Ошибка при подтверждении удаления сервера: {e}")
        await callback.answer("Произошла ошибка", show_alert=True)

@router.callback_query(F.data.startswith("confirm_delete_server:"))
async def process_delete_server(callback: CallbackQuery, state: FSMContext):
    """Процесс удаления сервера после подтверждения"""
    try:
        data = await state.get_data()
        server_id = data.get('server_id')
        server_name = data.get('server_name')
        
        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute(
                "UPDATE tariff SET is_enable = 0 WHERE server_id = ?",
                (server_id,)
            )
            
            cursor = await conn.execute(
                "SELECT COUNT(*) FROM tariff WHERE server_id = ?",
                (server_id,)
            )
            disabled_tariffs_count = (await cursor.fetchone())[0]
            
            await conn.execute(
                "DELETE FROM server_settings WHERE id = ?",
                (server_id,)
            )
            await conn.commit()
        
        success_message = (
            f"✅ Сервер «{server_name}» успешно удален\n"
            f"📊 Отключено тарифов: {disabled_tariffs_count}"
        )
        
        await callback.message.edit_text(
            success_message,
            reply_markup=get_servers_keyboard()
        )
        
        logger.info(f"Удален сервер {server_name} (ID: {server_id}) и {disabled_tariffs_count} тарифов")
        
    except Exception as e:
        logger.error(f"Ошибка при удалении сервера: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при удалении сервера",
            reply_markup=get_servers_keyboard()
        )
    finally:
        await state.clear()

@router.callback_query(F.data == "cancel_delete_server")
async def cancel_delete_server(callback: CallbackQuery, state: FSMContext):
    """Отмена удаления сервера"""
    await state.clear()
    await callback.message.edit_text(
        "❌ Удаление сервера отменено",
        reply_markup=get_servers_keyboard()
    ) 
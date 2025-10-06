from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from loguru import logger
import aiosqlite

from handlers.database import db
from handlers.admin.admin_kb import get_servers_keyboard

router = Router()

class ServerAddStates(StatesGroup):
    waiting_for_url = State()
    waiting_for_port = State()
    waiting_for_protocol = State()
    waiting_for_inbound = State()
    waiting_for_path = State()
    waiting_for_login = State()
    waiting_for_password = State()
    waiting_for_name = State()

@router.callback_query(F.data == "add_server")
async def start_server_add(callback: CallbackQuery, state: FSMContext):
    """Начало процесса добавления сервера"""
    try:
        if not await db.is_admin(callback.from_user.id):
            await callback.answer("У вас нет прав для выполнения этого действия")
            return

        await callback.message.delete()
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="🔙 Отмена", callback_data="cancel_add_server")
        
        await callback.message.answer(
            "🌐 Введите URL сервера 3x-ui, который начинается с https:// \n"
            "Пример: https://3xui.example.com 🔑",
            reply_markup=keyboard.as_markup()
        )
        
        await state.set_state(ServerAddStates.waiting_for_url)
        
    except Exception as e:
        logger.error(f"Ошибка при начале добавления сервера: {e}")
        await callback.message.answer("Произошла ошибка. Попробуйте позже.")

@router.message(ServerAddStates.waiting_for_url)
async def process_url(message: Message, state: FSMContext):
    """Обработка введенного URL"""
    url = message.text.strip()
    if not url.startswith('https://'):
        await message.answer("URL должен начинаться с https://\nПопробуйте еще раз:")
        return

    await state.update_data(url=url)
    
    await message.answer(
        f"Вы ввели {url}\n"
        "Теперь укажите порт по которому доступна панель:"
    )
    await state.set_state(ServerAddStates.waiting_for_port)

@router.message(ServerAddStates.waiting_for_port)
async def process_port(message: Message, state: FSMContext):
    """Обработка введенного порта"""
    try:
        port = int(message.text.strip())
        data = await state.get_data()
        
        await state.update_data(port=port)
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="VLESS", callback_data="protocol_vless")
        keyboard.button(text="SHADOWSOCKS", callback_data="protocol_shadowsocks")
        keyboard.adjust(2)
        
        await message.answer(
            f"Вы ввели {data['url']}:{port}\n"
            "Выберите протокол:",
            reply_markup=keyboard.as_markup()
        )
        await state.set_state(ServerAddStates.waiting_for_protocol)
    except ValueError:
        await message.answer("Порт должен быть числом\nПопробуйте еще раз:")

@router.callback_query(F.data.startswith("protocol_"))
async def process_protocol(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора протокола"""
    protocol = callback.data.split('_')[1]  # получаем vless или shadowsocks
    data = await state.get_data()
    
    await state.update_data(protocol=protocol)
    
    await callback.message.edit_text(
        f"Вы ввели {data['url']}:{data['port']} (протокол: {protocol.upper()})\n"
        "Теперь укажите ID входящего соединения (inbound_id).\n"
        "Это число, которое можно найти в панели 3x-ui в списке входящих соединений:"
    )
    await state.set_state(ServerAddStates.waiting_for_inbound)

@router.message(ServerAddStates.waiting_for_inbound)
async def process_inbound(message: Message, state: FSMContext):
    """Обработка введенного inbound_id"""
    try:
        inbound_id = int(message.text.strip())
        data = await state.get_data()
        
        await state.update_data(inbound_id=inbound_id)
        
        await message.answer(
            f"Вы ввели {data['url']}:{data['port']} (протокол: {data['protocol']})\n"
            "Теперь введите секретный путь панели, к примеру для https://3xui.example.com/secret_path\n"
            "здесь путь это secret_path"
        )
        await state.set_state(ServerAddStates.waiting_for_path)
    except ValueError:
        await message.answer("ID входящего соединения должен быть числом\nПопробуйте еще раз:")

@router.message(ServerAddStates.waiting_for_path)
async def process_path(message: Message, state: FSMContext):
    """Обработка введенного пути"""
    path = message.text.strip().lstrip('/')
    data = await state.get_data()
    
    await state.update_data(path=path)
    
    await message.answer(
        f"Вы ввели {data['url']}:{data['port']}/{path}\n"
        "Теперь укажите Логин:"
    )
    await state.set_state(ServerAddStates.waiting_for_login)

@router.message(ServerAddStates.waiting_for_login)
async def process_login(message: Message, state: FSMContext):
    """Обработка введенного логина"""
    login = message.text.strip()
    data = await state.get_data()
    
    await state.update_data(login=login)
    
    await message.answer(
        f"Вы ввели {data['url']}:{data['port']}/{data['path']}\n"
        f"Логин для подключения: {login}\n"
        "Пришли мне пароль:"
    )
    await state.set_state(ServerAddStates.waiting_for_password)

@router.message(ServerAddStates.waiting_for_password)
async def process_password(message: Message, state: FSMContext):
    """Обработка введенного пароля"""
    password = message.text.strip()
    
    await state.update_data(password=password)
    
    await message.answer(
        "Отлично, мы почти закончили. Осталось добавить имя,\n"
        "введи наименование сервера (Рекомендуется указывать страну,\n"
        "где он находится, это будет отображено в тарифном плане в поле Страна):"
    )
    await state.set_state(ServerAddStates.waiting_for_name)

@router.message(ServerAddStates.waiting_for_name)
async def process_name(message: Message, state: FSMContext):
    """Обработка введенного имени и сохранение сервера"""
    try:
        name = message.text.strip()
        data = await state.get_data()
        
        async with aiosqlite.connect(db.db_path) as conn:
            await conn.execute("""
                INSERT INTO server_settings 
                (url, port, secret_path, username, password, name, inbound_id, protocol, is_enable)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (data['url'], data['port'], data['path'], data['login'], 
                  data['password'], name, data['inbound_id'], data['protocol']))
            await conn.commit()
        
        await message.answer(
            f"Сервер {name} успешно добавлен, теперь можно создать тарифный план для него!",
            reply_markup=get_servers_keyboard()
        )
        logger.info(f"Добавлен новый сервер: {name} с протоколом {data['protocol']}")
        
    except Exception as e:
        logger.error(f"Ошибка при сохранении сервера: {e}")
        await message.answer(
            "Произошла ошибка при сохранении сервера. Попробуйте позже.",
            reply_markup=get_servers_keyboard()
        )
    finally:
        await state.clear()

@router.callback_query(F.data == "cancel_add_server")
async def cancel_add_server(callback: CallbackQuery, state: FSMContext):
    """Отмена добавления сервера"""
    await state.clear()
    await callback.message.edit_text(
        "Добавление сервера отменено",
        reply_markup=get_servers_keyboard()
    ) 
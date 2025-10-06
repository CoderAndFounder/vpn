from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import aiosqlite
import re
from loguru import logger
import py3xui

from handlers.database import db
from handlers.admin.admin_kb import get_admin_users_keyboard, get_admin_users_keyboard_cancel

router = Router()

class UserBanStates(StatesGroup):
    waiting_for_username = State()
    confirm_ban = State()

def get_cancel_keyboard():
    """Создание клавиатуры с кнопкой отмены"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="Отмена", callback_data="cancel_ban")
    return keyboard.as_markup()

def get_confirm_keyboard():
    """Создание клавиатуры подтверждения"""
    keyboard = InlineKeyboardBuilder()
    keyboard.button(text="✅ Да", callback_data="confirm_ban")
    keyboard.button(text="❌ Нет", callback_data="cancel_ban")
    keyboard.adjust(2)
    return keyboard.as_markup()

@router.callback_query(F.data == "ban_user")
async def process_ban_user(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки блокировки пользователя"""
    try:
        await callback.message.delete()
        await callback.message.answer(
            "Введите имя пользователя без @",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(UserBanStates.waiting_for_username)
    except Exception as e:
        logger.error(f"Ошибка при начале процесса блокировки: {e}")
        await callback.message.answer(
            "Произошла ошибка. Попробуйте позже.",
            reply_markup=get_admin_users_keyboard()
        )

@router.message(UserBanStates.waiting_for_username)
async def process_username_input(message: Message, state: FSMContext):
    """Обработчик ввода имени пользователя"""
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute(
                "SELECT * FROM user WHERE username = ?",
                (message.text,)
            ) as cursor:
                user = await cursor.fetchone()

        if not user:
            await message.answer(
                "❌ Пользователь не найден",
                reply_markup=get_admin_users_keyboard()
            )
            await state.clear()
            return

        await state.update_data(user_data=dict(user))

        await message.answer(
            f"Вы собираетесь заблокировать пользователя:\n\n"
            f"Имя пользователя: @{user['username']}\n"
            f"Дата регистрации: {user['date']}\n\n"
            f"❌ Это действие необратимо и удалит все подписки пользователя с северов а так же заблокирует его в боте\n",
            reply_markup=get_confirm_keyboard()
        )
        await state.set_state(UserBanStates.confirm_ban)

    except Exception as e:
        logger.error(f"Ошибка при поиске пользователя: {e}")
        await message.answer(
            "Произошла ошибка при поиске пользователя",
            reply_markup=get_admin_users_keyboard()
        )
        await state.clear()

@router.callback_query(F.data == "confirm_ban")
async def process_confirm_ban(callback: CallbackQuery, state: FSMContext):
    """Обработчик подтверждения блокировки"""
    try:
        user_data = (await state.get_data())['user_data']
        logger.info(f"Начало процесса блокировки пользователя: {user_data['username']}")
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("""
                SELECT us.*, ss.url, ss.port, ss.username, ss.password, ss.inbound_id, ss.secret_path
                FROM user_subscription us
                JOIN server_settings ss ON us.server_id = ss.id
                WHERE us.user_id = ? AND us.is_active = 1
            """, (user_data['telegram_id'],)) as cursor:
                subscriptions = await cursor.fetchall()
                logger.info(f"Найдено активных подписок: {len(subscriptions)}")

        for sub in subscriptions:
            try:
                logger.info(f"Обработка подписки: {sub['vless']}")
                
                uuid_match = re.search(r'vless://([^@]+)@', sub['vless'])
                if not uuid_match:
                    logger.error(f"Не удалось извлечь UUID из строки vless: {sub['vless']}")
                    continue
                client_uuid = uuid_match.group(1)
                logger.info(f"Извлечен UUID: {client_uuid}")

                api_url = f"{sub['url']}:{sub['port']}/{sub['secret_path']}"
                
                api = py3xui.AsyncApi(
                    host=api_url,
                    username=sub['username'],
                    password=sub['password'],
                    use_tls_verify=False
                )
                logger.info(f"Подключаемся к API: {api_url}")
                await api.login()
                logger.info("Успешно подключились к API")

                logger.info(f"Попытка удаления пользователя. inbound_id: {sub['inbound_id']}, uuid: {client_uuid}")
                await api.client.delete(sub['inbound_id'], client_uuid)
                logger.info(f"Пользователь успешно удален с сервера {api_url} (inbound_id: {sub['inbound_id']})")

            except Exception as e:
                logger.error(f"Ошибка при удалении с сервера {api_url}: {e}")
                logger.error(f"Детали ошибки: {str(e)}")
                logger.error(f"Параметры подключения: URL={api_url}, inbound_id={sub['inbound_id']}, uuid={client_uuid}")

        try:
            async with aiosqlite.connect(db.db_path) as conn:
                await conn.execute(
                    "UPDATE user_subscription SET is_active = 0 WHERE user_id = ?",
                    (user_data['telegram_id'],)
                )
                await conn.execute(
                    "UPDATE user SET is_enable = 0 WHERE telegram_id = ?",
                    (user_data['telegram_id'],)
                )
                await conn.commit()
                logger.info(f"Все подписки пользователя деактивированы и пользователь заблокирован: {user_data['telegram_id']}")
        except Exception as e:
            logger.error(f"Ошибка при деактивации подписок и блокировке пользователя: {e}")

        await callback.message.edit_text(
            f"✅ Пользователь @{user_data['username']} успешно заблокирован",
            reply_markup=get_admin_users_keyboard()
        )
        logger.info(f"Процесс блокировки пользователя {user_data['username']} завершен")

    except Exception as e:
        logger.error(f"Критическая ошибка при блокировке пользователя: {e}")
        logger.exception("Полный стек ошибки:")
        await callback.message.edit_text(
            "Произошла ошибка при блокировке пользователя",
            reply_markup=get_admin_users_keyboard()
        )
    finally:
        await state.clear()

@router.callback_query(F.data == "cancel_ban")
async def process_cancel_ban(callback: CallbackQuery, state: FSMContext):
    """Обработчик отмены блокировки"""
    try:
        await callback.message.edit_text(
            "Операция отменена",
            reply_markup=get_admin_users_keyboard_cancel()
        )
    except Exception as e:
        logger.error(f"Ошибка при отмене блокировки: {e}")
        await callback.message.edit_text(
            "Произошла ошибка",
            reply_markup=get_admin_users_keyboard()
        )
    finally:
        await state.clear() 
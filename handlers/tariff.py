from aiogram import Router, F, types
from aiogram.types import CallbackQuery
from aiogram.utils.keyboard import InlineKeyboardBuilder
from asyncio import Lock
from handlers.database import db
from loguru import logger
import aiosqlite
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from handlers.promocode import promo_manager
from handlers.yookassa import yookassa_manager
from handlers.buy_subscribe import subscription_manager
from handlers.user.user_kb import get_trial_vless_keyboard, get_success_by_keyboard, get_start_keyboard
import os
from aiogram.types import FSInputFile

router = Router()

class PromoCodeStates(StatesGroup):
    waiting_for_promo = State()

payment_locks = {}

@router.callback_query(F.data == "start_tariffs")
async def show_tariffs(callback: CallbackQuery):
    try:
        await callback.message.delete()
        
        tariffs = await db.get_active_tariffs()
        if not tariffs:
            await callback.message.answer("В данный момент нет доступных тарифов.")
            return

        tariffs_text = "Ознакомьтесь с тарифными планами нашего сервиса:\n\n"
        for tariff in tariffs:
            tariffs_text += (
                f"<blockquote>"
                f"<b>Тарифный план:</b> {tariff['name']}\n"
                f"<b>Описание:</b> {tariff['description']}\n"
                f"<b>Стоимость:</b> {tariff['price']} руб.\n"
                f"<b>Страна:</b> {tariff['server_name']}\n"
                f"<b>Срок действия:</b> {tariff['left_day']} дней\n"
                f"</blockquote>\n"
            )

        keyboard = InlineKeyboardBuilder()
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("""
                SELECT DISTINCT s.id, s.name 
                FROM server_settings s
                JOIN tariff t ON s.id = t.server_id
                WHERE t.is_enable = 1
            """) as cursor:
                servers = await cursor.fetchall()

        for server in servers:
            keyboard.button(
                text=f"{server['name']}", 
                callback_data=f"user_select_server:{server['id']}"
            )
        keyboard.button(text="🔙 Назад", callback_data="tariff_back_to_start")
        keyboard.adjust(2, 1)

        message_data = await db.get_bot_message('tariff_message')
        
        if message_data and message_data['image_path'] and os.path.exists(message_data['image_path']):
            full_text = message_data['text'] + "\n\n" + tariffs_text
            await callback.message.answer_photo(
                photo=FSInputFile(message_data['image_path']),
                caption=full_text,
                reply_markup=keyboard.as_markup(),
                parse_mode="HTML"
            )
        else:
            await callback.message.answer(
                text=tariffs_text,
                reply_markup=keyboard.as_markup(),
                parse_mode="HTML"
            )

    except Exception as e:
        logger.error(f"Ошибка при отображении тарифов: {e}")
        await callback.message.answer("Произошла ошибка при загрузке тарифов. Попробуйте позже.")

    finally:
        await callback.answer()

@router.callback_query(F.data.startswith("select_tariff:"))
async def process_tariff_selection(callback: CallbackQuery):
    """Обработчик выбора тарифа"""
    try:
        await callback.message.delete()
        
        tariff_id = int(callback.data.split(":")[1])
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("""
                SELECT t.*, s.name as server_name 
                FROM tariff t 
                INNER JOIN server_settings s ON t.server_id = s.id 
                WHERE t.id = ? AND t.is_enable = 1
            """, (tariff_id,)) as cursor:
                tariff = await cursor.fetchone()
                
        if not tariff:
            await callback.message.answer("Выбранный тариф недоступен.")
            return
            
        message_text = (
            f"Выберите способ оплаты:\n"
            f"<blockquote>"
            f"<b>Тарифный план:</b> {tariff['name']}\n"
            f"<b>Описание:</b> {tariff['description']}\n"
            f"<b>Стоимость:</b> {tariff['price']} руб.\n"
            f"<b>Страна:</b> {tariff['server_name']}\n"
            f"<b>Сроком на:</b> {tariff['left_day']} дней.\n"
            f"💡 Вы можете применить промокод, чтобы сэкономить деньги.\n"
            f"</blockquote>\n"
        )
        
        keyboard = InlineKeyboardBuilder()
        is_yookassa_active = await db.is_yookassa_enabled()
        
        is_crypto_active = await db.is_crypto_enabled()
        
        
        if is_yookassa_active:
            keyboard.button(text="🔵 ЮКасса", callback_data=f"create_invoice:{tariff_id}")
        if is_crypto_active:
            keyboard.button(text="🪙 CryptoBot", callback_data=f"apply_crypto_payments:{tariff_id}")
        keyboard.button(text="💲 Оплатить с баланса", callback_data=f"apply_balance:{tariff_id}")
        keyboard.button(text="🎫 Применить промокод", callback_data=f"apply_promo_code:{tariff_id}")
        keyboard.button(text="💵 Оплатить кодом-оплаты", callback_data=f"apply_payments_code:{tariff_id}")
        keyboard.button(text="🔙 Отмена", callback_data="tariff_back_to_start")
        keyboard.adjust(2, 1)  
        
        await callback.message.answer(
            text=message_text,
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML"
        )
        
    except Exception as e:
        logger.error(f"Ошибка при выборе тарифа: {e}")
        await callback.message.answer("Произошла ошибка при выборе тарифа. Попробуйте позже.")
    finally:
        await callback.answer()

@router.callback_query(F.data.startswith("create_invoice:"))
async def process_create_invoice(callback: CallbackQuery, state: FSMContext):
    """Обработчик создания счета"""
    try:
        data = callback.data.split(":")
        tariff_id = int(data[1])
        promo_code = data[2] if len(data) > 2 else None
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("""
                SELECT t.*, s.name as server_name 
                FROM tariff t 
                INNER JOIN server_settings s ON t.server_id = s.id 
                WHERE t.id = ? AND t.is_enable = 1
            """, (tariff_id,)) as cursor:
                tariff = await cursor.fetchone()

        if not tariff:
            await callback.answer("Тариф недоступен")
            return

        price = float(tariff['price'])
        if promo_code:
            async with aiosqlite.connect(db.db_path) as conn:
                async with conn.execute("""
                    SELECT percentage 
                    FROM promocodes 
                    WHERE promocod = ? AND is_enable = 1 
                    AND activation_total < activation_limit
                """, (promo_code,)) as cursor:
                    promo = await cursor.fetchone()
                    if promo:
                        percentage = promo[0]
                        discount = price * (percentage / 100)
                        price = price - discount

        payment_id, payment_url = await yookassa_manager.create_payment(
            amount=price,
            description=f"Оплата тарифа {tariff['name']}",
            user_id=str(callback.from_user.id),
            tariff_name=tariff['name']
        )

        if not payment_id or not payment_url:
            await callback.message.answer("Ошибка при создании платежа. Попробуйте позже.")
            return

        await state.update_data(payment_id=payment_id, tariff_id=tariff_id)

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="💰 Оплатить", url=payment_url)
        keyboard.button(text="🕵️‍♂️ Проверить платеж", callback_data=f"check_payment:{payment_id}")
        keyboard.button(text="🔙 Отмена", callback_data="tariff_back_to_start")
        keyboard.adjust(1)

        await callback.message.delete()
        await callback.message.answer(
            "💡 *Ваш счет готов!*\n\n"
            "👇 *Нажмите на кнопку ниже, чтобы быстро и безопасно оплатить счет.* Мы используем надежные платежные системы, чтобы ваша транзакция прошла без задержек и была защищена.\n\n"
            "💰 Завершите оплату и нажмите кнопку 🕵️‍♂️ *Проверить платеж*, что бы получить доступ к вашему сервису в считанные минуты! Если у Вас возникнут вопросы, наша поддержка всегда готова помочь 🤝",
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )


    except Exception as e:
        logger.error(f"Ошибка при создании счета: {e}")
        await callback.message.answer("Произошла ошибка при создании счета. Попробуйте позже.")

@router.callback_query(F.data.startswith("check_payment:"))
async def check_payment(callback: CallbackQuery, state: FSMContext):
    """Обработчик проверки платежа"""
    try:
        payment_id = callback.data.split(":")[1]
        
        if payment_id not in payment_locks:
            payment_locks[payment_id] = Lock()
        
        if not payment_locks[payment_id].locked():
            async with payment_locks[payment_id]:
                async with aiosqlite.connect(db.db_path) as conn:
                    async with conn.execute(
                        'SELECT id FROM user_subscription WHERE payment_id = ?',
                        (payment_id,)
                    ) as cursor:
                        if await cursor.fetchone():
                            await callback.answer("Платеж уже был обработан и подписка активирована!", show_alert=True)
                            return

                is_paid = await yookassa_manager.check_payment(payment_id, bot=callback.bot)
                
                if not is_paid:
                    await callback.answer("Платеж еще не оплачен. Попробуйте проверить позже.")
                    return

                data = await state.get_data()
                tariff_id = data.get('tariff_id')
                
                if 'promo_code' in data:
                    success, message_text, _ = await promo_manager.apply_promo_code(
                        data['promo_code'], 
                        data['original_price']
                    )
                    if not success:
                        logger.warning(f"Ошибка при применении промокода после оплаты: {message_text}")

                subscription = await subscription_manager.create_subscription(
                    user_id=callback.from_user.id,
                    tariff_id=tariff_id,
                    payment_id=payment_id,  
                    bot=callback.bot
                )

                if not subscription:
                    await callback.message.answer("Ошибка при активации подписки. Обратитесь в поддержку.")
                    return

                async with aiosqlite.connect(db.db_path) as conn:
                    async with conn.execute(
                        'SELECT price FROM tariff WHERE id = ?',
                        (tariff_id,)
                    ) as cursor:
                        tariff = await cursor.fetchone()
                        if tariff:
                            await conn.execute("""
                                INSERT INTO payments (user_id, tariff_id, price)
                                VALUES (?, ?, ?)
                            """, (
                                callback.from_user.id,
                                tariff_id,
                                tariff[0]
                            ))
                            await conn.commit()

                message_text = (
                    "🎉 Поздравляем! Ваша подписка активирована!\n\n"
                    f"<blockquote>"
                    f"<b>Тариф:</b> {subscription['tariff']['name']}\n"
                    f"<b>Действует до:</b> {subscription['end_date'].strftime('%d.%m.%Y')}\n"
                    f"</blockquote>"
                    "Для подключения используйте следующую ссылку:\n\n"
                    "<blockquote>"
                    f"<code>{subscription['vless']}</code>\n"
                    "</blockquote>\n"
                    "⚠️ Сохраните эту ссылку, она потребуется для настройки приложения.\n"
                    "Инструкции по настройке Вы найдете в личном кабинете."
                )

                await callback.message.delete()
                await callback.message.answer(
                    text=message_text,
                    reply_markup=get_success_by_keyboard(),
                    parse_mode="HTML"
                )

                await state.clear()
        else:
            await callback.answer("Платеж обрабатывается, пожалуйста подождите...", show_alert=True)
            return

    except Exception as e:
        logger.error(f"Ошибка при проверке платежа: {e}")
        await callback.answer(
            "Произошла ошибка при проверке платежа",
            show_alert=True
        )
    finally:
        if payment_id in payment_locks and not payment_locks[payment_id].locked():
            del payment_locks[payment_id]

@router.callback_query(F.data == "tariff_back_to_start")
async def process_back_to_start(callback: CallbackQuery):
    """Обработчик кнопки Назад"""
    try:
        from handlers.commands import start_command
        await callback.message.delete()
        await start_command(callback.message)
    except Exception as e:
        logger.error(f"Ошибка при возврате в главное меню: {e}")
        await callback.answer("Произошла ошибка при возврате в главное меню")

@router.callback_query(F.data.startswith("apply_promo_code:"))
async def process_promo_code_button(callback: CallbackQuery, state: FSMContext):
    """Обработчик кнопки применения промокода"""
    try:
        tariff_id = int(callback.data.split(":")[1])
        await state.update_data(tariff_id=tariff_id)
        
        await callback.message.delete()
        
        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="Отмена", callback_data=f"select_tariff:{tariff_id}")
        
        await callback.message.answer(
            "Отправь мне промокод и я пересчитаю тарифный план с учетом скидки:",
            reply_markup=keyboard.as_markup()
        )
        
        await state.set_state(PromoCodeStates.waiting_for_promo)
        
    except Exception as e:
        logger.error(f"Ошибка при обработке кнопки промокода: {e}")
        await callback.message.answer("Произошла ошибка. Попробуйте позже.")

@router.message(PromoCodeStates.waiting_for_promo)
async def process_promo_code(message: types.Message, state: FSMContext):
    """Обработчик ввода промокода"""
    try:
        is_valid, message_text, percentage = await promo_manager.check_promo_code(message.text)
        
        if not is_valid:
            keyboard = InlineKeyboardBuilder()
            keyboard.button(text="🔙 Назад", callback_data="start_tariffs")
            await message.answer(
                message_text,
                reply_markup=keyboard.as_markup()
            )
            await state.clear()
            return

        data = await state.get_data()
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("""
                SELECT t.*, s.name as server_name 
                FROM tariff t
                JOIN server_settings s ON t.server_id = s.id
                WHERE t.id = ?
            """, (data['tariff_id'],)) as cursor:
                tariff = await cursor.fetchone()
                if tariff:
                    tariff = dict(tariff)

        if not tariff:
            await message.answer("Тариф не найден")
            await state.clear()
            return

        discount = tariff['price'] * (percentage / 100)
        new_price = tariff['price'] - discount

        await state.update_data(
            promo_code=message.text,
            original_price=tariff['price'],
            discount_price=new_price
        )

        payment_id, payment_url = await yookassa_manager.create_payment(
            amount=float(new_price),
            description=f"Оплата тарифа {tariff['name']} со скидкой {percentage}%",
            user_id=str(message.from_user.id),
            tariff_name=tariff['name']
        )

        if not payment_id or not payment_url:
            await message.answer("Ошибка при создании платежа. Попробуйте позже.")
            return

        message_text = (
            f"Вы выбрали:\n"
            f"<blockquote>"
            f"<b>Тарифный план:</b> {tariff['name']}\n"
            f"<b>Описание:</b> {tariff['description']}\n"
            f"<b>Страна:</b> {tariff['server_name']}\n"
            f"<b>Сроком на:</b> {tariff['left_day']} дней.\n"
            f"<b>Базовая стоимость:</b> {tariff['price']} руб.\n"
            f"<b>Стоимость со скидкой:</b> {new_price:.2f} руб.\n"
            f"</blockquote>\n"
            f"Промокод успешно применен! Скидка: {percentage}%"
        )

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="💰 Оплатить", url=payment_url)
        keyboard.button(text="🕵️‍♂️ Проверить платеж", callback_data=f"check_payment:{payment_id}")
        keyboard.button(text="🔙 Отмена", callback_data="tariff_back_to_start")
        keyboard.adjust(1)

        await message.answer(
            text=message_text,
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Ошибка при обработке промокода: {e}")
        await message.answer("Произошла ошибка при обработке промокода. Попробуйте позже.")
        await state.clear()

@router.callback_query(F.data.startswith("buy_tariff:"))
async def buy_tariff(callback: CallbackQuery, state: FSMContext):
    try:
        tariff_id = int(callback.data.split(":")[1])
        
        tariff = await db.get_tariff(tariff_id)
        if not tariff:
            await callback.answer("Тариф не найден")
            return

        payment_id, payment_url = await yookassa_manager.create_payment(
            amount=float(tariff['price']),
            description=f"Оплата тарифа {tariff['name']}",
            user_id=str(callback.from_user.id),
            tariff_name=tariff['name']
        )

        if not payment_id or not payment_url:
            await callback.message.answer("Ошибка при создании платежа. Попробуйте позже.")
            return

        await state.update_data(payment_id=payment_id, tariff_id=tariff_id)

        keyboard = InlineKeyboardBuilder()
        keyboard.button(text="💰 Оплатить", url=payment_url)
        keyboard.button(text="🕵️‍♂️ Проверить платеж", callback_data=f"check_payment:{payment_id}")
        keyboard.button(text="🔙 Отмена", callback_data="tariff_back_to_start")
        keyboard.adjust(1)

        await callback.message.delete()
        await callback.message.answer(
            "💡 *Ваш счет готов!*\n\n"
            "👇 *Нажмите на кнопку ниже, чтобы быстро и безопасно оплатить счет.* Мы используем надежные платежные системы, чтобы ваша транзакция прошла без задержек и была защищена.\n\n"
            "💰 Завершите оплату и нажмите кнопку 🕵️‍♂️ *Проверить платеж*, что бы получить доступ к вашему сервису в считанные минуты! Если у Вас возникнут вопросы, наша поддержка всегда готова помочь 🤝",
            reply_markup=keyboard.as_markup(),
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.error(f"Ошибка при создании платежа: {e}")
        await callback.message.answer("Произошла ошибка при создании платежа. Попробуйте позже.")

@router.callback_query(F.data == "show_tariffs")
async def show_tariffs(callback: CallbackQuery):
    """Отображение списка серверов с тарифами"""
    try:
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("""
                SELECT DISTINCT s.id, s.name 
                FROM server_settings s
                JOIN tariff t ON s.id = t.server_id
                WHERE t.is_enable = 1
            """) as cursor:
                servers = await cursor.fetchall()

        if not servers:
            await callback.answer("В данный момент нет доступных тарифов")
            return

        keyboard = InlineKeyboardBuilder()
        for server in servers:
            keyboard.button(
                text=f"{server['name']}", 
                callback_data=f"user_select_server:{server['id']}"
            )
        keyboard.button(text="🔙 Назад", callback_data="tariff_back_to_start")
        keyboard.adjust(2, 1)

        tariff_message = await db.get_bot_message("tariff")
        text = tariff_message['text'] if tariff_message else "🚀 Независимо от ваших потребностей, мы предлагаем гибкие тарифные планы для любого типа сервера"

        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard.as_markup()
        )

    except Exception as e:
        logger.error(f"Ошибка при отображении серверов: {e}")
        await callback.message.edit_text(
            "Произошла ошибка при загрузке списка серверов",
            reply_markup= await get_start_keyboard()
        )

@router.callback_query(F.data.startswith("user_select_server:"))
async def show_server_tariffs(callback: CallbackQuery):
    """Отображение тарифов для выбранного сервера"""
    try:
        server_id = int(callback.data.split(":")[1])
        
        async with aiosqlite.connect(db.db_path) as conn:
            conn.row_factory = aiosqlite.Row
            async with conn.execute("""
                SELECT t.*, s.name as server_name
                FROM tariff t
                JOIN server_settings s ON t.server_id = s.id
                WHERE t.server_id = ? AND t.is_enable = 1
                ORDER BY t.price
            """, (server_id,)) as cursor:
                tariffs = await cursor.fetchall()

        if not tariffs:
            await callback.answer("Для данного сервера нет доступных тарифов")
            return

        server_name = tariffs[0]['server_name']
        text = f"🌍 Сервер: {server_name}\n\nДоступные тарифные планы:\n\n"
        
        for tariff in tariffs:
            text += (
                f"<blockquote>"
                f"<b>Тарифный план:</b> {tariff['name']}\n"
                f"<b>Описание:</b> {tariff['description']}\n"
                f"<b>Стоимость:</b> {tariff['price']} руб.\n"
                f"<b>Срок действия:</b> {tariff['left_day']} дней\n"
                f"</blockquote>\n"
            )
        
        text += "\nВыберите подходящий тарифный план:"

        keyboard = InlineKeyboardBuilder()
        for tariff in tariffs:
            keyboard.button(
                text=f"{tariff['name']} - {tariff['price']}₽", 
                callback_data=f"select_tariff:{tariff['id']}"
            )
        keyboard.button(text="🔙 К серверам", callback_data="show_tariffs")
        keyboard.button(text="🔙 В меню", callback_data="tariff_back_to_start")
        keyboard.adjust(2)

        await callback.message.edit_text(
            text=text,
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Ошибка при отображении тарифов сервера: {e}")
        await callback.message.edit_text(
            "Произошла ошибка при загрузке тарифов",
            reply_markup= await get_start_keyboard()
        )

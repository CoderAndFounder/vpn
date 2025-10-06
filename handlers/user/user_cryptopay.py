from aiogram import Router, F
from aiogram.types import CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import InlineKeyboardBuilder
from loguru import logger
import json
from datetime import datetime, timedelta
import aiosqlite

from handlers.database import db
from handlers.crypto_pay import crypto_pay_manager
from handlers.buy_subscribe import subscription_manager
from handlers.user.user_kb import get_lk_keyboard
router = Router()

@router.callback_query(F.data.startswith("apply_crypto_payments:"))
async def process_crypto_payment(callback: CallbackQuery, state: FSMContext):
    """Обработка оплаты криптовалютой"""
    try:
        tariff_id = int(callback.data.split(':')[1])
        
        crypto_settings = await db.get_crypto_settings()
        if not crypto_settings or not crypto_settings['is_enable']:
            await callback.answer("Оплата криптовалютой временно недоступна", show_alert=True)
            return

        async with aiosqlite.connect(db.db_path) as db_conn:
            db_conn.row_factory = aiosqlite.Row
            async with db_conn.execute('SELECT * FROM tariff WHERE id = ?', (tariff_id,)) as cursor:
                tariff = await cursor.fetchone()

        if not tariff:
            await callback.answer("Тариф не найден", show_alert=True)
            return

        supported_assets = json.loads(crypto_settings['supported_assets'])
        if not supported_assets:
            await callback.answer("Нет доступных валют для оплаты", show_alert=True)
            return

        asset = supported_assets[0]

        description = f"Оплата тарифа {tariff['name']} на {tariff['left_day']} дней"
        invoice = await crypto_pay_manager.create_payment(
            amount=float(tariff['price']),
            description=description
        )

        if not invoice:
            await callback.answer("Ошибка при создании счета", show_alert=True)
            return

        payment_data = {
            'user_id': callback.from_user.id,
            'tariff_id': tariff_id,
            'invoice_id': invoice['invoice_id'],
            'amount': float(tariff['price']),
            'asset': asset,
            'status': 'pending'
        }
        
        async with aiosqlite.connect(db.db_path) as db_conn:
            await db_conn.execute("""
                INSERT INTO crypto_payments 
                (user_id, tariff_id, invoice_id, amount, asset, status, created_at)
                VALUES (?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                payment_data['user_id'],
                payment_data['tariff_id'],
                payment_data['invoice_id'],
                payment_data['amount'],
                payment_data['asset'],
                payment_data['status']
            ))
            await db_conn.commit()

        logger.debug(f"Invoice data: {invoice}")
        message_text = (
            f"💰 <b>Оплата тарифа {tariff['name']}</b>\n\n"
            f"💵 Сумма: {tariff['price']} RUB\n"
            f"⏱ Счет действителен 60 минут\n\n"
            f"🔗 <a href='{invoice['pay_url']}'>Оплатить</a>\n\n"
            "После оплаты нажмите кнопку проверки"
        )

        keyboard = InlineKeyboardBuilder()
        keyboard.button(
            text="🔄 Проверить оплату",
            callback_data=f"check_crypto_payment:{invoice['invoice_id']}"
        )
        keyboard.button(text="❌ Отменить", callback_data="cancel_payment")
        keyboard.adjust(1)

        await callback.message.edit_text(
            text=message_text,
            reply_markup=keyboard.as_markup(),
            parse_mode="HTML"
        )

    except Exception as e:
        logger.error(f"Ошибка при создании крипто-платежа: {e}")
        await callback.answer(
            "Произошла ошибка при создании платежа",
            show_alert=True
        )

@router.callback_query(F.data.startswith("check_crypto_payment:"))
async def check_crypto_payment(callback: CallbackQuery):
    """Проверка статуса криптоплатежа"""
    try:
        invoice_id = callback.data.split(':')[1]
        
        async with aiosqlite.connect(db.db_path) as db_conn:
            db_conn.row_factory = aiosqlite.Row
            async with db_conn.execute('SELECT * FROM crypto_payments WHERE invoice_id = ?', (invoice_id,)) as cursor:
                payment = await cursor.fetchone()

        if not payment:
            await callback.answer("Платёж не найден", show_alert=True)
            return

        invoices = await crypto_pay_manager.api.get_invoices(
            invoice_ids=[invoice_id]
        )
        
        if not invoices or len(invoices) == 0:
            await callback.answer("Не удалось получить информацию о платеже", show_alert=True)
            return

        invoice = invoices[0]
        logger.info(f"Получен статус платежа {invoice_id}: {invoice.get('status', 'unknown')}")
        
        if invoice.get('status') == 'paid':
            async with aiosqlite.connect(db.db_path) as db_conn:
                await db_conn.execute(
                    'UPDATE crypto_payments SET status = ? WHERE invoice_id = ?',
                    ('paid', invoice_id)
                )
                await db_conn.execute("""
                    INSERT INTO payments (user_id, tariff_id, price, date)
                    VALUES (?, ?, ?, datetime('now'))
                """, (payment['user_id'], payment['tariff_id'], payment['amount']))
                await db_conn.commit()

            subscription = await subscription_manager.create_subscription(
                user_id=payment['user_id'],
                tariff_id=payment['tariff_id'],
                is_trial=False
            )

            if not subscription:
                logger.error("Ошибка при создании подписки в базе данных")
                await callback.message.edit_text(
                    "Произошла ошибка при активации подписки. Пожалуйста, обратитесь в поддержку.",
                    reply_markup=None
                )
                return

            async with aiosqlite.connect(db.db_path) as db_conn:
                db_conn.row_factory = aiosqlite.Row
                async with db_conn.execute('SELECT * FROM tariff WHERE id = ?', (payment['tariff_id'],)) as cursor:
                    tariff = await cursor.fetchone()

            message_text = (
                "🎉 Поздравляем! Ваша подписка активирована!\n\n"
                f"<blockquote>"
                f"<b>Тариф:</b> {tariff['name']}\n"
                f"<b>Действует до:</b> {subscription['end_date'].strftime('%d.%m.%Y')}\n"
                f"</blockquote>"
                "Для подключения используйте следующую ссылку:\n\n"
                "<blockquote>"
                f"<code>{subscription['vless']}</code>\n"
                "</blockquote>\n"
                "⚠️ Сохраните эту ссылку, она потребуется для настройки приложения.\n"
                "Инструкции по настройке Вы найдете в личном кабинете."
            )

            await callback.message.edit_text(
                text=message_text,
                parse_mode="HTML",
                reply_markup=get_lk_keyboard()
            )
        else:
            await callback.answer(
                f"Оплата еще не получена. Статус: {invoice.get('status', 'в обработке')}",
                show_alert=True
            )

    except Exception as e:
        logger.error(f"Ошибка при проверке крипто-платежа: {e}")
        logger.debug(f"Детали ошибки: {str(e)}")
        await callback.answer(
            "Произошла ошибка при проверке платежа",
            show_alert=True
        )

@router.callback_query(F.data == "cancel_payment")
async def cancel_payment(callback: CallbackQuery):
    """Отмена платежа"""
    try:
        await callback.message.edit_text(
            "❌ Оплата отменена",
            reply_markup=None
        )
    except Exception as e:
        logger.error(f"Ошибка при отмене платежа: {e}")
        await callback.answer("Произошла ошибка", show_alert=True) 
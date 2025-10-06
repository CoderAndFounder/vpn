from aiogram import Router, F
from aiogram.types import CallbackQuery
from handlers.database import Database
from handlers.buy_subscribe import subscription_manager
from loguru import logger
from handlers.user.user_kb import get_start_keyboard, get_user_balance_keyboard
import aiosqlite
from datetime import datetime

router = Router()

@router.callback_query(F.data.startswith("apply_balance:"))
async def process_balance_payment(callback: CallbackQuery):
    """Обработка оплаты с баланса"""
    try:
        tariff_id = int(callback.data.split(":")[1])
        db = Database()
        
        logger.info(f"Начало оплаты с баланса для пользователя {callback.from_user.id}, тариф {tariff_id}")
        
        tariff = await db.get_tariff(tariff_id)
        if not tariff:
            logger.warning(f"Тариф {tariff_id} не найден при попытке оплаты пользователем {callback.from_user.id}")
            await callback.answer("Тариф не найден", show_alert=True)
            return
            
        current_balance = await db.get_user_balance(callback.from_user.id)
        logger.info(f"Текущий баланс пользователя {callback.from_user.id}: {current_balance} руб.")
        
        if not await db.check_balance_sufficient(callback.from_user.id, float(tariff['price'])):
            logger.warning(f"Недостаточно средств у пользователя {callback.from_user.id}. "
                         f"Требуется: {tariff['price']}, баланс: {current_balance}")
            await callback.message.edit_text(
                f"❌ <b>Недостаточно средств на балансе.</b>\n\n"
                f"Необходимо: <b>{tariff['price']} руб.</b>\n"
                f"Ваш баланс: <b>{current_balance:.2f} руб.</b>\n\n"
                f"Пополните баланс и повторите попытку.",
                reply_markup=get_user_balance_keyboard(),
                parse_mode="HTML"
            )
            return
            
        payment_success = await db.update_balance(
            user_id=callback.from_user.id,
            amount=-float(tariff['price']),
            type='subscription_payment',
            description=f"Оплата тарифа {tariff['name']}"
        )
        
        if payment_success:
            logger.info(f"Успешное списание {tariff['price']} руб. с баланса пользователя {callback.from_user.id}")
            
            subscription_created = await subscription_manager.create_subscription(
                user_id=callback.from_user.id,
                tariff_id=tariff_id,
                payment_id=None
            )
            
            if subscription_created:
                logger.info(f"Подписка успешно создана для пользователя {callback.from_user.id}")
                
                protocol_key = 'vless' if 'vless' in subscription_created else 'ss'
                
                await callback.message.edit_text(
                    "✅ Оплата прошла успешно!\n\n"
                    f"<b>Тариф:</b> {tariff['name']}\n"
                    f"<b>Сумма:</b> {tariff['price']} руб.\n"
                    f"<b>Списано с баланса:</b> {tariff['price']} руб.\n"
                    f"<b>Остаток на балансе:</b> {(current_balance - float(tariff['price'])):.2f} руб.\n\n"
                    "🎉 Подписка успешно активирована!\n\n"
                    "🔐 <b>Данные для подключения:</b>\n"
                    f"<code>{subscription_created[protocol_key]}</code>\n\n",
                    parse_mode="HTML",
                    reply_markup=await get_start_keyboard(),
                    disable_web_page_preview=True
                )
                
                async with aiosqlite.connect(db.db_path) as conn:
                    async with conn.execute(
                        'SELECT pay_notify FROM bot_settings LIMIT 1'
                    ) as cursor:
                        notify_settings = await cursor.fetchone()

                    if notify_settings and notify_settings[0] != 0:
                        message_text = (
                            "🎉 Новая подписка! 🏆\n"
                            "<blockquote>"
                            f"👤 Пользователь: {callback.from_user.id}\n"
                            f"💳 Тариф: {tariff['name']}\n"
                            f"💰 Способ оплаты: Оплата с баланса\n"
                            f"📅 Дата активации: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                            "🚀 Подписка успешно оформлена!</blockquote>"
                        )

                        try:
                            await callback.bot.send_message(
                                chat_id=notify_settings[0],
                                text=message_text,
                                parse_mode="HTML"
                            )
                        except Exception as e:
                            logger.error(f"Ошибка при отправке уведомления администратору: {e}")
            else:
                refund_success = await db.update_balance(
                    user_id=callback.from_user.id,
                    amount=float(tariff['price']),
                    type='refund',
                    description=f"Возврат средств за тариф {tariff['name']} (ошибка активации)"
                )
                
                logger.info(f"Возврат средств пользователю {callback.from_user.id}: {'успешно' if refund_success else 'ошибка'}")
                
                await callback.message.edit_text(
                    "❌ Произошла ошибка при активации подписки.\n"
                    "Средства возвращены на баланс.\n"
                    "Пожалуйста, попробуйте позже или обратитесь в поддержку.",
                    reply_markup=await get_start_keyboard()
                )
            
    except Exception as e:
        logger.error(f"Ошибка при оплате с баланса пользователем {callback.from_user.id}: {e}")
        await callback.message.edit_text(
            "❌ Произошла ошибка при обработке оплаты.\n"
            "Пожалуйста, попробуйте позже или обратитесь в поддержку.",
            reply_markup=await get_start_keyboard()
        ) 
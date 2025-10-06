from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from handlers.database import db
from handlers.admin.admin_kb import get_admin_show_payments_code_keyboard
from datetime import datetime
from loguru import logger
import random
import string

router = Router()

class PaymentCodeStates(StatesGroup):
    waiting_for_count = State()
    waiting_for_amount = State()
    waiting_for_delete_code = State()

def generate_payment_code(length: int = 12) -> str:
    """Генерация уникального кода оплаты"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choices(chars, k=length))

@router.callback_query(F.data == "admin_show_payments_code")
async def show_payment_codes(callback: CallbackQuery):
    """Обработчик отображения кодов оплаты"""
    try:
        payment_codes = await db.get_all_payment_codes()
        
        active_codes = [code for code in payment_codes if code['is_enable']]
        
        total_sum = sum(code['sum'] for code in active_codes)
        
        recent_codes = sorted(
            payment_codes, 
            key=lambda x: datetime.strptime(x['create_date'], '%Y-%m-%d %H:%M:%S'),
            reverse=True
        )[:2]
        
        message = "💰 Коды оплаты:\n\n"
        message += f"Всего активных кодов: {len(active_codes)}\n"
        message += f"На сумму: {total_sum:.2f} ₽\n\n"
        
        if recent_codes:
            message += "2 последних добавленных кода:\n"
            for code in recent_codes:
                message += "<blockquote>\n"
                message += f"<code>{code['pay_code']}</code>\n"
                message += f"Сумма: {code['sum']} ₽\n"
                message += f"Дата добавления: {code['create_date']}\n"
                message += f"Статус: {'✅ Активен' if code['is_enable'] else '❌ Неактивен'}\n"
                message += "</blockquote>\n"
        else:
            message += "Коды оплаты отсутствуют"

        await callback.message.delete()
        await callback.message.answer(
            text=message,
            reply_markup=get_admin_show_payments_code_keyboard(),
            parse_mode="HTML"
        )
        await callback.answer()
        
    except Exception as e:
        logger.error(f"Ошибка при отображении кодов оплаты: {e}")
        await callback.answer("Произошла ошибка при получении кодов оплаты", show_alert=True)

@router.callback_query(F.data == "admin_add_payments_code")
async def add_payment_code(callback: CallbackQuery, state: FSMContext):
    """Обработчик добавления кода оплаты"""
    await callback.message.delete()
    await callback.message.answer(
        "💵 Введите количество кодов оплаты для создания\n"
        "(К примеру если ввести 10 то будет создано 10 кодов)"
    )
    await state.set_state(PaymentCodeStates.waiting_for_count)
    await callback.answer()

@router.message(PaymentCodeStates.waiting_for_count)
async def process_codes_count(message: Message, state: FSMContext):
    """Обработка введенного количества кодов"""
    try:
        count = int(message.text)
        if count <= 0 or count > 100:  
            await message.answer("❌ Количество кодов должно быть от 1 до 100")
            return
        
        await state.update_data(codes_count=count)
        await message.answer("💰 Введите номинал кода оплаты:")
        await state.set_state(PaymentCodeStates.waiting_for_amount)
        
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректное число")

@router.message(PaymentCodeStates.waiting_for_amount)
async def process_codes_amount(message: Message, state: FSMContext):
    """Обработка введенного номинала кода"""
    try:
        amount = float(message.text)
        if amount <= 0:
            await message.answer("❌ Сумма должна быть больше 0")
            return
        
        data = await state.get_data()
        codes_count = data['codes_count']
        
        generated_codes = []
        total_sum = amount * codes_count
        
        for _ in range(codes_count):
            while True:
                code = generate_payment_code()
                if not await db.get_payment_code(code):
                    break
            
            if await db.add_payment_code(code, amount):
                generated_codes.append({"code": code, "sum": amount})
        
        message_text = f"✅ Вы добавили {codes_count} кодов оплаты на сумму: {total_sum:.2f} ₽\n"
        
        if codes_count > 5:
            message_text += "📋 Первые 5 кодов:\n\n"
            for code_info in generated_codes[:5]:
                message_text += "<blockquote>\n"
                message_text += f"Код оплаты:<code> {code_info['code']}</code>\n"
                message_text += f"Сумма: {code_info['sum']} ₽\n"
                message_text += "</blockquote>\n"
            message_text += "\n💾 Чтобы получить все коды в виде файла, нажмите кнопку 'Получить коды'"
        else:
            message_text += "📋 Список кодов:\n\n"
            for code_info in generated_codes:
                message_text += "<blockquote>\n"
                message_text += f"Код оплаты:<code> {code_info['code']}</code>\n"
                message_text += f"Сумма: {code_info['sum']} ₽\n"
                message_text += "</blockquote>\n"
        
        await message.answer(
            message_text,
            parse_mode="HTML",
            reply_markup=get_admin_show_payments_code_keyboard()
        )
        await state.clear()
        
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректную сумму")
    except Exception as e:
        logger.error(f"Ошибка при создании кодов оплаты: {e}")
        await message.answer(
            "❌ Произошла ошибка при создании кодов оплаты",
            reply_markup=get_admin_show_payments_code_keyboard()
        )
        await state.clear()

@router.callback_query(F.data == "admin_delete_payments_code")
async def delete_payment_code(callback: CallbackQuery, state: FSMContext):
    """Обработчик удаления кода оплаты"""
    await callback.message.delete()
    await callback.message.answer("Введите код оплаты для удаления:")
    await state.set_state(PaymentCodeStates.waiting_for_delete_code)
    await callback.answer()

@router.message(PaymentCodeStates.waiting_for_delete_code)
async def process_delete_code(message: Message, state: FSMContext):
    """Обработка введенного кода для удаления"""
    try:
        payment_code = await db.get_payment_code(message.text)
        
        if not payment_code:
            await message.answer(
                "❌ Код оплаты не найден или уже неактивен",
                reply_markup=get_admin_show_payments_code_keyboard()
            )
            await state.clear()
            return
        
        if await db.disable_payment_code(message.text):
            message_text = "✅ Код оплаты успешно деактивирован\n\n"
            message_text += "<blockquote>\n"
            message_text += f"Код:<code> {payment_code['pay_code']}</code>\n"
            message_text += f"Сумма: {payment_code['sum']} ₽\n"
            message_text += f"Дата создания: {payment_code['create_date']}\n"
            message_text += "</blockquote>"
            
            await message.answer(
                message_text,
                parse_mode="HTML",
                reply_markup=get_admin_show_payments_code_keyboard()
            )
        else:
            await message.answer(
                "❌ Произошла ошибка при деактивации кода",
                reply_markup=get_admin_show_payments_code_keyboard()
            )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Ошибка при удалении кода оплаты: {e}")
        await message.answer(
            "❌ Произошла ошибка при обработке запроса",
            reply_markup=get_admin_show_payments_code_keyboard()
        )
        await state.clear() 
from flask import Blueprint, render_template, jsonify
import aiosqlite
from loguru import logger
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

payments_bp = Blueprint('payments', __name__, url_prefix='/admin/payments')

async def get_db():
    db_path = os.path.join(os.getcwd(), os.getenv('DATABASE_PATH'))
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    return db

@payments_bp.route('/')
async def payments_list():
    try:
        db = await get_db()
        query = """
            SELECT 
                p.id,
                p.price,
                p.date,
                u.username as user_name,
                t.name as tariff_name,
                COALESCE(s.name, '') as server_name
            FROM payments p
            LEFT JOIN "user" u ON p.user_id = u.telegram_id
            LEFT JOIN tariff t ON p.tariff_id = t.id
            LEFT JOIN server_settings s ON t.server_id = s.id
            ORDER BY p.id DESC
        """
        async with db.execute(query) as cursor:
            payments = await cursor.fetchall()
            # Преобразуем в список словарей
            payments_list = [dict(row) for row in payments]
            # Форматируем дату
            for payment in payments_list:
                payment['date'] = datetime.fromisoformat(payment['date']).strftime('%d.%m.%Y %H:%M')

        await db.close()
        return render_template('admin/payments.html', payments=payments_list)
    except Exception as e:
        logger.error(f"Ошибка при получении платежей: {e}")
        return "Ошибка при получении платежей", 500

# API для получения данных в формате JSON
@payments_bp.route('/api/payments')
async def get_payments():
    try:
        db = await get_db()
        query = """
            SELECT 
                p.id,
                p.price,
                p.date,
                u.username as user_name,
                t.name as tariff_name,
                COALESCE(s.name, '') as server_name
            FROM payments p
            LEFT JOIN "user" u ON p.user_id = u.telegram_id
            LEFT JOIN tariff t ON p.tariff_id = t.id
            LEFT JOIN server_settings s ON t.server_id = s.id
            ORDER BY p.id DESC
        """
        async with db.execute(query) as cursor:
            payments = await cursor.fetchall()
            payments_list = [dict(row) for row in payments]
            for payment in payments_list:
                payment['date'] = datetime.fromisoformat(payment['date']).strftime('%d.%m.%Y %H:%M')

        await db.close()
        return jsonify(payments_list)
    except Exception as e:
        logger.error(f"Ошибка при получении данных платежей: {e}")
        return jsonify({"error": str(e)}), 500

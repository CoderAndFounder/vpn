from flask import Blueprint, render_template, g, current_app, request
import aiosqlite
import os
from loguru import logger

admin_bp = Blueprint('admin', __name__)

async def get_db():
    if 'db' not in g:
        g.db = await aiosqlite.connect(os.getenv('DATABASE_PATH'))
        g.db.row_factory = aiosqlite.Row
    return g.db

@admin_bp.route('/dashboard')
async def admin_dashboard():
    try:
        db = await get_db()
        # Получаем общую сумму заработка
        async with db.execute('SELECT SUM(price) as total_earnings FROM payments') as cursor:
            earnings = await cursor.fetchone()
            total_earnings = earnings['total_earnings'] or 0

        # Получаем популярные тарифы
        async with db.execute('''
            SELECT t.name, COUNT(*) as count
            FROM user_subscription us
            JOIN tariff t ON us.tariff_id = t.id
            GROUP BY t.id, t.name
            ORDER BY count DESC
            LIMIT 2
        ''') as cursor:
            popular_tariffs = await cursor.fetchall()
            
        # Форматируем названия тарифов
        if len(popular_tariffs) == 0:
            popular_tariffs_text = "Нет данных"
        elif len(popular_tariffs) == 1:
            popular_tariffs_text = popular_tariffs[0]['name']
        else:
            popular_tariffs_text = f"{popular_tariffs[0]['name']}<br>{popular_tariffs[1]['name']}"

        # Получаем последние платежи
        async with db.execute('''
            SELECT 
                p.id,
                p.price,
                p.date,
                t.name as tariff_name,
                u.username
            FROM payments p
            JOIN tariff t ON p.tariff_id = t.id
            JOIN "user" u ON p.user_id = u.telegram_id
            ORDER BY p.date DESC
            LIMIT 10
        ''') as cursor:
            recent_payments = await cursor.fetchall()

        # Получаем статистику пользователей
        async with db.execute('''
            SELECT 
                COUNT(*) as total_users,
                SUM(CASE WHEN date >= date('now', '-7 days') THEN 1 ELSE 0 END) as new_users_week
            FROM "user"
        ''') as cursor:
            user_stats = await cursor.fetchone()

        return render_template('admin/dashboard.html', 
                             total_earnings=total_earnings,
                             popular_tariffs=popular_tariffs_text,
                             recent_payments=recent_payments,
                             total_users=user_stats['total_users'],
                             new_users_week=user_stats['new_users_week'])
    except Exception as e:
        logger.error(f"Ошибка при доступе к панели администратора: {e}")
        return "Ошибка доступа к панели администратора", 500

@admin_bp.route('/dashboard')
async def dashboard():
    try:
        db = await get_db()
        
        # Получаем общую сумму заработка
        async with db.execute('SELECT SUM(price) as total_earnings FROM payments') as cursor:
            earnings = await cursor.fetchone()
            total_earnings = earnings['total_earnings'] or 0
        
        # Получаем статистику
        async with db.execute('''
            SELECT 
                (SELECT COUNT(*) FROM "user") as total_users,
                (SELECT COUNT(*) FROM "user" WHERE date >= date('now', '-7 days')) as new_users_week,
                (SELECT COUNT(*) FROM user_subscription WHERE is_active = 1) as active_subscriptions
        ''') as cursor:
            stats = await cursor.fetchone()
        
        await db.close()
        
        return await render_template('admin/dashboard.html',
                                   total_users=stats['total_users'],
                                   new_users_week=stats['new_users_week'],
                                   active_subscriptions=stats['active_subscriptions'],
                                   total_earnings=total_earnings)
    except Exception as e:
        logger.error(f"Ошибка при получении данных дашборда: {e}")
        return await render_template('admin/dashboard.html', error=str(e))

@admin_bp.route('/servers')
async def servers_page():
    try:
        async with get_db() as db:
            async with db.execute('SELECT * FROM server_settings ORDER BY id DESC') as cursor:
                servers = await cursor.fetchall()
                columns = [description[0] for description in cursor.description]
                servers_list = [dict(zip(columns, row)) for row in servers]
        return await render_template('admin/servers.html', servers=servers_list)
    except Exception as e:
        logger.error(f"Ошибка при получении списка серверов: {e}")
        return await render_template('admin/servers.html', error=str(e))

@admin_bp.teardown_app_request
async def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        await db.close()

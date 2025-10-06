from flask import Blueprint, render_template, jsonify, request
import aiosqlite
import os
from loguru import logger
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

users_bp = Blueprint('users', __name__, url_prefix='/admin/users')

async def get_db():
    db_path = os.path.join(os.getcwd(), os.getenv('DATABASE_PATH'))
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    return db

@users_bp.route('/')
async def users_list():
    try:
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '').strip()
        per_page = 20
        offset = (page - 1) * per_page
        
        db = await get_db()
        
        # Базовый запрос с поиском
        base_query = '''
            FROM "user"
            WHERE (username LIKE ? OR telegram_id LIKE ? OR referral_code LIKE ?)
        '''
        search_params = (f'%{search}%', f'%{search}%', f'%{search}%')
        
        # Получаем общее количество с учетом поиска
        async with db.execute(f'SELECT COUNT(*) as count {base_query}', search_params) as cursor:
            total_users = (await cursor.fetchone())['count']
            
        # Получаем пользователей с пагинацией и поиском
        async with db.execute(f'''
            SELECT 
                id, username, telegram_id, trial_period, is_enable,
                datetime(date, 'localtime') as date,
                referral_code, referral_count, referred_by
            {base_query}
            ORDER BY id DESC
            LIMIT ? OFFSET ?
        ''', search_params + (per_page, offset)) as cursor:
            users = [dict(row) for row in await cursor.fetchall()]
            
        total_pages = (total_users + per_page - 1) // per_page
        
        await db.close()
        return render_template('admin/users.html', 
                             users=users, 
                             current_page=page,
                             total_pages=total_pages,
                             total_users=total_users,
                             search=search)
    except Exception as e:
        logger.error(f"Ошибка при получении пользователей: {e}")
        return str(e), 500

@users_bp.route('/edit/<int:user_id>', methods=['GET', 'POST'])
async def edit_user(user_id):
    try:
        db = await get_db()
        if request.method == 'GET':
            async with db.execute('SELECT * FROM "user" WHERE id = ?', (user_id,)) as cursor:
                user = await cursor.fetchone()
                if not user:
                    await db.close()
                    return jsonify({'error': 'Пользователь не найден'}), 404
                return jsonify(dict(user))
        else:
            data = request.get_json()
            await db.execute('''
                UPDATE "user" 
                SET username = ?, trial_period = ?, is_enable = ?
                WHERE id = ?
            ''', (data['username'], data['trial_period'], data['is_enable'], user_id))
            await db.commit()
            await db.close()
            return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Ошибка при работе с пользователем: {e}")
        return jsonify({'error': str(e)}), 500

@users_bp.route('/delete/<int:user_id>', methods=['POST'])
async def delete_user(user_id):
    try:
        db = await get_db()
        await db.execute('DELETE FROM "user" WHERE id = ?', (user_id,))
        await db.commit()
        await db.close()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Ошибка при удалении пользователя: {e}")
        return jsonify({'error': str(e)}), 500

@users_bp.route('/view/<int:user_id>', methods=['GET'])
async def view_user(user_id):
    try:
        db = await get_db()
        # Получаем информацию о пользователе
        async with db.execute('SELECT * FROM "user" WHERE id = ?', (user_id,)) as cursor:
            user = await cursor.fetchone()
            if not user:
                await db.close()
                return jsonify({'error': 'Пользователь не найден'}), 404
            user_data = dict(user)
        
        # Получаем платежи пользователя
        async with db.execute('''
            SELECT p.*, t.name as tariff_name
            FROM payments p
            LEFT JOIN tariff t ON p.tariff_id = t.id
            WHERE p.user_id = ?
            ORDER BY p.date DESC
        ''', (user['telegram_id'],)) as cursor:
            payments = [dict(row) for row in await cursor.fetchall()]
        
        # Получаем подписки пользователя
        async with db.execute('''
            SELECT 
                us.*, 
                t.name as tariff_name,
                s.name as server_name,
                julianday(us.end_date) - julianday('now') as days_left
            FROM user_subscription us
            LEFT JOIN tariff t ON us.tariff_id = t.id
            LEFT JOIN server_settings s ON us.server_id = s.id
            WHERE us.user_id = ?
            ORDER BY us.start_date DESC
        ''', (user['telegram_id'],)) as cursor:
            subscriptions = [dict(row) for row in await cursor.fetchall()]
        
        await db.close()
        return jsonify({
            'user': user_data,
            'payments': payments,
            'subscriptions': subscriptions
        })
    except Exception as e:
        logger.error(f"Ошибка при получении данных пользователя: {e}")
        return jsonify({'error': str(e)}), 500

@users_bp.route('/subscription/<int:subscription_id>/toggle', methods=['POST'])
async def toggle_subscription(subscription_id):
    try:
        db = await get_db()
        # Получаем текущий статус подписки
        async with db.execute('SELECT is_active FROM user_subscription WHERE id = ?', 
                            (subscription_id,)) as cursor:
            subscription = await cursor.fetchone()
            if not subscription:
                await db.close()
                return jsonify({'error': 'Подписка не найдена'}), 404
            
            # Инвертируем статус
            new_status = not subscription['is_active']
            
            # Обновляем статус
            await db.execute('''
                UPDATE user_subscription 
                SET is_active = ?
                WHERE id = ?
            ''', (new_status, subscription_id))
            await db.commit()
            
        await db.close()
        return jsonify({'success': True, 'is_active': new_status})
    except Exception as e:
        logger.error(f"Ошибка при изменении статуса подписки: {e}")
        return jsonify({'error': str(e)}), 500

@users_bp.route('/subscription/<int:subscription_id>/delete', methods=['POST'])
async def delete_subscription(subscription_id):
    try:
        db = await get_db()
        await db.execute('DELETE FROM user_subscription WHERE id = ?', (subscription_id,))
        await db.commit()
        await db.close()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Ошибка при удалении подписки: {e}")
        return jsonify({'error': str(e)}), 500

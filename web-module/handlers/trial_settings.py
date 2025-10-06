from flask import Blueprint, jsonify, request, render_template
import aiosqlite
import os
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

trial_settings_bp = Blueprint('trial_settings', __name__, url_prefix='/admin/trial-settings')

async def get_db():
    db_path = os.path.join(os.getcwd(), os.getenv('DATABASE_PATH'))
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    return db

@trial_settings_bp.route('/')
async def trial_settings_list():
    try:
        db = await get_db()
        async with db.execute('''
            SELECT t.*, s.name as server_name 
            FROM trial_settings t
            LEFT JOIN server_settings s ON t.server_id = s.id
            ORDER BY t.id DESC
        ''') as cursor:
            settings = await cursor.fetchall()
            settings_list = [dict(row) for row in settings]
        await db.close()
        return render_template('admin/trial_settings.html', settings=settings_list)
    except Exception as e:
        logger.error(f"Ошибка при получении пробных тарифов: {e}")
        return render_template('admin/trial_settings.html', error=str(e))

@trial_settings_bp.route('/api/trial-settings', methods=['GET'])
async def get_trial_settings():
    try:
        db = await get_db()
        async with db.execute('''
            SELECT t.*, s.name as server_name 
            FROM trial_settings t
            LEFT JOIN server_settings s ON t.server_id = s.id
            ORDER BY t.id DESC
        ''') as cursor:
            settings = await cursor.fetchall()
            result = [dict(row) for row in settings]
        await db.close()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Ошибка при получении пробных тарифов: {e}")
        return jsonify({"error": str(e)}), 500

@trial_settings_bp.route('/api/trial-settings/<int:setting_id>', methods=['GET'])
async def get_trial_setting(setting_id):
    try:
        db = await get_db()
        async with db.execute('''
            SELECT t.*, s.name as server_name 
            FROM trial_settings t
            LEFT JOIN server_settings s ON t.server_id = s.id
            WHERE t.id = ?
        ''', (setting_id,)) as cursor:
            setting = await cursor.fetchone()
        await db.close()
        if setting:
            return jsonify(dict(setting))
        return jsonify({"error": "Пробный тариф не найден"}), 404
    except Exception as e:
        logger.error(f"Ошибка при получении пробного тарифа {setting_id}: {e}")
        return jsonify({"error": str(e)}), 500

@trial_settings_bp.route('/api/trial-settings', methods=['POST'])
async def create_trial_setting():
    try:
        data = request.json
        db = await get_db()
        
        # Деактивируем все существующие активные тарифы
        await db.execute('UPDATE trial_settings SET is_enable = 0 WHERE is_enable = 1')
        
        # Создаем новый тариф
        query = '''INSERT INTO trial_settings 
                  (name, left_day, server_id, is_enable) 
                  VALUES (?, ?, ?, ?)'''
        values = (
            data['name'],
            data['left_day'],
            data['server_id'],
            True  # Новый тариф всегда активный
        )
        await db.execute(query, values)
        await db.commit()
        await db.close()
        return jsonify({"message": "Пробный тариф создан успешно"})
    except Exception as e:
        logger.error(f"Ошибка при создании пробного тарифа: {e}")
        return jsonify({"error": str(e)}), 500

@trial_settings_bp.route('/api/trial-settings/<int:setting_id>', methods=['PUT'])
async def update_trial_setting(setting_id):
    try:
        data = request.json
        db = await get_db()
        
        # Если обновляемый тариф становится активным, деактивируем остальные
        if data.get('is_enable'):
            await db.execute('UPDATE trial_settings SET is_enable = 0 WHERE id != ?', (setting_id,))
        
        query = '''UPDATE trial_settings 
                  SET name=?, left_day=?, server_id=?, is_enable=?
                  WHERE id=?'''
        values = (
            data['name'],
            data['left_day'],
            data['server_id'],
            data.get('is_enable', False),
            setting_id
        )
        await db.execute(query, values)
        await db.commit()
        await db.close()
        return jsonify({"message": "Пробный тариф обновлен успешно"})
    except Exception as e:
        logger.error(f"Ошибка при обновлении пробного тарифа {setting_id}: {e}")
        return jsonify({"error": str(e)}), 500

@trial_settings_bp.route('/api/trial-settings/<int:setting_id>', methods=['DELETE'])
async def delete_trial_setting(setting_id):
    try:
        db = await get_db()
        await db.execute('DELETE FROM trial_settings WHERE id = ?', (setting_id,))
        await db.commit()
        await db.close()
        return jsonify({"message": "Пробный тариф удален успешно"})
    except Exception as e:
        logger.error(f"Ошибка при удалении пробного тарифа {setting_id}: {e}")
        return jsonify({"error": str(e)}), 500

@trial_settings_bp.route('/api/servers', methods=['GET'])
async def get_servers():
    try:
        db = await get_db()
        async with db.execute('SELECT id, name FROM server_settings WHERE is_enable = 1 ORDER BY name') as cursor:
            servers = await cursor.fetchall()
            result = [dict(row) for row in servers]
        await db.close()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Ошибка при получении списка серверов: {e}")
        return jsonify({"error": str(e)}), 500

from flask import Blueprint, render_template, jsonify, request
import aiosqlite
import os
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

settings_bp = Blueprint('settings', __name__, url_prefix='/admin/settings')

async def get_db():
    db_path = os.path.join(os.getcwd(), os.getenv('DATABASE_PATH'))
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    return db

@settings_bp.route('/')
async def settings_list():
    try:
        db = await get_db()
        # Получаем настройки ЮKassa
        async with db.execute('SELECT * FROM yookassa_settings ORDER BY id') as cursor:
            yookassa_settings = [dict(row) for row in await cursor.fetchall()]
        
        # Получаем настройки бота
        async with db.execute('SELECT * FROM bot_settings LIMIT 1') as cursor:
            bot_settings_row = await cursor.fetchone()
            bot_settings = dict(bot_settings_row) if bot_settings_row else None
            
        await db.close()
        return render_template('admin/settings.html', 
                             yookassa_settings=yookassa_settings,
                             bot_settings=bot_settings)
    except Exception as e:
        logger.error(f"Ошибка при получении настроек: {e}")
        return str(e), 500

@settings_bp.route('/yookassa/edit/<int:setting_id>', methods=['GET', 'POST'])
async def edit_yookassa(setting_id):
    try:
        db = await get_db()
        if request.method == 'GET':
            async with db.execute('SELECT * FROM yookassa_settings WHERE id = ?', (setting_id,)) as cursor:
                setting = await cursor.fetchone()
                if not setting:
                    await db.close()
                    return jsonify({'error': 'Настройки не найдены'}), 404
                return jsonify(dict(setting))
        else:
            data = request.get_json()
            await db.execute('''
                UPDATE yookassa_settings 
                SET name = ?, shop_id = ?, api_key = ?, description = ?, is_enable = ?
                WHERE id = ?
            ''', (data['name'], data['shop_id'], data['api_key'], 
                  data.get('description'), data['is_enable'], setting_id))
            await db.commit()
            await db.close()
            return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Ошибка при работе с настройками ЮKassa: {e}")
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/yookassa/create', methods=['POST'])
async def create_yookassa():
    try:
        data = request.get_json()
        db = await get_db()
        await db.execute('''
            INSERT INTO yookassa_settings (name, shop_id, api_key, description, is_enable)
            VALUES (?, ?, ?, ?, ?)
        ''', (data['name'], data['shop_id'], data['api_key'], 
              data.get('description'), data.get('is_enable', 0)))
        await db.commit()
        await db.close()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Ошибка при создании настроек ЮKassa: {e}")
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/yookassa/delete/<int:setting_id>', methods=['POST'])
async def delete_yookassa(setting_id):
    try:
        db = await get_db()
        await db.execute('DELETE FROM yookassa_settings WHERE id = ?', (setting_id,))
        await db.commit()
        await db.close()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Ошибка при удалении настроек ЮKassa: {e}")
        return jsonify({'error': str(e)}), 500

@settings_bp.route('/bot/edit', methods=['POST'])
async def edit_bot():
    try:
        data = request.get_json()
        db = await get_db()
        
        # Проверяем существование записи
        async with db.execute('SELECT COUNT(*) as count FROM bot_settings') as cursor:
            result = await cursor.fetchone()
            exists = result['count'] > 0

        if exists:
            await db.execute('''
                UPDATE bot_settings 
                SET bot_token = ?, admin_id = ?, chat_id = ?, chanel_id = ?, 
                    is_enable = ?, reg_notify = ?, pay_notify = ?
            ''', (data['bot_token'], data['admin_id'], data.get('chat_id'), 
                  data.get('chanel_id'), data['is_enable'], 
                  data.get('reg_notify'), data.get('pay_notify')))
        else:
            await db.execute('''
                INSERT INTO bot_settings 
                (bot_token, admin_id, chat_id, chanel_id, is_enable, reg_notify, pay_notify)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (data['bot_token'], data['admin_id'], data.get('chat_id'), 
                  data.get('chanel_id'), data['is_enable'], 
                  data.get('reg_notify'), data.get('pay_notify')))
            
        await db.commit()
        await db.close()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Ошибка при обновлении настроек бота: {e}")
        return jsonify({'error': str(e)}), 500

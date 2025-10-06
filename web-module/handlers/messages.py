from flask import Blueprint, render_template, jsonify, request
import aiosqlite
import os
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

messages_bp = Blueprint('messages', __name__, url_prefix='/admin/messages')

async def get_db():
    db_path = os.path.join(os.getcwd(), os.getenv('DATABASE_PATH'))
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    return db

@messages_bp.route('/')
async def messages_list():
    try:
        db = await get_db()
        async with db.execute('SELECT * FROM bot_message ORDER BY command') as cursor:
            messages = [dict(row) for row in await cursor.fetchall()]
        await db.close()
        return render_template('admin/messages.html', messages=messages)
    except Exception as e:
        logger.error(f"Ошибка при получении сообщений: {e}")
        return str(e), 500

@messages_bp.route('/edit/<command>', methods=['GET', 'POST'])
async def edit_message(command):
    try:
        db = await get_db()
        if request.method == 'GET':
            async with db.execute('SELECT * FROM bot_message WHERE command = ?', (command,)) as cursor:
                message = await cursor.fetchone()
                if not message:
                    await db.close()
                    return jsonify({'error': 'Сообщение не найдено'}), 404
                return jsonify(dict(message))
        else:
            data = request.get_json()
            await db.execute('''
                UPDATE bot_message 
                SET text = ?, image_path = ?, is_enable = ?
                WHERE command = ?
            ''', (data['text'], data.get('image_path'), data['is_enable'], command))
            await db.commit()
            await db.close()
            return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Ошибка при работе с сообщением: {e}")
        return jsonify({'error': str(e)}), 500

@messages_bp.route('/create', methods=['POST'])
async def create_message():
    try:
        data = request.get_json()
        db = await get_db()
        await db.execute('''
            INSERT INTO bot_message (command, text, image_path, is_enable)
            VALUES (?, ?, ?, ?)
        ''', (data['command'], data['text'], data.get('image_path'), data.get('is_enable', 1)))
        await db.commit()
        await db.close()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Ошибка при создании сообщения: {e}")
        return jsonify({'error': str(e)}), 500

@messages_bp.route('/delete/<command>', methods=['POST'])
async def delete_message(command):
    try:
        db = await get_db()
        await db.execute('DELETE FROM bot_message WHERE command = ?', (command,))
        await db.commit()
        await db.close()
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Ошибка при удалении сообщения: {e}")
        return jsonify({'error': str(e)}), 500

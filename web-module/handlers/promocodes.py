from flask import Blueprint, render_template, jsonify, request
import aiosqlite
import os
from datetime import datetime
from loguru import logger
from dotenv import load_dotenv
import string
import random

load_dotenv()

promocodes_bp = Blueprint('promocodes', __name__, url_prefix='/admin/promocodes')

async def get_db():
    db_path = os.path.join(os.getcwd(), os.getenv('DATABASE_PATH'))
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    return db

async def init_db():
    try:
        async with aiosqlite.connect(os.path.join(os.getcwd(), os.getenv('DATABASE_PATH'))) as db:
            await db.execute('''
                CREATE TABLE IF NOT EXISTS promocodes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    promocod TEXT UNIQUE NOT NULL,
                    activation_limit INTEGER NOT NULL DEFAULT 0,
                    activation_total INTEGER NOT NULL DEFAULT 0,
                    percentage INTEGER NOT NULL DEFAULT 0,
                    is_enable BOOLEAN NOT NULL DEFAULT 1,
                    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            await db.commit()
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise e

def generate_promocode(length=8):
    """Генерация случайного промокода"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

@promocodes_bp.route('/')
async def promocodes_list():
    try:
        await init_db()  # Убедимся, что таблица существует
        db = await get_db()
        async with db.execute('''
            SELECT 
                id,
                promocod as code,
                activation_limit as usage_limit,
                activation_total as usage_count,
                percentage as discount,
                is_enable as is_active,
                datetime(date, 'localtime') as created_at
            FROM promocodes
            ORDER BY id DESC
        ''') as cursor:
            promocodes = await cursor.fetchall()
            promocodes_list = [dict(row) for row in promocodes]
        await db.close()
        return render_template('admin/promocodes.html', promocodes=promocodes_list)
    except Exception as e:
        logger.error(f"Ошибка при получении промокодов: {e}")
        return str(e), 500

@promocodes_bp.route('/generate', methods=['GET'])
async def generate():
    """Генерация нового промокода"""
    try:
        while True:
            new_code = generate_promocode()
            # Проверяем, не существует ли уже такой промокод
            db = await get_db()
            async with db.execute('SELECT id FROM promocodes WHERE promocod = ?', [new_code]) as cursor:
                exists = await cursor.fetchone()
                await db.close()
                if not exists:
                    break
        return jsonify({'promocode': new_code})
    except Exception as e:
        logger.error(f"Ошибка при генерации промокода: {e}")
        return jsonify({'error': str(e)}), 500

@promocodes_bp.route('/create', methods=['POST'])
async def create_promocode():
    try:
        data = request.get_json()
        code = data.get('code')
        usage_limit = data.get('usage_limit', 1)
        discount = data.get('discount')
        is_active = data.get('is_active', True)
        
        db = await get_db()
        # Проверяем уникальность промокода
        async with db.execute('SELECT id FROM promocodes WHERE promocod = ?', (code,)) as cursor:
            if await cursor.fetchone():
                await db.close()
                return jsonify({'error': 'Промокод уже существует'}), 400
        
        # Создаем промокод
        await db.execute('''
            INSERT INTO promocodes (promocod, activation_limit, percentage, is_enable)
            VALUES (?, ?, ?, ?)
        ''', (code, usage_limit, discount, is_active))
        await db.commit()
        await db.close()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Ошибка при создании промокода: {e}")
        return jsonify({'error': str(e)}), 500

@promocodes_bp.route('/edit/<int:promo_id>', methods=['GET', 'POST'])
async def edit_promocode(promo_id):
    try:
        db = await get_db()
        
        if request.method == 'GET':
            async with db.execute('''
                SELECT 
                    id,
                    promocod as code,
                    activation_limit as usage_limit,
                    percentage as discount,
                    is_enable as is_active
                FROM promocodes 
                WHERE id = ?
            ''', (promo_id,)) as cursor:
                promo = await cursor.fetchone()
                if not promo:
                    await db.close()
                    return jsonify({'error': 'Промокод не найден'}), 404
                return jsonify(dict(promo))
        else:
            data = request.get_json()
            usage_limit = data.get('usage_limit')
            discount = data.get('discount')
            is_active = data.get('is_active', True)
            
            await db.execute('''
                UPDATE promocodes 
                SET activation_limit = ?, percentage = ?, is_enable = ?
                WHERE id = ?
            ''', (usage_limit, discount, is_active, promo_id))
            await db.commit()
            await db.close()
            
            return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Ошибка при работе с промокодом: {e}")
        return jsonify({'error': str(e)}), 500

@promocodes_bp.route('/delete/<int:promo_id>', methods=['POST'])
async def delete_promocode(promo_id):
    try:
        db = await get_db()
        # Проверяем существование промокода
        async with db.execute('SELECT promocod FROM promocodes WHERE id = ?', (promo_id,)) as cursor:
            promo = await cursor.fetchone()
            if not promo:
                await db.close()
                return jsonify({'error': 'Промокод не найден'}), 404
        
        # Удаляем промокод
        await db.execute('DELETE FROM promocodes WHERE id = ?', (promo_id,))
        await db.commit()
        await db.close()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

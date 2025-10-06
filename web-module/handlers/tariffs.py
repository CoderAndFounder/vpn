from flask import Blueprint, render_template, jsonify, request
import aiosqlite
import os
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

tariffs_bp = Blueprint('tariffs', __name__, url_prefix='/admin/tariffs')

async def get_db():
    db_path = os.path.join(os.getcwd(), os.getenv('DATABASE_PATH'))
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    return db

@tariffs_bp.route('/')
async def tariffs_list():
    try:
        db = await get_db()
        async with db.execute('''
            SELECT t.*, s.name as server_name 
            FROM tariff t 
            LEFT JOIN server_settings s ON t.server_id = s.id
            ORDER BY t.id
        ''') as cursor:
            tariffs = await cursor.fetchall()
            tariffs_list = [dict(row) for row in tariffs]
        await db.close()
        return render_template('admin/tariffs.html', tariffs=tariffs_list)
    except Exception as e:
        logger.error(f"Ошибка при получении тарифов: {e}")
        return "Ошибка при получении тарифов", 500

@tariffs_bp.route('/edit/<int:tariff_id>', methods=['GET'])
async def get_tariff(tariff_id):
    try:
        db = await get_db()
        async with db.execute('SELECT * FROM tariff WHERE id = ?', [tariff_id]) as cursor:
            tariff = await cursor.fetchone()
        await db.close()
        return jsonify(dict(tariff))
    except Exception as e:
        logger.error(f"Ошибка при получении тарифа: {e}")
        return jsonify({"error": str(e)}), 500

@tariffs_bp.route('/edit/<int:tariff_id>', methods=['POST'])
async def update_tariff(tariff_id):
    try:
        data = request.json
        db = await get_db()
        await db.execute('''
            UPDATE tariff 
            SET name = ?, description = ?, price = ?, left_day = ?, is_enable = ?, server_id = ?
            WHERE id = ?
        ''', [
            data['name'], 
            data['description'], 
            data['price'], 
            data['left_day'], 
            data['is_enable'], 
            data['server_id'],
            tariff_id
        ])
        await db.commit()
        await db.close()
        return jsonify({"success": True})
    except Exception as e:
        logger.error(f"Ошибка при обновлении тарифа: {e}")
        return jsonify({"error": str(e)}), 500

@tariffs_bp.route('/create', methods=['POST'])
async def create_tariff():
    try:
        data = request.json
        db = await get_db()
        cursor = await db.execute('''
            INSERT INTO tariff (name, description, price, left_day, is_enable, server_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', [
            data['name'],
            data['description'],
            data['price'],
            data['left_day'],
            data['is_enable'],
            data['server_id']
        ])
        await db.commit()
        new_id = cursor.lastrowid
        await db.close()
        return jsonify({"success": True, "id": new_id})
    except Exception as e:
        logger.error(f"Ошибка при создании тарифа: {e}")
        return jsonify({"error": str(e)}), 500

@tariffs_bp.route('/servers', methods=['GET'])
async def get_servers():
    try:
        async with aiosqlite.connect(os.path.join(os.getcwd(), os.getenv('DATABASE_PATH'))) as db:
            async with db.execute('''
                SELECT id, name, ip 
                FROM server_settings 
                WHERE is_enable = 1 
                ORDER BY name
            ''') as cursor:
                servers = await cursor.fetchall()
                return jsonify([{
                    'id': row[0], 
                    'name': f"{row[1]} ({row[2] if row[2] else 'IP не указан'})"
                } for row in servers])
    except Exception as e:
        logger.error(f"Ошибка при получении списка серверов: {e}")
        return jsonify({'error': str(e)}), 500

@tariffs_bp.route('/view/<int:id>', methods=['GET'])
async def view_tariff(id):
    try:
        async with aiosqlite.connect(os.path.join(os.getcwd(), os.getenv('DATABASE_PATH'))) as db:
            async with db.execute('''
                SELECT t.*, s.name as server_name, s.ip as server_ip
                FROM tariff t 
                LEFT JOIN server_settings s ON t.server_id = s.id 
                WHERE t.id = ?
            ''', (id,)) as cursor:
                row = await cursor.fetchone()
                if row:
                    return jsonify({
                        'id': row[0],
                        'name': row[1],
                        'description': row[2],
                        'price': float(row[3]),
                        'left_day': row[4],
                        'is_enable': bool(row[5]),
                        'server_id': row[6],
                        'server_name': f"{row[7]} ({row[8]})" if row[7] else 'Не указан'
                    })
                return jsonify({'error': 'Тариф не найден'}), 404
    except Exception as e:
        logger.error(f"Ошибка при получении тарифа: {e}")
        return jsonify({'error': str(e)}), 500

@tariffs_bp.route('/delete/<int:tariff_id>', methods=['POST'])
async def delete_tariff(tariff_id):
    try:
        db = await get_db()
        # Проверяем существование тарифа
        async with db.execute('SELECT name FROM tariff WHERE id = ?', (tariff_id,)) as cursor:
            tariff = await cursor.fetchone()
            if not tariff:
                await db.close()
                return jsonify({'error': 'Тариф не найден'}), 404
        
        # Удаляем тариф
        await db.execute('DELETE FROM tariff WHERE id = ?', (tariff_id,))
        await db.commit()
        await db.close()
        
        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Ошибка при удалении тарифа: {e}")
        return jsonify({'error': str(e)}), 500

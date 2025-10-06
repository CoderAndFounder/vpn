from flask import Blueprint, jsonify, request, render_template
import aiosqlite
import os
from loguru import logger
from dotenv import load_dotenv

load_dotenv()

servers_bp = Blueprint('servers', __name__, url_prefix='/admin/servers')

async def get_db():
    db_path = os.path.join(os.getcwd(), os.getenv('DATABASE_PATH'))
    db = await aiosqlite.connect(db_path)
    db.row_factory = aiosqlite.Row
    return db

@servers_bp.route('/')
async def servers_list():
    try:
        db = await get_db()
        async with db.execute('SELECT * FROM server_settings ORDER BY id DESC') as cursor:
            servers = await cursor.fetchall()
            servers_list = [dict(row) for row in servers]
        await db.close()
        return render_template('admin/servers.html', servers=servers_list)
    except Exception as e:
        logger.error(f"Error getting servers: {e}")
        return render_template('admin/servers.html', error=str(e))

@servers_bp.route('/api/servers', methods=['GET'])
async def get_servers():
    try:
        db = await get_db()
        async with db.execute('SELECT * FROM server_settings ORDER BY id DESC') as cursor:
            servers = await cursor.fetchall()
            result = [dict(row) for row in servers]
        await db.close()
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting servers: {e}")
        return jsonify({"error": str(e)}), 500

@servers_bp.route('/api/servers/<int:server_id>', methods=['GET'])
async def get_server(server_id):
    try:
        db = await get_db()
        async with db.execute('SELECT * FROM server_settings WHERE id = ?', (server_id,)) as cursor:
            server = await cursor.fetchone()
        await db.close()
        if server:
            return jsonify(dict(server))
        return jsonify({"error": "Server not found"}), 404
    except Exception as e:
        logger.error(f"Error getting server {server_id}: {e}")
        return jsonify({"error": str(e)}), 500

@servers_bp.route('/api/servers', methods=['POST'])
async def create_server():
    try:
        data = request.json
        db = await get_db()
        query = '''INSERT INTO server_settings 
                  (name, ip, url, port, secret_path, username, password, secretkey, is_enable, inbound_id, inbound_id_promo) 
                  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)'''
        values = (
            data.get('name', 'Unnamed Server'),
            data.get('ip'),
            data['url'],
            data['port'],
            data['secret_path'],
            data['username'],
            data['password'],
            data.get('secretkey'),
            data.get('is_enable', True),
            data.get('inbound_id', 1),
            data.get('inbound_id_promo', 2)
        )
        await db.execute(query, values)
        await db.commit()
        await db.close()
        return jsonify({"message": "Server created successfully"})
    except Exception as e:
        logger.error(f"Error creating server: {e}")
        return jsonify({"error": str(e)}), 500

@servers_bp.route('/api/servers/<int:server_id>', methods=['PUT'])
async def update_server(server_id):
    try:
        data = request.json
        db = await get_db()
        query = '''UPDATE server_settings 
                  SET name=?, ip=?, url=?, port=?, secret_path=?, 
                      username=?, password=?, secretkey=?, is_enable=?,
                      inbound_id=?, inbound_id_promo=?
                  WHERE id=?'''
        values = (
            data.get('name', 'Unnamed Server'),
            data.get('ip'),
            data['url'],
            data['port'],
            data['secret_path'],
            data['username'],
            data['password'],
            data.get('secretkey'),
            data.get('is_enable', True),
            data.get('inbound_id', 1),
            data.get('inbound_id_promo', 2),
            server_id
        )
        await db.execute(query, values)
        await db.commit()
        await db.close()
        return jsonify({"message": "Server updated successfully"})
    except Exception as e:
        logger.error(f"Error updating server {server_id}: {e}")
        return jsonify({"error": str(e)}), 500

@servers_bp.route('/api/servers/<int:server_id>', methods=['DELETE'])
async def delete_server(server_id):
    try:
        db = await get_db()
        await db.execute('DELETE FROM server_settings WHERE id = ?', (server_id,))
        await db.commit()
        await db.close()
        return jsonify({"message": "Server deleted successfully"})
    except Exception as e:
        logger.error(f"Error deleting server {server_id}: {e}")
        return jsonify({"error": str(e)}), 500

@servers_bp.route('/api/servers/<int:server_id>/stats', methods=['GET'])
async def get_server_stats(server_id):
    try:
        db = await get_db()
        
        # Получаем тарифы сервера
        async with db.execute('''
            SELECT t.*, COUNT(us.id) as subscriptions_count, 
                   COALESCE(SUM(p.price), 0) as total_revenue
            FROM tariff t
            LEFT JOIN user_subscription us ON t.id = us.tariff_id AND us.server_id = ? AND us.is_active = 1
            LEFT JOIN payments p ON t.id = p.tariff_id
            WHERE t.server_id = ?
            GROUP BY t.id
        ''', (server_id, server_id)) as cursor:
            tariffs = [dict(row) for row in await cursor.fetchall()]

        # Получаем общую статистику по подпискам
        async with db.execute('''
            SELECT 
                COUNT(DISTINCT us.id) as total_subscriptions,
                COUNT(DISTINCT us.user_id) as total_users,
                COALESCE(SUM(p.price), 0) as total_revenue
            FROM user_subscription us
            LEFT JOIN payments p ON us.tariff_id = p.tariff_id
            WHERE us.server_id = ? AND us.is_active = 1
        ''', (server_id,)) as cursor:
            stats = dict(await cursor.fetchone())

        await db.close()
        return jsonify({
            "tariffs": tariffs,
            "stats": stats
        })
    except Exception as e:
        logger.error(f"Error getting server stats for server {server_id}: {e}")
        return jsonify({"error": str(e)}), 500

from flask import Flask, render_template, session, redirect, url_for, request
from dotenv import load_dotenv
import os
from loguru import logger
import aiosqlite
from handlers.admin import admin_bp
from handlers.tariffs import tariffs_bp
from handlers.promocodes import promocodes_bp
from handlers.settings import settings_bp
from handlers.messages import messages_bp
from handlers.users import users_bp
from handlers.servers import servers_bp
from handlers.trial_settings import trial_settings_bp
from handlers.payments import payments_bp
from functools import wraps

# Загрузка переменных окружения
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key')

# Функция для защиты blueprint'ов
def check_auth():
    if 'logged_in' not in session and request.endpoint != 'login':
        return redirect(url_for('login'))

# Маршрут для авторизации
@app.route('/login', methods=['GET', 'POST'])
async def login():
    if 'logged_in' in session:
        return redirect(url_for('admin.admin_dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if email == os.getenv('admin_email') and password == os.getenv('admin_password'):
            session['logged_in'] = True
            return redirect(url_for('admin.admin_dashboard'))
        else:
            return render_template('login.html', error='Неверные учетные данные')
    
    return render_template('login.html')

# Маршрут для выхода
@app.route('/logout')
async def logout():
    session.pop('logged_in', None)
    return redirect(url_for('login'))

@app.route('/')
async def index():
    if 'logged_in' not in session:
        return redirect(url_for('login'))
    return render_template('index.html')

# Сначала настраиваем защиту для blueprint'ов
for blueprint in [admin_bp, tariffs_bp, promocodes_bp, settings_bp, 
                 messages_bp, users_bp, servers_bp, trial_settings_bp, 
                 payments_bp]:
    blueprint.before_request(check_auth)

# Затем регистрируем их
app.register_blueprint(admin_bp)
app.register_blueprint(tariffs_bp)
app.register_blueprint(promocodes_bp)
app.register_blueprint(settings_bp)
app.register_blueprint(messages_bp)
app.register_blueprint(users_bp)
app.register_blueprint(servers_bp)
app.register_blueprint(trial_settings_bp)
app.register_blueprint(payments_bp)

if __name__ == '__main__':
    logger.add("logs/app.log", rotation="500 MB")
    app.run(host='0.0.0.0', port=16389, debug=True)

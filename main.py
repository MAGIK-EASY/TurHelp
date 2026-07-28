from flask import Flask, render_template, url_for, request, redirect, session, flash, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from contextlib import contextmanager
from admin_routes import admin_bp
import os
from PIL import Image
import base64
import re
from io import BytesIO

app = Flask(__name__)
app.secret_key = b'try_hack_this'
app.permanent_session_lifetime = timedelta(days=30) # Сессия на 30 дней для "Запомнить меня"

# Импортируем и регистрируем Blueprint для админ-панели
app.register_blueprint(admin_bp)

# Константа с данными администратора
ADMIN_CREDENTIALS = {
    'number': '0000',
    'password': "scrypt:32768:8:1$rYSEXfO2KSVrC5Pc$0a56f6f8f27bb47366695e58bbd8286fc4001e8de87fe14496eb1d4727bd7ae28c0a9af6123be0377ad75e9c9d97e26c8181249f68268e7a48a009ffcc79a46b"
    # pass: you_shall_not_pass_321$
}

# Контекстный менеджер для работы с базой данных с поддержкой транзакций
@contextmanager
def db_connection():
    conn = None
    try:
        conn = sqlite3.connect('turhelp.db')
        conn.execute("PRAGMA foreign_keys = ON")  # Включаем поддержку внешних ключей
        cursor = conn.cursor()
        yield cursor
        conn.commit()
    except sqlite3.Error as e:
        if conn:
            conn.rollback()
        app.logger.error(f"Database error: {str(e)}")
        raise
    finally:
        if conn:
            conn.close()


# Роут для работы карточек на главной странице
@app.route('/Choosing_tour')
def tour_page():
    tour_id = request.args.get('tour_id')
    name = request.args.get('name', '')
    address = request.args.get('address', '')
    country = request.args.get('country', '')
    duration = request.args.get('duration', '')
    price = request.args.get('price', '')
    description = request.args.get('description', '')
    image = request.args.get('image', 'default.jpg')

    return render_template("Choosing_tour.html",
                           tour_id=tour_id,
                           name=name,
                           address=address,
                           country=country,
                           duration=duration,
                           price=price,
                           description=description,
                           image=image)

UPLOAD_FOLDER = 'static/uploads/avatars'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024  # 5MB max

# Создаем папку для аватаров, если её нет
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def save_avatar(file, user_id):
    """Сохраняет аватар и возвращает путь к нему"""
    try:
        print(f"DEBUG: save_avatar called with type: {type(file)}")

        # Проверяем, пришел ли файл как base64 или обычный файл
        if isinstance(file, str) and file.startswith('data:image'):
            print("DEBUG: Processing base64 image")
            # Это base64 изображение
            image_data = re.sub('^data:image/.+;base64,', '', file)
            image_bytes = base64.b64decode(image_data)
            file = BytesIO(image_bytes)
            ext = 'jpg'
        elif hasattr(file, 'filename') and file and allowed_file(file.filename):
            print(f"DEBUG: Processing uploaded file: {file.filename}")
            # Это обычный файл
            ext = file.filename.rsplit('.', 1)[1].lower()
        else:
            print(f"DEBUG: Unknown file type: {type(file)}")
            return None

        # Генерируем уникальное имя файла
        filename = f"avatar_{user_id}_{datetime.now().strftime('%Y%m%d%H%M%S')}.{ext}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        print(f"DEBUG: Saving to: {filepath}")

        # Открываем изображение
        img = Image.open(file)
        print(f"DEBUG: Image opened, mode: {img.mode}, size: {img.size}")

        # Конвертируем в RGB если нужно
        if img.mode in ('RGBA', 'LA', 'P'):
            bg = Image.new('RGB', img.size, (255, 255, 255))
            if img.mode == 'P':
                img = img.convert('RGBA')
            bg.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
            img = bg
        elif img.mode != 'RGB':
            img = img.convert('RGB')

        # Сохраняем
        img.save(filepath, optimize=True, quality=85)
        print(f"DEBUG: Image saved successfully")

        return f"/static/uploads/avatars/{filename}"

    except Exception as e:
        print(f"ERROR in save_avatar: {str(e)}")
        import traceback
        traceback.print_exc()
        app.logger.error(f"Error saving avatar: {str(e)}")
        return None


def normalize_phone_number(phone):
    if not phone:
        return phone

    # Удаляем все нецифровые символы
    cleaned = re.sub(r'[^\d]', '', phone.strip())

    # Если номер начинается с 8, заменяем на 7
    if cleaned.startswith('8'):
        cleaned = '7' + cleaned[1:]

    # Если номер начинается с 7, оставляем как есть
    # Если номер пустой или слишком короткий, возвращаем как есть
    return cleaned

# Роут для страницы профиля
@app.route('/profile')
def profile():
    if 'user_id' not in session:
        flash('Для доступа к профилю необходимо войти', 'warning')
        return redirect(url_for('login'))

    try:
        conn = sqlite3.connect('turhelp.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Получаем данные пользователя по ID
        cursor.execute("""
            SELECT id, name, surname, thname, birthday, tnumber, avatar, regdate 
            FROM Clients 
            WHERE id = ?
        """, (session['user_id'],))
        user_data = cursor.fetchone()

        if not user_data:
            flash('Пользователь не найден', 'danger')
            conn.close()
            return redirect(url_for('home'))

        user = {
            'id': user_data['id'],
            'name': user_data['name'],
            'surname': user_data['surname'],
            'thname': user_data['thname'] or '',
            'birthday': user_data['birthday'] or '',
            'tnumber': user_data['tnumber'],
            'avatar': user_data['avatar'] or '/static/images/default-avatar.png',
            'regdate': user_data['regdate']
        }

        # Получаем отзывы пользователя
        cursor.execute("""
            SELECT r.id, r.stars, r.description, r.date, t.country, t.id as tour_id
            FROM reviews r
            JOIN Tours t ON r.tourid = t.id
            WHERE r.clientid = ?
            ORDER BY r.date DESC
        """, (user['id'],))
        reviews_data = cursor.fetchall()

        user_reviews = []
        for review in reviews_data:
            user_reviews.append({
                'id': review['id'],
                'stars': review['stars'],
                'description': review['description'],
                'date': review['date'],
                'country': review['country'],
                'tour_id': review['tour_id']
            })

        conn.close()

        return render_template("profile.html",
                               user=user,
                               reviews=user_reviews,
                               user_name=session['user_name'],
                               is_authenticated=True,
                               is_admin=session.get('is_admin', False))

    except Exception as e:
        app.logger.error(f"Error loading profile: {str(e)}")
        flash('Ошибка при загрузке профиля', 'danger')
        return redirect(url_for('home'))


# Роут для обновления профиля
@app.route('/profile/update', methods=['POST'])
def update_profile():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401

    try:
        name = request.form.get('name', '').strip()
        surname = request.form.get('surname', '').strip()
        thname = request.form.get('thname', '').strip()
        birthday = request.form.get('birthday', '').strip()
        tnumber = request.form.get('tnumber', '').strip()
        cropped_image = request.form.get('cropped_image', '')

        # Нормализуем номер телефона
        tnumber = normalize_phone_number(tnumber)

        if len(tnumber) != 11:
            return jsonify({'success': False, 'error': 'Введите корректный номер телефона'}), 400

        if not all([name, surname, tnumber]):
            return jsonify({'success': False, 'error': 'Имя, фамилия и телефон обязательны'}), 400

        conn = sqlite3.connect('turhelp.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        user_id = session['user_id']

        # Проверяем, не занят ли номер телефона другим пользователем
        cursor.execute("SELECT id FROM Clients WHERE tnumber = ? AND id != ?", (tnumber, user_id))
        if cursor.fetchone():
            conn.close()
            return jsonify({'success': False, 'error': 'Этот номер телефона уже используется'}), 400

        # Обработка аватара
        avatar_path = None

        if cropped_image and cropped_image.startswith('data:image'):
            avatar_path = save_avatar(cropped_image, user_id)
        elif 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename:
                avatar_path = save_avatar(file, user_id)

        if avatar_path:
            cursor.execute("""
                UPDATE Clients 
                SET name = ?, surname = ?, thname = ?, birthday = ?, tnumber = ?, avatar = ?
                WHERE id = ?
            """, (name, surname, thname if thname else None,
                  birthday if birthday else None, tnumber, avatar_path, user_id))
        else:
            cursor.execute("""
                UPDATE Clients 
                SET name = ?, surname = ?, thname = ?, birthday = ?, tnumber = ?
                WHERE id = ?
            """, (name, surname, thname if thname else None,
                  birthday if birthday else None, tnumber, user_id))

        conn.commit()
        conn.close()

        # Обновляем имя в сессии, если оно изменилось
        if session.get('user_name') != name:
            session['user_name'] = name

        return jsonify({'success': True, 'message': 'Профиль успешно обновлен'})

    except Exception as e:
        app.logger.error(f"Error updating profile: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Роут для изменения пароля
@app.route('/profile/change-password', methods=['POST'])
def change_password():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401

    try:
        data = request.get_json()
        current_password = data.get('current_password', '')
        new_password = data.get('new_password', '')

        if not current_password or not new_password:
            return jsonify({'success': False, 'error': 'Все поля обязательны'}), 400

        if len(new_password) < 8:
            return jsonify({'success': False, 'error': 'Пароль должен быть не менее 8 символов'}), 400

        conn = sqlite3.connect('turhelp.db')
        cursor = conn.cursor()

        cursor.execute("SELECT password FROM Clients WHERE id = ?", (session['user_id'],))
        user = cursor.fetchone()

        if not user:
            conn.close()
            return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404

        # Проверяем текущий пароль
        if not check_password_hash(user[0], current_password):
            conn.close()
            return jsonify({'success': False, 'error': 'Неверный текущий пароль'}), 400

        # Хешируем новый пароль
        new_hash = generate_password_hash(new_password)

        # Обновляем пароль
        cursor.execute("UPDATE Clients SET password = ? WHERE id = ?",
                       (new_hash, session['user_id']))

        conn.commit()
        conn.close()

        return jsonify({'success': True, 'message': 'Пароль успешно изменен'})

    except Exception as e:
        app.logger.error(f"Error changing password: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Роут главной страницы
@app.route('/')
def home():
  with db_connection() as cursor:
    cursor.execute("SELECT DISTINCT city FROM Agency ORDER BY city")
    raw_cities = cursor.fetchall()
    cities = [city[0] for city in raw_cities]
    cursor.execute("SELECT DISTINCT country FROM Tours ORDER BY country")
    raw_countries = cursor.fetchall()
    countries = [country[0] for country in raw_countries]

  if 'user_name' in session:
    # Пользователь авторизован - показываем персональную страницу
    return render_template("homepage.html", cities=cities, countries = countries,
                           user_name=session['user_name'],
                           is_authenticated=True)
  else:
    # Неавторизованный пользователь
    return render_template("homepage.html", cities=cities, countries = countries, is_authenticated=False)


# Роут для выбора тура на главной странице
@app.route('/search_tours', methods=['POST'])
def search_tours():
    data = request.get_json()
    city = data.get('city')
    country = data.get('country')

    conn = sqlite3.connect('turhelp.db')
    cursor = conn.cursor()

    query = """
    SELECT 
        Tours.id, 
        Agency.name, 
        Agency.address, 
        Tours.country,
        Tours.description,
        Tours.price,
        Tours.duration
    FROM Agency
    INNER JOIN Tours ON Agency.id = Tours.agencyid
    WHERE Agency.city = ? AND Tours.country = ?
    """
    
    cursor.execute(query, (city, country))
    results = cursor.fetchall()
    conn.close()

    agencies = []
    for row in results:
        agencies.append({
            'id': row[0],
            'name': row[1],
            'address': row[2],
            'country': row[3],
            'description': row[4],
            'price': row[5],
            'duration': row[6]
        })

    return jsonify({'agencies': agencies})


# Роут для регистрации
@app.route('/registrations', methods=['GET', 'POST'])
def registrations():
    if request.method == 'POST':
        try:
            name = request.form.get('name', '').strip()
            surname = request.form.get('surname', '').strip()
            thname = request.form.get('thname', '').strip()
            birthday = request.form.get('birthday', '').strip()
            number = request.form.get('number', '').strip()
            password = request.form.get('password', '').strip()

            # НОРМАЛИЗУЕМ НОМЕР ТЕЛЕФОНА (удаляем плюс, 8->7)
            number = normalize_phone_number(number)

            # Проверка, что номер содержит 11 цифр
            if len(number) != 11:
                error_msg = 'Введите корректный номер телефона (10 цифр после 7 или 8)'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'error': error_msg})
                flash(error_msg, 'danger')
                return render_template('registrations.html')

            # Проверка обязательных полей
            if not all([name, surname, birthday, number, password]):
                error_msg = 'Все поля кроме отчества обязательны для заполнения'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'error': error_msg})
                flash(error_msg, 'danger')
                return render_template('registrations.html')

            # Проверка длины пароля
            if len(password) < 8:
                error_msg = 'Пароль должен быть не менее 8 символов'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'error': error_msg})
                flash(error_msg, 'danger')
                return render_template('registrations.html')

            hashpass = generate_password_hash(password)
            regdate = datetime.now().strftime("%Y-%m-%d")

            conn = sqlite3.connect('turhelp.db')
            cursor = conn.cursor()

            # Проверяем, есть ли уже такой номер
            cursor.execute("SELECT id FROM Clients WHERE tnumber = ?", (number,))
            if cursor.fetchone():
                conn.close()
                error_msg = 'Этот номер телефона уже зарегистрирован'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'error': error_msg})
                flash(error_msg, 'warning')
                return render_template('registrations.html')

            # Регистрируем нового пользователя
            cursor.execute(
                "INSERT INTO Clients (name, surname, thname, birthday, tnumber, password, regdate) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (name, surname, thname, birthday, number, hashpass, regdate)
            )
            conn.commit()

            # Получаем ID нового пользователя
            user_id = cursor.lastrowid
            conn.close()

            # Авторизуем пользователя
            session['user_id'] = user_id
            session['user_name'] = name
            session['is_admin'] = False

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': 'Регистрация успешна'})

            return redirect(url_for('home'))

        except sqlite3.IntegrityError as e:
            error_msg = 'Ошибка регистрации: пользователь с такими данными уже существует'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': error_msg})
            flash(error_msg, 'danger')
            return render_template('registrations.html')
        except Exception as e:
            app.logger.error(f"Registration error: {str(e)}")
            error_msg = 'Произошла ошибка при регистрации'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': error_msg})
            flash(error_msg, 'danger')
            return render_template('registrations.html')

    return render_template("registrations.html")


# Роут для логина
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        number = request.form.get('number', '').strip()
        password = request.form.get('password', '').strip()

        number = normalize_phone_number(number)

        # Проверка обязательных полей
        if not number or not password:
            error_msg = 'Введите номер телефона и пароль'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': error_msg})
            flash(error_msg, 'danger')
            return render_template('login.html')

        # Проверяем админа
        if number == ADMIN_CREDENTIALS['number'] and check_password_hash(ADMIN_CREDENTIALS['password'], password):
            session['user_id'] = 0
            session['user_name'] = 'Администратор'
            session['is_admin'] = True
            if request.form.get('remember-me'):
                session.permanent = True

            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': True, 'message': 'Вход выполнен'})
            return redirect(url_for('admin_bp.admin_panel'))

        conn = sqlite3.connect('turhelp.db')
        cursor = conn.cursor()

        # Ищем пользователя по номеру телефона
        cursor.execute("SELECT id, name, password FROM Clients WHERE tnumber = ?", (number,))
        user = cursor.fetchone()
        conn.close()

        if user:
            user_id, user_name, stored_password = user
            if check_password_hash(stored_password, password):
                session['user_id'] = user_id
                session['user_name'] = user_name
                session['is_admin'] = False

                if request.form.get('remember-me'):
                    session.permanent = True

                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': True, 'message': 'Вход выполнен'})

                return redirect(url_for('home'))
            else:
                error_msg = 'Неверный пароль'
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return jsonify({'success': False, 'error': error_msg})
                flash(error_msg, 'danger')
        else:
            error_msg = 'Пользователь с таким номером не найден'
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return jsonify({'success': False, 'error': error_msg})
            flash(error_msg, 'danger')

        return render_template("login.html", number=number)

    return render_template("login.html")


# Роут для выхода из профиля пользователя
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))


# Роут для ссылки на статистику
@app.route('/stats')
def stats_page():
    try:
        with db_connection() as cursor:
            # Статистика новых пользователей
            one_week_ago = datetime.now() - timedelta(days=7)
            cursor.execute("SELECT COUNT(*) FROM Clients WHERE regdate >= ?",
                         (one_week_ago.strftime('%Y-%m-%d'),))
            new_users_count = cursor.fetchone()[0]

            # Получаем список популярных туров с максимальным рейтингом
            cursor.execute("""
                WITH top_tours AS (
                    SELECT t.id, t.country, t.description, t.price, t.duration,
                           a.name as agency_name, a.address,
                           AVG(r.stars) as avg_rating, 
                           COUNT(r.id) as reviews_count,
                           RANK() OVER (ORDER BY AVG(r.stars) DESC, COUNT(r.id) DESC) as rating_rank
                    FROM Tours t
                    LEFT JOIN reviews r ON t.id = r.tourid
                    LEFT JOIN Agency a ON t.agencyid = a.id
                    GROUP BY t.id
                )
                SELECT id, country, description, price, duration, agency_name, address, 
                       ROUND(avg_rating, 1) as avg_rating, reviews_count
                FROM top_tours
                WHERE rating_rank = 1
                ORDER BY country ASC
            """)
            
            popular_tours = []
            for row in cursor.fetchall():
                popular_tours.append({
                    'id': row[0],
                    'country': row[1],
                    'description': row[2],
                    'price': row[3],
                    'duration': row[4],
                    'agency_name': row[5],
                    'address': row[6],
                    'avg_rating': row[7],
                    'reviews_count': row[8]
                })

                # Получаем рейтинг агентств
                cursor.execute("""
                    SELECT a.name, ROUND(AVG(r.stars), 1) as avg_rating, COUNT(DISTINCT t.id) as tours_count, COUNT(r.id) as reviews_count
                    FROM Agency a
                    LEFT JOIN Tours t ON a.id = t.agencyid
                    LEFT JOIN reviews r ON t.id = r.tourid
                    GROUP BY a.id
                    ORDER BY avg_rating DESC
                    LIMIT 10
                """)
                agencies_ratings = []
                for row in cursor.fetchall():
                    agencies_ratings.append({
                        'name': row[0],
                        'avg_rating': row[1],
                        'tours_count': row[2],
                        'reviews_count': row[3]
                    })

        return render_template("stats.html",
            new_users_count=new_users_count,
            popular_tours=popular_tours,
            agencies_ratings=agencies_ratings,
            user_name=session.get('user_name'),
            is_authenticated='user_name' in session)

    except Exception as e:
        app.logger.error(f"Error fetching stats: {str(e)}")
        flash('Произошла ошибка при загрузке статистики', 'danger')
        return redirect(url_for('home'))


# Роут для ссылки на страницу "О нас"
@app.route('/about')
def about():
  if 'user_name' in session:
    return render_template("about.html", user_name=session['user_name'], is_authenticated=True)
  else:
    return render_template("about.html", is_authenticated=False)


# Роут для получения отзывов из базы данных для конкретного тура
@app.route('/get_reviews/<int:tour_id>')
def get_reviews(tour_id):
    try:
        with db_connection() as cursor:
            cursor.execute("""
                SELECT r.id, r.stars, r.description, r.date, 
                       c.name, c.surname, c.avatar, c.id as client_id
                FROM reviews r
                JOIN Clients c ON r.clientid = c.id
                WHERE r.tourid = ?
                ORDER BY r.date DESC
            """, (tour_id,))
            reviews = cursor.fetchall()

        formatted_reviews = []
        for review in reviews:
            full_name = f"{review[5] or ''} {review[4] or ''}".strip()
            if not full_name:
                full_name = 'Аноним'

            formatted_reviews.append({
                'id': review[0],
                'stars': review[1],
                'description': review[2],
                'date': review[3],
                'full_name': full_name,  # Только для отображения
                'avatar': review[6] if review[6] else '/static/images/default-avatar.png',
                'client_id': review[7]   # Только для проверки прав
            })

        return jsonify({'reviews': formatted_reviews})
    except Exception as e:
        return jsonify({'reviews': [], 'error': str(e)}), 500

# Роут для добавления отзыва
@app.route('/add_review', methods=['POST'])
def add_review():
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401

    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'error': 'Неверный формат данных'}), 400

    tour_id = data.get('tour_id')
    stars = data.get('stars')
    description = data.get('description', '').strip()

    if not all([tour_id, stars]) or not description:
        return jsonify({'success': False, 'error': 'Не все обязательные поля заполнены'}), 400

    try:
        with db_connection() as cursor:
            client_id = session['user_id']

            # Добавляем отзыв
            cursor.execute("""
                INSERT INTO reviews (tourid, clientid, stars, description, date)
                VALUES (?, ?, ?, ?, DATE('now'))
            """, (tour_id, client_id, stars, description))

        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error adding review: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Роут для удаления пользователем отзыва
@app.route('/delete_review/<int:review_id>', methods=['DELETE'])
def delete_review(review_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401

    try:
        with db_connection() as cursor:
            # Проверяем, принадлежит ли отзыв текущему пользователю
            cursor.execute("""
                SELECT clientid 
                FROM reviews 
                WHERE id = ?
            """, (review_id,))
            result = cursor.fetchone()

            if not result:
                return jsonify({'success': False, 'error': 'Отзыв не найден'}), 404

            review_owner_id = result[0]

            # Разрешаем удалять либо автору, либо админу
            if review_owner_id != session['user_id'] and not session.get('is_admin', False):
                return jsonify({'success': False, 'error': 'Недостаточно прав'}), 403

            # Удаляем отзыв
            cursor.execute("DELETE FROM reviews WHERE id = ?", (review_id,))

        return jsonify({'success': True})
    except Exception as e:
        app.logger.error(f"Error deleting review: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


# Роут для получение среднего рейтинга тура
@app.route('/get_tour_rating/<int:tour_id>')
def get_tour_rating(tour_id):
    try:
        with db_connection() as cursor:
            # Получаем средний рейтинг и количество отзывов
            cursor.execute("""
                SELECT AVG(stars), COUNT(*) 
                FROM reviews 
                WHERE tourid = ?
            """, (tour_id,))
            result = cursor.fetchone()

            if result and result[1] > 0:  # Если есть отзывы
                avg_rating = round(result[0], 1)
                reviews_count = result[1]
                return jsonify({
                    'success': True,
                    'avg_rating': avg_rating,
                    'reviews_count': reviews_count
                })
            else:  # Если отзывов нет
                return jsonify({
                    'success': True,
                    'avg_rating': 0,
                    'reviews_count': 0
                })
    except Exception as e:
        app.logger.error(f"Error fetching tour rating: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/get_tour_rating_distribution/<int:tour_id>')
def get_tour_rating_distribution(tour_id):
    try:
        with db_connection() as cursor:
            cursor.execute("""
                SELECT stars, COUNT(*) as count
                FROM reviews
                WHERE tourid = ?
                GROUP BY stars
                ORDER BY stars DESC
            """, (tour_id,))
            distribution = cursor.fetchall()

            # Заполняем все оценки от 1 до 5
            result = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
            for row in distribution:
                result[row[0]] = row[1]

            # Вычисляем общее количество отзывов
            total_reviews = sum(result.values())

            return jsonify({
                'success': True,
                'distribution': result,
                'total_reviews': total_reviews  # <-- ДОБАВЛЕНО
            })
    except Exception as e:
        app.logger.error(f"Error in get_tour_rating_distribution: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500


if __name__ == '__main__':
  app.run(debug=True)
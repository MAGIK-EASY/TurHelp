from flask import Flask, render_template, url_for, request, redirect, session, flash, jsonify
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
from contextlib import contextmanager
from flask import send_from_directory
from admin_routes import admin_bp

# Установка зависимостей: pip install -r requirements.txt

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
    price = request.args.get('price', '')
    description = request.args.get('description', '')
    image = request.args.get('image', 'default.jpg')

    return render_template("Choosing_tour.html",
                           tour_id=tour_id,
                           name=name,
                           address=address,
                           country=country,
                           price=price,
                           description=description,
                           image=image)


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

    # Ищем агентства в выбранном городе с турами в выбранную страну
    query = """
    SELECT 
        Agency.id, 
        Agency.name, 
        Agency.address, 
        Agency.information,
        Tours.country,
        Tours.description,
        Tours.price
    FROM Agency
    INNER JOIN Tours ON Agency.id = Tours.agencyid
    WHERE Agency.city = ? AND Tours.country = ?
    """

    cursor.execute(query, (city, country))
    results = cursor.fetchall()
    conn.close()

    # Формируем ответ
    agencies = []
    for row in results:
        agencies.append({
            'id': row[0],
            'name': row[1],
            'address': row[2],
            'information': row[3],
            'country': row[4],
            'description': row[5],
            'price': row[6]
        })

    return jsonify({'agencies': agencies})


# Роут для Регистрации
@app.route('/registrations', methods=['GET', 'POST'])
def registrations():
  try:
    if request.method == 'POST':
      # Получаем данные из формы
      name = request.form.get('name', '').strip()
      surname = request.form.get('surname', '').strip()
      thname = request.form.get('thname', '').strip()
      birthday = request.form.get('birthday', '').strip()
      number = request.form.get('number', '').strip()
      password = request.form.get('password', '').strip()

      hashpass = generate_password_hash(password) # Хэшированный пароль

      conn = sqlite3.connect('turhelp.db')
      cursor = conn.cursor()

      # Проверяем, есть ли уже такой номер
      cursor.execute("SELECT id FROM Clients WHERE tnumber = ?", (number,))
      if cursor.fetchone():
        flash('Этот номер телефона уже зарегистрирован. Хотите войти?', 'warning')

      # Регистрируем нового пользователя
      cursor.execute("INSERT INTO Clients (name, surname, thname, birthday, tnumber, password) VALUES (?, ?, ?, ?, ?, ?)", (name, surname, thname, birthday, number, hashpass)) #""
      conn.commit()

      # Авторизуем пользователя
      session['user_name'] = name
      conn.close()

      return redirect(url_for('home'))

    return render_template("registrations.html")

  except sqlite3.IntegrityError:
    flash('Ошибка регистрации')
    return render_template('registrations.html')


# Роут для логина(вход в аккаунт)
@app.route('/login', methods=['GET', 'POST'])
def login():
  if request.method == 'POST':
    # Получаем данные из формы
    number = request.form.get('number', '').strip()
    password = request.form.get('password', '').strip()

    # Сначала проверяем, не это ли администратор
    if number == ADMIN_CREDENTIALS['number'] and check_password_hash(ADMIN_CREDENTIALS['password'], password):
        session['user_name'] = 'Администратор'
        session['is_admin'] = True
        if request.form.get('remember-me'):
            session.permanent = True
        return redirect(url_for('admin_bp.admin_panel'))

    conn = sqlite3.connect('turhelp.db')
    cursor = conn.cursor()

    # Ищем пользователя в базе данных
    cursor.execute("SELECT name, tnumber, password FROM Clients WHERE tnumber = ?", (number,))
    user = cursor.fetchone() # берет кортеж данных
    conn.close()

    if user:
      stored_name, stored_number, stored_password = user
      # Проверяем пароль (в нашей текущей реализации пароли хранятся в зашифрованном виде)
      if check_password_hash(stored_password, password):
        # Устанавливаем сессию
        session['user_name'] = stored_name

        # Обработка "Запомнить меня"
        if request.form.get('remember-me'):
          session.permanent = True

        return redirect(url_for('home'))
      else:
        flash('Неверный пароль', 'danger')
    else:
      flash('Пользователь с таким номером не найден', 'danger')

    return render_template("login.html", number=number)

  # GET запрос - просто отображаем форму
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
            # Получаем статистику
            cursor.execute("SELECT COUNT(*) FROM Clients WHERE date(birthday) >= date('now', '-1 month')")
            new_users_count = cursor.fetchone()[0]

            cursor.execute("""
                SELECT t.id, t.country, t.description, t.price, a.name as agency_name, a.address,
                       AVG(r.stars) as avg_rating, COUNT(r.id) as reviews_count
                FROM Tours t
                LEFT JOIN reviews r ON t.id = r.tourid
                LEFT JOIN Agency a ON t.agencyid = a.id
                GROUP BY t.id
                ORDER BY avg_rating DESC, reviews_count DESC
                LIMIT 1
            """)
            popular_tour = cursor.fetchone()

            if popular_tour and popular_tour[6] is not None:  # Проверяем avg_rating
                tour_data = {
                    'id': popular_tour[0],
                    'country': popular_tour[1],
                    'description': popular_tour[2],
                    'price': popular_tour[3],
                    'agency_name': popular_tour[4],
                    'address': popular_tour[5],
                    'avg_rating': round(popular_tour[6], 1),
                    'reviews_count': popular_tour[7]
                }
            else:
                tour_data = None

        return render_template("stats.html",
                               new_users_count=new_users_count,
                               popular_tour=tour_data,
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
                SELECT r.id, r.stars, r.description, r.date, c.name 
                FROM reviews r
                JOIN Clients c ON r.clientid = c.id
                WHERE r.tourid = ?
                ORDER BY r.date DESC
            """, (tour_id,))
            reviews = cursor.fetchall()

        if not reviews:  # Если отзывов нет
            return jsonify({'reviews': []})

        # Форматируем отзывы для отправки
        formatted_reviews = []
        for review in reviews:
            formatted_reviews.append({
                'id': review[0],
                'stars': review[1],
                'description': review[2],
                'date': review[3],
                'author': review[4] if review[4] else 'Аноним'
            })

        return jsonify({'reviews': formatted_reviews})

    except Exception as e:
        app.logger.error(f"Error fetching reviews: {str(e)}")
        return jsonify({'reviews': [], 'error': str(e)}), 500

# Роут для добавления отзыва
@app.route('/add_review', methods=['POST'])
def add_review():
    if 'user_name' not in session:
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
            # Получаем ID клиента
            cursor.execute("SELECT id FROM Clients WHERE name = ?", (session['user_name'],))
            client_data = cursor.fetchone()

            if not client_data:
                return jsonify({'success': False, 'error': 'Пользователь не найден'}), 404

            client_id = client_data[0]

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
    # Удаление отзыва
    if 'user_name' not in session:
        return jsonify({'success': False, 'error': 'Требуется авторизация'}), 401

    try:
        with db_connection() as cursor:
            # Проверяем, принадлежит ли отзыв текущему пользователю
            cursor.execute("""
                SELECT c.name 
                FROM reviews r
                JOIN Clients c ON r.clientid = c.id
                WHERE r.id = ?
            """, (review_id,))
            review_owner = cursor.fetchone()

            if not review_owner:
                return jsonify({'success': False, 'error': 'Отзыв не найден'}), 404

            # Разрешаем удалять либо автору, либо админу
            if review_owner[0] != session['user_name'] and not session.get('is_admin', False):
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

if __name__ == '__main__':
  app.run(debug=True)
from flask import Blueprint, render_template, session, redirect, url_for, flash, request
from functools import wraps
import sqlite3
from openpyxl import Workbook
from flask import make_response
from io import BytesIO

#Создаем Blueprint для админских маршрутов
admin_bp = Blueprint('admin_bp', __name__, template_folder='templates')

# Создает и возвращает соединение с базой данных
def get_db_connection():
    conn = sqlite3.connect('turhelp.db')
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# Декоратор для проверки прав администратора
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            flash('Доступ запрещен', 'danger')
            return redirect(url_for('home'))
        return f(*args, **kwargs)
    return decorated_function


# Главная страница админ-панели
@admin_bp.route('/admin')
@admin_required
def admin_panel():
    return render_template("admin.html",
                         user_name=session['user_name'],
                         is_authenticated=True)


# Управление пользователями
@admin_bp.route('/admin/clients')
@admin_required
def manage_clients():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, surname, name, thname, birthday, tnumber, regdate FROM Clients")
    clients = cursor.fetchall()
    conn.close()
    return render_template("admin_clients.html",
                         clients=clients,
                         user_name=session['user_name'],
                         is_authenticated=True)

@admin_bp.route('/admin/clients/delete/<int:client_id>', methods=['POST'])
@admin_required
def delete_client(client_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Clients WHERE id = ?", (client_id,))
        conn.commit()
        flash('Пользователь успешно удален', 'success')
    except sqlite3.Error as e:
        flash(f'Ошибка при удалении пользователя: {str(e)}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('admin_bp.manage_clients'))

# Редактирование пользователя
@admin_bp.route('/admin/clients/edit/<int:client_id>', methods=['GET', 'POST'])
@admin_required
def edit_client(client_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        surname = request.form.get('surname')
        name = request.form.get('name')
        thname = request.form.get('thname')
        birthday = request.form.get('birthday')
        tnumber = request.form.get('tnumber')

        try:
            cursor.execute("""
                UPDATE Clients 
                SET surname=?, name=?, thname=?, birthday=?, tnumber=?
                WHERE id=?
            """, (surname, name, thname, birthday, tnumber, client_id))
            conn.commit()
            flash('Данные пользователя успешно обновлены', 'success')
            return redirect(url_for('admin_bp.manage_clients'))
        except sqlite3.Error as e:
            flash(f'Ошибка при обновлении пользователя: {str(e)}', 'danger')
        finally:
            conn.close()

    # GET запрос - показываем форму
    cursor.execute("SELECT id, surname, name, thname, birthday, tnumber FROM Clients WHERE id=?", (client_id,))
    client_data = cursor.fetchone()
    conn.close()

    if not client_data:
        flash('Пользователь не найден', 'danger')
        return redirect(url_for('admin_bp.manage_clients'))

    # Преобразуем в словарь с правильным порядком полей
    client = {
        'id': client_data[0],
        'surname': client_data[1],  # Фамилия
        'name': client_data[2],  # Имя
        'thname': client_data[3],  # Отчество
        'birthday': client_data[4],
        'tnumber': client_data[5]
    }

    return render_template("edit_client.html",
                           client=client,
                           user_name=session['user_name'],
                           is_authenticated=True)

# Управление турами
@admin_bp.route('/admin/tours')
@admin_required
def manage_tours():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, country, agencyid, duration, price, description FROM Tours")
    tours = cursor.fetchall()
    conn.close()
    return render_template("admin_tours.html",
                         tours=tours,
                         user_name=session['user_name'],
                         is_authenticated=True)


@admin_bp.route('/admin/tours/add', methods=['GET', 'POST'])
@admin_required
def add_tour():
    # Получаем список агентств для выпадающего списка
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM Agency")
    agencies = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
    conn.close()

    if request.method == 'POST':
        country = request.form.get('country')
        agencyid = request.form.get('agencyid')
        duration = request.form.get('duration')
        price = request.form.get('price')
        description = request.form.get('description')

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Tours (country, agencyid, duration, price, description) VALUES (?, ?, ?, ?, ?)",
                (country, agencyid, duration, price, description)
            )
            conn.commit()
            flash('Тур успешно добавлен', 'success')
            return redirect(url_for('admin_bp.manage_tours'))
        except sqlite3.Error as e:
            flash(f'Ошибка при добавлении тура: {str(e)}', 'danger')
        finally:
            conn.close()

    return render_template("add_tour.html",
                         agencies=agencies,
                         user_name=session['user_name'],
                         is_authenticated=True)

@admin_bp.route('/admin/tours/delete/<int:tour_id>', methods=['POST'])
@admin_required
def delete_tour(tour_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Tours WHERE id = ?", (tour_id,))
        conn.commit()
        flash('Тур успешно удален', 'success')
    except sqlite3.Error as e:
        flash(f'Ошибка при удалении тура: {str(e)}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('admin_bp.manage_tours'))

# Скачиваем Excel
@admin_bp.route('/admin/tours/export')
@admin_required
def export_tours():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Tours")
        tours = cursor.fetchall()
        cursor.execute("PRAGMA table_info(Tours)")
        columns = [column[1] for column in cursor.fetchall()]
        conn.close()

        # Создаем Excel файл
        wb = Workbook()
        ws = wb.active
        ws.title = "Туры"

        # Заголовки
        ws.append(columns)

        # Данные
        for tour in tours:
            ws.append(tour)

        # Сохраняем в буфер
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        # Создаем ответ
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename=tours_export.xlsx'
        return response

    except Exception as e:
        flash(f'Ошибка при экспорте: {str(e)}', 'danger')
        return redirect(url_for('admin_bp.manage_tours'))


# Редактирование тура
@admin_bp.route('/admin/tours/edit/<int:tour_id>', methods=['GET', 'POST'])
@admin_required
def edit_tour(tour_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        country = request.form.get('country')
        agencyid = request.form.get('agencyid')
        duration = request.form.get('duration')
        price = request.form.get('price')
        description = request.form.get('description')

        try:
            cursor.execute("""
                UPDATE Tours 
                SET country=?, agencyid=?, duration=?, price=?, description=?
                WHERE id=?
            """, (country, agencyid, duration, price, description, tour_id))
            conn.commit()
            flash('Данные тура успешно обновлены', 'success')
            return redirect(url_for('admin_bp.manage_tours'))
        except sqlite3.Error as e:
            flash(f'Ошибка при обновлении тура: {str(e)}', 'danger')
        finally:
            conn.close()

    # GET запрос - показываем форму
        cursor.execute("SELECT id, country, agencyid, duration, price, description FROM Tours WHERE id=?", (tour_id,))
    tour_data = cursor.fetchone()

    # Преобразуем в словарь
    tour = {
        'id': tour_data[0],
        'country': tour_data[1],
        'agencyid': tour_data[2],
        'duration': tour_data[3],
        'price': tour_data[4],
        'description': tour_data[5]
    }

    # Получаем список агентств для выпадающего списка
    cursor.execute("SELECT id, name FROM Agency")
    agencies = [{'id': row[0], 'name': row[1]} for row in cursor.fetchall()]
    conn.close()

    if not tour:
        flash('Тур не найден', 'danger')
        return redirect(url_for('admin_bp.manage_tours'))

    return render_template("edit_tour.html",
                           tour=tour,
                           agencies=agencies,
                           user_name=session['user_name'],
                           is_authenticated=True)

# Управление агентствами
@admin_bp.route('/admin/agencies')
@admin_required
def manage_agencies():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, city, address FROM Agency")
    agencies = cursor.fetchall()
    conn.close()
    return render_template("admin_agencies.html",
                           agencies=agencies,
                           user_name=session['user_name'],
                           is_authenticated=True)


@admin_bp.route('/admin/agencies/add', methods=['GET', 'POST'])
@admin_required
def add_agency():
    if request.method == 'POST':
        name = request.form.get('name')
        city = request.form.get('city')
        address = request.form.get('address')

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT INTO Agency (name, city, address) VALUES (?, ?, ?)",
                (name, city, address)
            )
            conn.commit()
            flash('Агентство успешно добавлено', 'success')
            return redirect(url_for('admin_bp.manage_agencies'))
        except sqlite3.Error as e:
            flash(f'Ошибка при добавлении агентства: {str(e)}', 'danger')
        finally:
            conn.close()

    return render_template("add_agency.html",
                           user_name=session['user_name'],
                           is_authenticated=True)


@admin_bp.route('/admin/agencies/delete/<int:agency_id>', methods=['POST'])
@admin_required
def delete_agency(agency_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM Agency WHERE id = ?", (agency_id,))
        conn.commit()
        flash('Агентство успешно удалено', 'success')
    except sqlite3.Error as e:
        flash(f'Ошибка при удалении агентства: {str(e)}', 'danger')
    finally:
        conn.close()
    return redirect(url_for('admin_bp.manage_agencies'))

# Редактирование агентства
@admin_bp.route('/admin/agencies/edit/<int:agency_id>', methods=['GET', 'POST'])
@admin_required
def edit_agency(agency_id):
    conn = get_db_connection()
    cursor = conn.cursor()

    if request.method == 'POST':
        name = request.form.get('name')
        city = request.form.get('city')
        address = request.form.get('address')

        try:
            cursor.execute("""
                UPDATE Agency 
                SET name=?, city=?, address=?
                WHERE id=?
            """, (name, city, address, agency_id))
            conn.commit()
            flash('Данные агентства успешно обновлены', 'success')
            return redirect(url_for('admin_bp.manage_agencies'))
        except sqlite3.Error as e:
            flash(f'Ошибка при обновлении агентства: {str(e)}', 'danger')
        finally:
            conn.close()

    # GET запрос - показываем форму
    cursor.execute("SELECT id, name, city, address FROM Agency WHERE id=?", (agency_id,))
    agency_data = cursor.fetchone()
    conn.close()

    if not agency_data:
        flash('Агентство не найдено', 'danger')
        return redirect(url_for('admin_bp.manage_agencies'))

    # Преобразуем в словарь
    agency = {
        'id': agency_data[0],
        'name': agency_data[1],
        'city': agency_data[2],
        'address': agency_data[3]
    }

    return render_template("edit_agency.html",
                           agency=agency,
                           user_name=session['user_name'],
                           is_authenticated=True)

# Скачиваем Excel
@admin_bp.route('/admin/agencies/export')
@admin_required
def export_agencies():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Agency")
        agencies = cursor.fetchall()
        cursor.execute("PRAGMA table_info(Agency)")
        columns = [column[1] for column in cursor.fetchall()]
        conn.close()

        # Создаем Excel файл
        wb = Workbook()
        ws = wb.active
        ws.title = "Агентства"

        # Заголовки
        ws.append(columns)

        # Данные
        for agency in agencies:
            ws.append(agency)

        # Сохраняем в буфер
        buffer = BytesIO()
        wb.save(buffer)
        buffer.seek(0)

        # Создаем ответ
        response = make_response(buffer.getvalue())
        response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        response.headers['Content-Disposition'] = 'attachment; filename=agencies_export.xlsx'
        return response

    except Exception as e:
        flash(f'Ошибка при экспорте: {str(e)}', 'danger')
        return redirect(url_for('admin_bp.manage_agencies'))
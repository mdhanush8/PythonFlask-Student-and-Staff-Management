from flask import Flask, request, session, redirect, render_template, jsonify, url_for
import csv
import os
from functools import wraps

app = Flask(__name__)
app.secret_key = '321'  # Change this to a secure key
PASSWORD_FILE = 'passwords.csv'
STUDENT_CSV_FILE = 'students.csv'
STAFF_CSV_FILE = 'staff.csv'

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'logged_in' not in session or not session['logged_in']:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def init_passwords():
    if not os.path.exists(PASSWORD_FILE):
        with open(PASSWORD_FILE, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(['password'])

def check_password(password):
    with open(PASSWORD_FILE, 'r') as file:
        reader = csv.reader(file)
        passwords = [row[0] for row in reader]
    return password in passwords

def add_password(password):
    with open(PASSWORD_FILE, 'a', newline='') as file:
        writer = csv.writer(file)
        writer.writerow([password])

def init_csv(file_name, headers):
    if not os.path.exists(file_name):
        with open(file_name, 'w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(headers + ['password'])

def is_duplicate(file_name, key_field, value, password):
    with open(file_name, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row[key_field] == value and row['password'] == password:
                return True
    return False

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'login':
            password = request.form['password']
            if check_password(password):
                session['logged_in'] = True
                session['current_password'] = password
                return jsonify({'success': True, 'redirect': url_for('root')})
            else:
                return jsonify({'success': False, 'error': 'Invalid password.'})
        
        elif action == 'set_password':
            new_password = request.form['new_password']
            if not check_password(new_password):
                add_password(new_password)
                return jsonify({'success': True})
            else:
                return jsonify({'success': False, 'error': 'Password already exists.'})
    
    return render_template('login.html')

@app.route('/')
def root():
    if 'logged_in' not in session or not session['logged_in']:
        return redirect(url_for('login'))
    return render_template('index.html')

def filter_data(file_name, password):
    filtered_data = []
    with open(file_name, 'r') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['password'] == password:
                filtered_data.append(row)
    return filtered_data

@app.route('/students', methods=['GET', 'POST'])
@login_required
def manage_students():
    if request.method == 'POST':
        data = request.json
        data['password'] = session['current_password']

        if is_duplicate(STUDENT_CSV_FILE, 'roll_number', data['roll_number'], data['password']):
            return jsonify({'error': 'Student with this roll number already exists'}), 400

        try:
            with open(STUDENT_CSV_FILE, 'a', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=['name', 'roll_number', 'department', 'class_', 'date_of_birth', 'gender', 'address', 'phone_number', 'mail_id', 'marksheet', 'certificate', 'password'])
                writer.writerow(data)
            return jsonify({'message': 'Student added successfully'}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    elif request.method == 'GET':
        password = session['current_password']
        students = filter_data(STUDENT_CSV_FILE, password)
        return jsonify(students), 200

@app.route('/students/<roll_number>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def student_details(roll_number):
    password = session['current_password']
    
    if request.method == 'GET':
        students = filter_data(STUDENT_CSV_FILE, password)
        student = next((s for s in students if s['roll_number'] == roll_number), None)
        if student:
            return jsonify(student), 200
        return jsonify({'error': 'Student not found'}), 404

    elif request.method in ['PUT', 'DELETE']:
        rows = []
        student_found = False
        with open(STUDENT_CSV_FILE, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['roll_number'] == roll_number and row['password'] == password:
                    student_found = True
                    if request.method == 'PUT':
                        updated_data = request.json
                        if 'roll_number' in updated_data and updated_data['roll_number'] != roll_number:
                            if is_duplicate(STUDENT_CSV_FILE, 'roll_number', updated_data['roll_number'], password):
                                return jsonify({'error': 'Student with this roll number already exists'}), 400
                        row.update(updated_data)
                rows.append(row)

        if not student_found:
            return jsonify({'error': 'Student not found'}), 404

        with open(STUDENT_CSV_FILE, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=reader.fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        return jsonify({'message': 'Student updated successfully' if request.method == 'PUT' else 'Student deleted successfully'}), 200

@app.route('/staff', methods=['GET', 'POST'])
@login_required
def manage_staff():
    if request.method == 'POST':
        data = request.json
        data['password'] = session['current_password']

        if is_duplicate(STAFF_CSV_FILE, 'id', data['id'], data['password']):
            return jsonify({'error': 'Staff member with this ID already exists'}), 400

        try:
            with open(STAFF_CSV_FILE, 'a', newline='') as file:
                writer = csv.DictWriter(file, fieldnames=['name', 'id', 'age', 'gender', 'date_of_joining', 'date_of_birth', 'address', 'phone_number', 'designation', 'department', 'password'])
                writer.writerow(data)
            return jsonify({'message': 'Staff added successfully'}), 201
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    elif request.method == 'GET':
        password = session['current_password']
        staff = filter_data(STAFF_CSV_FILE, password)
        return jsonify(staff), 200

@app.route('/staff/<staff_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def staff_details(staff_id):
    password = session['current_password']
    
    if request.method == 'GET':
        staff_list = filter_data(STAFF_CSV_FILE, password)
        staff_member = next((s for s in staff_list if s['id'] == staff_id), None)
        if staff_member:
            return jsonify(staff_member), 200
        return jsonify({'error': 'Staff member not found'}), 404

    elif request.method in ['PUT', 'DELETE']:
        rows = []
        staff_found = False
        with open(STAFF_CSV_FILE, 'r') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['id'] == staff_id and row['password'] == password:
                    staff_found = True
                    if request.method == 'PUT':
                        updated_data = request.json
                        if 'id' in updated_data and updated_data['id'] != staff_id:
                            if is_duplicate(STAFF_CSV_FILE, 'id', updated_data['id'], password):
                                return jsonify({'error': 'Staff member with this ID already exists'}), 400
                        row.update(updated_data)
                rows.append(row)

        if not staff_found:
            return jsonify({'error': 'Staff member not found'}), 404

        with open(STAFF_CSV_FILE, 'w', newline='') as file:
            writer = csv.DictWriter(file, fieldnames=reader.fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        return jsonify({'message': 'Staff member updated successfully' if request.method == 'PUT' else 'Staff member deleted successfully'}), 200

if __name__ == '__main__':
    init_passwords()
    init_csv(STUDENT_CSV_FILE, ['name', 'roll_number', 'department', 'class_', 'date_of_birth', 'gender', 'address', 'phone_number', 'mail_id', 'marksheet', 'certificate'])
    init_csv(STAFF_CSV_FILE, ['name', 'id', 'age', 'gender', 'date_of_joining', 'date_of_birth', 'address', 'phone_number', 'designation', 'department'])
    app.run ( host="0.0.0.0" , port=8005, threaded=True ,debug=True)


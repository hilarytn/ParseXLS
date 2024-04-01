from flask import Flask, render_template, request, redirect, send_file, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
import os
import pandas as pd
from datetime import datetime
import re
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql://vbnesasy_vbnesasy:2xl#-%{oVRl,@72.249.30.172/vbnesasy_sanitation_technologies'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.secret_key = 'd491df968bb27646946de16c3931b9ca'

application = app

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

USER_FILES_DIR = 'user_files'  # Directory to store user-specific files
UPLOAD_FOLDER = 'uploads'
MASTER_FILE = 'master_file.xlsx'
INVENTORY_FILE = 'inventory.csv'
LINE_FILE_PREFIX = 'line_'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# User model
class User(UserMixin, db.Model):
    id = db.Column(db.String(8), primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)

    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.id = str(uuid.uuid4())[:8]

# Create database tables
with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    # Query the User object from the database based on user_id
    return User.query.get(user_id)

# Function to sanitize sheet name
def sanitize_sheet_name(sheet_name):
    return re.sub(r'[^\w\s]', '_', sheet_name)

# Function to parse excel file
def parse_excel(file_path):
    df = pd.read_excel(file_path)
    return df

# Function to update master file and record inventory
def update_master(data, filename, line_number, username):
    user_dir = os.path.join(USER_FILES_DIR, username)
    master_file_path, inventory_file_path = get_user_file_paths(username)

    file_uuid = str(uuid.uuid4())

    if os.path.exists(master_file_path):
        master_df = pd.read_excel(master_file_path)
        master_df = pd.concat([master_df, data], ignore_index=True)
        master_df['uuid'] = file_uuid  # Associate data with UUID
    else:
        master_df = data.copy()
        master_df['uuid'] = file_uuid

    # Calculate downtime
    master_df['downtime'] = master_df['nd'] - master_df['st']

    master_df.to_excel(master_file_path, index=False)

    # Record inventory
    upload_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(inventory_file_path, 'a') as f:
        f.write(f'{filename},{upload_date},{file_uuid}\n')

    # Update line-specific file
    line_filename = f"{LINE_FILE_PREFIX}{line_number}.xlsx"
    line_file_path = os.path.join(user_dir, line_filename)
    if os.path.exists(line_file_path):
        line_df = pd.read_excel(line_file_path)
        line_df = pd.concat([line_df, data], ignore_index=True)
        line_df['uuid'] = file_uuid
    else:
        line_df = data.copy()
        line_df['uuid'] = file_uuid

    # Calculate downtime
    line_df['downtime'] = line_df['nd'] - line_df['st']

    line_df.to_excel(line_file_path, index=False)

# Function to cleanup uploaded files
def cleanup_uploaded_files():
    # Delete all files in the UPLOAD_FOLDER directory
    for filename in os.listdir(UPLOAD_FOLDER):
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        try:
            if os.path.isfile(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"Error deleting file {file_path}: {e}")

# Function to get available line numbers from line files present
def get_available_lines(username):
    user_dir = os.path.join(USER_FILES_DIR, username)
    available_lines = []
    for filename in os.listdir(user_dir):
        if filename.startswith('line_') and filename.endswith('.xlsx'):
            line_number = filename.split('_')[1].split('.')[0]
            available_lines.append(int(line_number))
    return sorted(available_lines)

# Function to get user-specific file paths
def get_user_file_paths(username):
    user_dir = os.path.join(USER_FILES_DIR, username)
    if not os.path.exists(user_dir):
        os.makedirs(user_dir)
    master_file_path = os.path.join(user_dir, MASTER_FILE)
    inventory_file_path = os.path.join(user_dir, INVENTORY_FILE)
    return master_file_path, inventory_file_path

@app.route('/home')
@login_required
def index():
    master_file_link = None
    master_file_path, _ = get_user_file_paths(current_user.username)
    if os.path.exists(master_file_path):
        master_file_link = url_for('download_master')
    inventory = []
    inventory_file_path = os.path.join(USER_FILES_DIR, current_user.username, INVENTORY_FILE)
    if os.path.exists(inventory_file_path):
        with open(inventory_file_path, 'r') as f:
            for line in f.readlines()[1:]:
                filename, upload_date, my_uuid = line.strip().split(',')
                inventory.append({'filename': filename, 'upload_date': upload_date, 'my_uuid': my_uuid})
    lines = get_available_lines(current_user.username)
    return render_template('index.html', master_file_link=master_file_link, inventory=inventory, current_user=current_user, lines=lines)

@app.route('/upload', methods=['POST'])
@login_required
def upload():
    try:
        if 'files[]' not in request.files:
            return redirect(request.url)
        files = request.files.getlist('files[]')
        if not files:
            return redirect(request.url)

        uploaded_files = []
        for file in files:
            if file.filename == '':
                return redirect(request.url)
            if file:
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
                file.save(file_path)
                df = parse_excel(file_path)
                line_number = extract_line_number(df)
                update_master(df, file.filename, line_number, current_user.username)
                uploaded_files.append(file.filename)

        if uploaded_files:
            message = f"Uploaded files: {', '.join(uploaded_files)}"
            cleanup_uploaded_files()
            master_file_path, _ = get_user_file_paths(current_user.username)
            if os.path.exists(master_file_path):
                master_file = MASTER_FILE
            lines = get_available_lines(current_user.username)
            return render_template('upload_success.html', message=message, master_file_link=master_file, lines=lines)
        else:
            return render_template('upload_failure.html')
    except Exception as e:
        error_message = f"An error occurred during upload: {e}"
        return render_template('upload_failure.html')

def extract_line_number(df):
    line_column = df.columns[0]
    line_str = df[line_column][0]
    line_number = int(re.search(r'Line:(\d+)', line_str).group(1))
    return line_number

def delete_file_data(uuid):
    master_file_path, inventory_file_path = get_user_file_paths(current_user.username)

    # Delete data from master file
    if os.path.exists(master_file_path):
        master_df = pd.read_excel(master_file_path)
        master_df = master_df[master_df['uuid'] != uuid]
        master_df.to_excel(master_file_path, index=False)
    
    # Delete data from line-specific files
    user_dir = os.path.join(USER_FILES_DIR, current_user.username)
    for filename in os.listdir(user_dir):
        if filename.startswith('line_') and filename.endswith('.xlsx'):
            line_file_path = os.path.join(user_dir, filename)
            line_df = pd.read_excel(line_file_path)
            line_df = line_df[line_df['uuid'] != uuid]
            if not line_df.empty:
                line_df.to_excel(line_file_path, index=False)
            else:
                os.remove(line_file_path)

    # Delete record from inventory
    if os.path.exists(inventory_file_path):
        with open(inventory_file_path, 'r') as f:
            lines = f.readlines()
        with open(inventory_file_path, 'w') as f:
            f.write(lines[0])  # Write header
            for line in lines[1:]:
                if uuid not in line:
                    f.write(line)

@app.route('/download_master')
@login_required
def download_master():
    master_file_path, _ = get_user_file_paths(current_user.username)
    if os.path.exists(master_file_path):
        return send_file(master_file_path, as_attachment=True)
    else:
        return "Master file not found."

@app.route('/master')
@login_required
def master():
    master_data = []
    master_file_path, _ = get_user_file_paths(current_user.username)
    if os.path.exists(master_file_path):
        master_df = pd.read_excel(master_file_path)
        master_data = master_df.to_dict('records')
    return render_template('master.html', master_data=master_data)

@app.route('/line/<int:line_number>')
@login_required
def line(line_number):
    line_file = f"line_{line_number}.xlsx"
    line_data = []
    user_dir = os.path.join(USER_FILES_DIR, current_user.username)
    line_file_path = os.path.join(user_dir, line_file)
    if os.path.exists(line_file_path):
        line_df = pd.read_excel(line_file_path)
        line_data = line_df.to_dict('records')
    else:
        return "Data for this line doesn't exist"
    return render_template('line.html', line_number=line_number, line_data=line_data)

# Route to handle user registration
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        try:
            existing_user = User.query.filter_by(username=username).first()

            if existing_user:
                return render_template('register.html', error="Username already exists. Please choose a different one.")

            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()

            return redirect(url_for('login'))
        except Exception as e:
            db.session.rollback()
            error_message = str(e)
            return render_template('register.html', error=f"An error occurred")

    return render_template('register.html')

@app.route('/', methods=['GET', 'POST'])
def login():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            login_user(user)
            return redirect(url_for('index'))
        else:
            error = 'Invalid username or password. Please try again.'

    return render_template('login.html', error=error)

@app.route('/delete/<uuid>', methods=['POST'])
@login_required
def delete_file(uuid):
    delete_file_data(uuid)
    return redirect(url_for('index'))

@app.route('/line_data/<int:line_number>')
@login_required
def line_data(line_number):
    # Retrieve data for the specified line
    line_file_path = os.path.join(USER_FILES_DIR, current_user.username, f"line_{line_number}.xlsx")
    if not os.path.exists(line_file_path):
        return jsonify({'error': f'Data for line {line_number} does not exist'})

    # Load data from the line file
    line_df = pd.read_excel(line_file_path)

    # Process data to calculate summary statistics
    summary_data = {}
    if not line_df.empty:
        # Calculate count, sum of tgaps, and sum of downtimes for each unique product
        summary_data = line_df.groupby('DESCR').agg({
            'tgap': 'sum',
            'downtime': 'sum'
        }).reset_index().to_dict(orient='records')

        # Compute count for each unique product
        product_counts = line_df['DESCR'].value_counts().to_dict()
        for product in summary_data:
            product['count'] = product_counts.get(product['DESCR'], 0)

        print(summary_data)

    return jsonify(summary_data)


@app.route('/login', methods=['GET'])
def login_form():
    return render_template('login.html')

@app.route('/index2', methods=['GET'])
def index2():
    return render_template('index2.html')

@app.route('/line2', methods=['GET'])
def line2():
    return render_template('line2.html')

@app.route('/login2', methods=['GET'])
def login2():
    return render_template('login2.html')

@app.route('/master2', methods=['GET'])
def master2():
    return render_template('master2.html')

@app.route('/process2', methods=['GET'])
def process2():
    return render_template('process_failure2.html')

@app.route('/process3', methods=['GET'])
def process3():
    return render_template('process_success2.html')

@app.route('/upload-failure2', methods=['GET'])
def upf():
    return render_template('upload_failure2.html')

@app.route('/upload-success2', methods=['GET'])
def ups():
    return render_template('upload_success2.html')

@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

if __name__ == "__main__":
    app.run(debug=True)
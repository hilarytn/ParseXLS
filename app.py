from flask import Flask, render_template, request, redirect, send_file, url_for, jsonify, session
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

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'


# Generate a UUID
uuid_str = str(uuid.uuid4())

# Truncate the UUID to the desired length
truncated_uuid = uuid_str.replace('-', '')[:8] 

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

application = app

UPLOAD_FOLDER = 'uploads'
MASTER_FILE = 'master_file.xlsx'
INVENTORY_FILE = 'inventory.csv'
LINE_FILE_PREFIX = 'line_'  # Constant for line file prefix
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Initialize the inventory file if it doesn't exist
if not os.path.exists(INVENTORY_FILE):
    with open(INVENTORY_FILE, 'w') as f:
        f.write('filename,upload_date,process_date\n')

# Function to sanitize sheet name
def sanitize_sheet_name(sheet_name):
    return re.sub(r'[^\w\s]', '_', sheet_name)

# Function to parse excel file
def parse_excel(file_path):
    df = pd.read_excel(file_path)
    return df

# Function to update master file and record inventory
def update_master(data, filename, line_number):
    if os.path.exists(MASTER_FILE):
        master_df = pd.read_excel(MASTER_FILE)
        master_df = pd.concat([master_df, data], ignore_index=True)
        master_df.to_excel(MASTER_FILE, index=False)
    else:
        data.to_excel(MASTER_FILE, index=False)
    
    # Record inventory
    upload_date = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    with open(INVENTORY_FILE, 'a') as f:
        f.write(f'{filename},{upload_date},\n')
    
    # Update line-specific file
    line_filename = f"{LINE_FILE_PREFIX}{line_number}.xlsx"  # Construct line-specific filename
    if os.path.exists(line_filename):
        line_df = pd.read_excel(line_filename)
        line_df = pd.concat([line_df, data], ignore_index=True)
        line_df.to_excel(line_filename, index=False)
    else:
        data.to_excel(line_filename, index=False)

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
def get_available_lines():
    available_lines = []
    for filename in os.listdir('.'):
        if filename.startswith('line_') and filename.endswith('.xlsx'):
            line_number = filename.split('_')[1].split('.')[0]
            available_lines.append(int(line_number))
    return sorted(available_lines)


@app.route('/home')
@login_required
def index():
    master_file_link = None
    if os.path.exists(MASTER_FILE):
        master_file_link = url_for('download_master')
    inventory = []
    if os.path.exists(INVENTORY_FILE):
        with open(INVENTORY_FILE, 'r') as f:
            for line in f.readlines()[1:]:
                filename, upload_date, process_date = line.strip().split(',')
                inventory.append({'filename': filename, 'upload_date': upload_date, 'process_date': process_date})
    lines = get_available_lines()
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
                line_number = extract_line_number(df)  # Extract line number from the DataFrame
                update_master(df, file.filename, line_number)
                uploaded_files.append(file.filename)
        
        if uploaded_files:
            message = f"Uploaded files: {', '.join(uploaded_files)}"
            cleanup_uploaded_files()  # Cleanup uploaded files after processing
            if os.path.exists(MASTER_FILE):
                master_file = MASTER_FILE
            lines = get_available_lines()
            return render_template('upload_success.html', message=message, master_file_link=master_file, lines=lines)
        else:
            return render_template('upload_failure.html')
    except Exception as e:
        error_message = f"An error occurred during upload: {e}"
        return render_template('upload_failure.html')

def extract_line_number(df):
    # Assume 'Line:X' is in the first row of the DataFrame
    line_column = df.columns[0]  # Assuming the line number is in the first column
    line_str = df[line_column][0]  # Extract line string from the first row
    line_number = int(re.search(r'Line:(\d+)', line_str).group(1))  # Extract line number using regex
    return line_number

@app.route('/download_master')
@login_required
def download_master():
    if os.path.exists(MASTER_FILE):
        return send_file(MASTER_FILE, as_attachment=True)
    else:
        return "Master file not found."
    
@app.route('/master')
@login_required
def master():
    master_data = []
    if os.path.exists(MASTER_FILE):
        master_df = pd.read_excel(MASTER_FILE)
        master_data = master_df.to_dict('records')
    if os.path.exists(MASTER_FILE):
        master_file = MASTER_FILE
    return render_template('master.html', master_data=master_data, master_file_link=master_file)


@app.route('/line/<int:line_number>')
@login_required
def line(line_number):
    line_file = f"line_{line_number}.xlsx"
    line_data = []
    if os.path.exists(line_file):
        line_df = pd.read_excel(line_file)
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
            # Check if the username already exists in the database
            existing_user = User.query.filter_by(username=username).first()

            if existing_user:
                return render_template('register.html', error="Username already exists. Please choose a different one.")

            # Create a new user instance with the provided username and password
            new_user = User(username=username, password=password)
            db.session.add(new_user)
            db.session.commit()

            return redirect(url_for('login'))
        except Exception as e:
            # Roll back any changes if an error occurs
            db.session.rollback()
            # Log the error or handle it in any other appropriate way
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

@app.route('/login', methods=['GET'])
def login_form():
    return render_template('login.html')

# Add the login_required decorator to the logout route
@app.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


if __name__ == "__main__":
    app.run(debug=True)

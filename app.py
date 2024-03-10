from flask import Flask, render_template, request, redirect, send_file, url_for
import os
import pandas as pd
from datetime import datetime
import re

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
MASTER_FILE = 'master_file.xlsx'
INVENTORY_FILE = 'inventory.csv'
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
def update_master(data, filename):
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

@app.route('/')
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
    return render_template('index.html', master_file_link=master_file_link, inventory=inventory)

@app.route('/upload', methods=['POST'])
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
                update_master(df, file.filename)
                uploaded_files.append(file.filename)
        
        if uploaded_files:
            message = f"Uploaded files: {', '.join(uploaded_files)}"
            cleanup_uploaded_files()  # Cleanup uploaded files after processing
            if os.path.exists(MASTER_FILE):
                master_file = MASTER_FILE
            return render_template('upload_success.html', message=message, master_file_link=master_file)
        else:
            return render_template('upload_failure.html')
    except Exception as e:
        error_message = f"An error occurred during upload: {e}"
        return render_template('upload_failure.html')

@app.route('/download_master')
def download_master():
    if os.path.exists(MASTER_FILE):
        return send_file(MASTER_FILE, as_attachment=True)
    else:
        return "Master file not found."
    
@app.route('/master')
def master():
    master_data = []
    if os.path.exists(MASTER_FILE):
        master_df = pd.read_excel(MASTER_FILE)
        master_data = master_df.to_dict('records')
    if os.path.exists(MASTER_FILE):
        master_file = MASTER_FILE
    return render_template('master.html', master_data=master_data, master_file_link=master_file)

if __name__ == "__main__":
    app.run(debug=True)
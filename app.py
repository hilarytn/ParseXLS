from flask import Flask, render_template, request, redirect
import os
import pandas as pd
from datetime import datetime
import re

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
MASTER_FILE = 'master_file.xlsx'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def sanitize_sheet_name(sheet_name):
    return re.sub(r'[^\w\s]', '_', sheet_name)

def parse_excel(file_path):
    df = pd.read_excel(file_path)
    return df

def update_master(data):
    if os.path.exists(MASTER_FILE):
        master_df = pd.read_excel(MASTER_FILE)
        master_df = pd.concat([master_df, data], ignore_index=True)
        master_df.to_excel(MASTER_FILE, index=False)
    else:
        data.to_excel(MASTER_FILE, index=False)

@app.route('/')
def index():
    return render_template('index.html')

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
                update_master(df)
                uploaded_files.append(file.filename)
        
        if uploaded_files:
            message = f"Uploaded files: {', '.join(uploaded_files)}"
            return render_template('upload_success.html', message=message)
        else:
            return render_template('upload_failure.html')
    except Exception as e:
        error_message = f"An error occurred during upload: {e}"
        return render_template('upload_failure.html')

@app.route('/process')
def process():
    return render_template('process.html')

if __name__ == "__main__":
    app.run(debug=True)

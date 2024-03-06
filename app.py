from flask import Flask, render_template, request, redirect
import os
import pandas as pd
from datetime import datetime

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def parse_excel_sheets(input_files):
    line_data = {}
    for file_name in input_files:
        xl = pd.ExcelFile(file_name)
        for sheet_name in xl.sheet_names:
            df = xl.parse(sheet_name)
            line_number = sheet_name.split()[-1]
            if line_number not in line_data:
                line_data[line_number] = df
            else:
                line_data[line_number] = pd.concat([line_data[line_number], df], ignore_index=True)
    return line_data


def save_line_data_to_excel(line_data, output_dir):
    for line_number, df in line_data.items():
        if not df.empty:
            output_file = os.path.join(output_dir, f"line_{line_number}.xlsx")
            df.to_excel(output_file, index=False)


def update_master_file(line_data, output_dir):
    master_file = os.path.join(output_dir, 'master_file.xlsx')
    if os.path.exists(master_file):
        with pd.ExcelWriter(master_file, mode='a', engine='openpyxl') as writer:
            for line_name, data_frames in line_data.items():
                pd.concat(data_frames).to_excel(writer, sheet_name=line_name, index=False)
    else:
        with pd.ExcelWriter(master_file, engine='openpyxl') as writer:
            for line_name, data_frames in line_data.items():
                pd.concat(data_frames).to_excel(writer, sheet_name=line_name, index=False)

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
        
        # Generate a unique collection name for this upload
        collection_name = datetime.now().strftime('%Y%m%d%H%M%S%f')
        collection_dir = os.path.join(app.config['UPLOAD_FOLDER'], collection_name)
        os.makedirs(collection_dir, exist_ok=True)

        uploaded_files = []
        for file in files:
            if file.filename == '':
                return redirect(request.url)
            if file:
                file.save(os.path.join(collection_dir, file.filename))
                uploaded_files.append(file.filename)
        
        if uploaded_files:
            # Provide feedback to the user that files were successfully uploaded
            message = f"Uploaded files: {', '.join(uploaded_files)}"
            return render_template('upload_success.html', message=message, collection_name=collection_name)
        else:
            # Provide feedback to the user that no files were uploaded
            return render_template('upload_failure.html')
    except Exception as e:
        error_message = f"An error occurred during upload: {e}"
        return render_template('upload_failure.html', error_message=error_message)


@app.route('/process/<collection_name>', methods=['POST'])
def process(collection_name):
    try:
        collection_dir = os.path.join(app.config['UPLOAD_FOLDER'], collection_name)
        if os.path.exists(collection_dir) and os.path.isdir(collection_dir):
            files = [os.path.join(collection_dir, filename) for filename in os.listdir(collection_dir)]
            line_data = parse_excel_sheets(files)
            
            # Create output directory inside the collection directory
            output_dir = os.path.join(collection_dir, 'output')
            
            save_line_data_to_excel(line_data, output_dir)
            update_master_file(line_data, output_dir)
            return render_template('process_success.html')  # Provide feedback for successful processing
        else:
            error_message = f"Collection '{collection_name}' not found."
            return render_template('process_failure.html', error_message=error_message)  # Provide feedback for failure
    except Exception as e:
        error_message = f"An error occurred during processing: {e}"
        return render_template('process_failure.html', error_message=error_message)  # Provide feedback for failure
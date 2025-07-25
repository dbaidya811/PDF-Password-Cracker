import os
from flask import Flask, request, render_template, send_file, redirect, url_for, flash
from PyPDF2 import PdfReader, PdfWriter
from werkzeug.utils import secure_filename
import threading
import time
from datetime import datetime, timedelta

tmp_dir = 'tmp'
os.makedirs(tmp_dir, exist_ok=True)

app = Flask(__name__)
app.secret_key = 'supersecretkey'
app.config['UPLOAD_FOLDER'] = tmp_dir

# Brute-force function
def brute_force_pdf_password(pdf_path):
    # প্রথমে 0000-99999999 পর্যন্ত সংখ্যা ট্রাই করব
    for i in range(0, 100000000):
        password = str(i).zfill(4)
        try:
            with open(pdf_path, 'rb') as f:
                reader = PdfReader(f)
                if reader.is_encrypted:
                    if reader.decrypt(password):
                        # Unlock and save new PDF
                        writer = PdfWriter()
                        for page in reader.pages:
                            writer.add_page(page)
                        unlocked_path = os.path.join(tmp_dir, f'unlocked_{os.path.basename(pdf_path)}')
                        with open(unlocked_path, 'wb') as out_f:
                            writer.write(out_f)
                        return password, unlocked_path
        except Exception:
            continue
    # যদি না পাওয়া যায়, তাহলে কমন পাসওয়ার্ড dataset থেকে ট্রাই করব
    try:
        with open('common_passwords.txt', 'r', encoding='utf-8') as pwfile:
            for line in pwfile:
                password = line.strip()
                if not password:
                    continue
                try:
                    with open(pdf_path, 'rb') as f:
                        reader = PdfReader(f)
                        if reader.is_encrypted:
                            if reader.decrypt(password):
                                writer = PdfWriter()
                                for page in reader.pages:
                                    writer.add_page(page)
                                unlocked_path = os.path.join(tmp_dir, f'unlocked_{os.path.basename(pdf_path)}')
                                with open(unlocked_path, 'wb') as out_f:
                                    writer.write(out_f)
                                return password, unlocked_path
                except Exception:
                    continue
    except Exception:
        pass
    return None, None

def cleanup_tmp_folder():
    while True:
        now = datetime.now()
        for filename in os.listdir(tmp_dir):
            file_path = os.path.join(tmp_dir, filename)
            if os.path.isfile(file_path):
                file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                if now - file_mtime > timedelta(hours=24):
                    try:
                        os.remove(file_path)
                    except Exception:
                        pass
        time.sleep(3600)  # Check every hour

@app.route('/', methods=['GET', 'POST'])
def upload_file():
    if request.method == 'POST':
        if 'pdf' not in request.files:
            flash('No file part')
            return redirect(request.url)
        file = request.files['pdf']
        if file.filename == '':
            flash('No selected file')
            return redirect(request.url)
        if file:
            filename = secure_filename(file.filename)
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            password, unlocked_path = brute_force_pdf_password(file_path)
            if password:
                return render_template('index.html', password=password, unlocked_pdf=os.path.basename(unlocked_path))
            else:
                flash('Password not found (tried all numbers from 0000 to 99999999)')
                return redirect(request.url)
    return render_template('index.html')

@app.route('/download/<filename>')
def download_file(filename):
    return send_file(os.path.join(app.config['UPLOAD_FOLDER'], filename), as_attachment=True)

if __name__ == '__main__':
    # Start background cleanup thread
    t = threading.Thread(target=cleanup_tmp_folder, daemon=True)
    t.start()
    app.run(debug=True) 
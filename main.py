from flask import Flask, render_template, request, redirect, send_from_directory, jsonify, flash
import os
import shutil
import fitz  # PyMuPDF
import re
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = "some_secret_key"

# Email config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME')
mail = Mail(app)

# Folder setup
UPLOAD_FOLDER = 'resumes'
SELECTED_FOLDER = 'selected_resumes'
STATIC_FOLDER = 'static'
ALLOWED_EXTENSIONS = {'pdf'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SELECTED_FOLDER'] = SELECTED_FOLDER

# Ensure folders exist
for folder in [UPLOAD_FOLDER, SELECTED_FOLDER, STATIC_FOLDER]:
    if not os.path.exists(folder):
        os.makedirs(folder)

uploaded_files = []
matched_candidates = []

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def extract_text_from_pdf(pdf_path):
    text = ""
    doc = fitz.open(pdf_path)
    for page in doc:
        text += page.get_text()
    return text.lower()

def extract_email(text):
    match = re.search(r"[\w\.-]+@[\w\.-]+", text)
    return match.group(0) if match else ""

def extract_name(text):
    match = re.search(r"(?<=name[:\s])[a-zA-Z\s]{2,50}", text, re.IGNORECASE)
    return match.group(0).strip().title() if match else "Unknown"

@app.route('/')
def index():
    return render_template('index.html', uploaded_files=uploaded_files, results=None, total_selected=0, upload_message=None, entered_skills='')

@app.route('/upload', methods=['POST'])
def upload():
    global uploaded_files
    uploaded_files.clear()
    files = request.files.getlist('resume')
    success_count = 0
    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(filepath)
            uploaded_files.append(filename)
            success_count += 1
    msg = f"{success_count} file(s) uploaded successfully." if success_count else "No valid files uploaded."
    return render_template('index.html', uploaded_files=uploaded_files, upload_message=msg, upload_success=True, results=None, total_selected=0, entered_skills='')

@app.route('/clear_resumes', methods=['POST'])
def clear_uploads():
    global uploaded_files
    for f in uploaded_files:
        try:
            os.remove(os.path.join(UPLOAD_FOLDER, f))
        except:
            continue
    uploaded_files.clear()
    shutil.rmtree(UPLOAD_FOLDER)
    os.makedirs(UPLOAD_FOLDER)
    return redirect('/')

@app.route('/process', methods=['POST'])
def process():
    global matched_candidates
    matched_candidates.clear()
    skills = request.form['skills']
    required_skills = [s.strip().lower() for s in skills.split(',') if s.strip()]

    if not required_skills:
        return render_template('index.html', uploaded_files=uploaded_files, results=[], total_selected=0, upload_message="Enter valid skills.", upload_success=False, entered_skills=skills)

    for filename in uploaded_files:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        text = extract_text_from_pdf(filepath)
        match_count = sum(1 for skill in required_skills if skill in text)
        match_ratio = match_count / len(required_skills)
        percentage = int(match_ratio * 100)

        if match_ratio >= 0.75:
            percentage = 80 + int((match_ratio - 0.75) * 20)
            percentage = min(percentage, 100)

        if percentage >= 80:
            name = extract_name(text)
            email = extract_email(text)
            matched_candidates.append({'filename': filename, 'name': name, 'email': email, 'percentage': percentage})

    shutil.rmtree(SELECTED_FOLDER)
    os.makedirs(SELECTED_FOLDER)
    for candidate in matched_candidates:
        shutil.copy(os.path.join(UPLOAD_FOLDER, candidate['filename']), os.path.join(SELECTED_FOLDER, candidate['filename']))

    return render_template('index.html', uploaded_files=uploaded_files, results=matched_candidates, total_selected=len(matched_candidates), upload_message=None, entered_skills=skills)

@app.route('/download_selected', methods=['GET'])
def download_selected():
    zip_path = os.path.join(STATIC_FOLDER, "selected_resumes.zip")
    if os.path.exists(zip_path):
        os.remove(zip_path)
    shutil.make_archive(zip_path.replace('.zip', ''), 'zip', SELECTED_FOLDER)
    return send_from_directory(STATIC_FOLDER, 'selected_resumes.zip', as_attachment=True)

@app.route("/send_emails", methods=["POST"])
def send_emails():
    interview_date = request.form['interview_date']
    interview_time = request.form['interview_time']
    message_body = request.form['message']
    names = request.form.getlist('candidate_names')
    emails = request.form.getlist('candidate_emails')

    for name, email in zip(names, emails):
        try:
            msg = Message(
                subject="Interview Invitation",
                recipients=[email],
                body=f"""Dear {name},

You have been shortlisted based on your resume.

Interview Details:
Date: {interview_date}
Time: {interview_time}

{message_body if message_body else ''}

Best regards,
ResumeMatchr Team"""
            )
            mail.send(msg)
        except Exception as e:
            print(f"Failed to send email to {email}: {e}")

    flash('Emails sent successfully!', 'success')
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)

from flask import Flask, render_template, request, redirect, send_from_directory, jsonify, flash
import os
import shutil
import fitz  # PyMuPDF
import re
from werkzeug.utils import secure_filename
from flask_mail import Mail, Message

app = Flask(__name__)
app.secret_key = "some_secret_key"

# Mail config
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
import os
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = 'your_email@gmail.com'
mail = Mail(app)

# Folder settings
UPLOAD_FOLDER = 'resumes'
SELECTED_FOLDER = 'selected_resumes'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['SELECTED_FOLDER'] = SELECTED_FOLDER

# Make sure folders exist
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
if not os.path.exists(SELECTED_FOLDER):
    os.makedirs(SELECTED_FOLDER)

# Globals
uploaded_files = []
matched_candidates = []

# --- Helper Functions ---
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

# --- Routes ---
@app.route('/', methods=['GET'])
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
    message = f"{success_count} file(s) uploaded successfully." if success_count else "No valid files uploaded."
    return render_template('index.html', uploaded_files=uploaded_files, upload_message=message, upload_success=True, results=None, total_selected=0, entered_skills='')

@app.route('/clear_uploads', methods=['POST'])
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
    required_skills = skills.lower().split(',')
    required_skills = [s.strip() for s in required_skills if s.strip()]

    if not required_skills:
        return render_template('index.html', uploaded_files=uploaded_files, results=[], total_selected=0, upload_message="Enter valid skills.", upload_success=False, entered_skills=skills)

    for filename in uploaded_files:
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        text = extract_text_from_pdf(filepath)
        matches = sum(1 for skill in required_skills if skill in text)
        percentage = int((matches / len(required_skills)) * 100) if required_skills else 0
        if percentage >= 80:
            name = extract_name(text)
            email = extract_email(text)
            matched_candidates.append({'filename': filename, 'name': name, 'email': email, 'percentage': percentage})

    # Copy selected resumes
    shutil.rmtree(SELECTED_FOLDER)
    os.makedirs(SELECTED_FOLDER)
    for candidate in matched_candidates:
        shutil.copy(os.path.join(UPLOAD_FOLDER, candidate['filename']), os.path.join(SELECTED_FOLDER, candidate['filename']))

    return render_template('index.html', uploaded_files=uploaded_files, results=matched_candidates, total_selected=len(matched_candidates), upload_message=None, entered_skills=skills)

@app.route('/download_selected', methods=['GET'])
def download_selected():
    return jsonify({'path': SELECTED_FOLDER})

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

Congratulations! You have been shortlisted based on your resume.

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
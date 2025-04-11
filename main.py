from flask import Flask, render_template, request, send_from_directory, redirect, url_for, flash
import os
import shutil
import PyPDF2
import docx2txt
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

UPLOAD_FOLDER = 'resumes'
SELECTED_FOLDER = 'selected_resumes'

app = Flask(__name__)
app.secret_key = 'hirescope_secret'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Ensure folders exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SELECTED_FOLDER, exist_ok=True)

def extract_text_from_pdf(pdf_path):
    with open(pdf_path, 'rb') as file:
        reader = PyPDF2.PdfReader(file)
        text = ''
        for page in reader.pages:
            text += page.extract_text()
        return text

def extract_text_from_docx(docx_path):
    return docx2txt.process(docx_path)

def extract_text(file_path):
    if file_path.endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    elif file_path.endswith('.docx'):
        return extract_text_from_docx(file_path)
    elif file_path.endswith('.txt'):
        with open(file_path, 'r', encoding='utf-8') as file:
            return file.read()
    return ''

def calculate_match_score(job_description, resume_text):
    cv = CountVectorizer().fit_transform([job_description, resume_text])
    similarity = cosine_similarity(cv[0:1], cv[1:2])
    return round(float(similarity[0][0]) * 100, 2)

def extract_email(text):
    import re
    match = re.search(r'[\w\.-]+@[\w\.-]+', text)
    return match.group(0) if match else 'Not found'

def extract_name(text):
    lines = text.strip().split('\n')
    for line in lines:
        if len(line.split()) >= 2:
            return line.strip()
    return "Unknown"

def send_interview_email(to_email, name, date, time):
    from_email = os.environ.get("MAIL_USERNAME")
    from_password = os.environ.get("MAIL_PASSWORD")

    subject = "Interview Invitation from HireScope"
    body = f"""
    Dear {name},

    Congratulations! You have been shortlisted based on your resume.
    We are pleased to invite you for an interview scheduled as follows:

    📅 Date: {date}
    ⏰ Time: {time}

    Please confirm your availability by replying to this email.

    Best regards,
    HireScope Team
    """

    msg = MIMEMultipart()
    msg['From'] = from_email
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(from_email, from_password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

@app.route('/', methods=['GET', 'POST'])
def index():
    result = []
    selected_count = 0
    if request.method == 'POST':
        job_description = request.form['job_description']
        resumes = request.files.getlist('resumes')

        for file in resumes:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(file_path)

        for file_name in os.listdir(app.config['UPLOAD_FOLDER']):
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], file_name)
            resume_text = extract_text(file_path)
            match_score = calculate_match_score(job_description, resume_text)
            name = extract_name(resume_text)
            email = extract_email(resume_text)

            if match_score >= 80:
                shutil.copy(file_path, SELECTED_FOLDER)
                selected = True
                selected_count += 1
            else:
                selected = False

            result.append({
                'name': name,
                'email': email,
                'score': match_score,
                'selected': selected,
                'filename': file_name
            })

        result = sorted(result, key=lambda x: x['score'], reverse=True)

    return render_template('index.html', results=result, selected_count=selected_count)

@app.route('/download/<filename>')
def download_resume(filename):
    return send_from_directory(SELECTED_FOLDER, filename)

@app.route('/send_email', methods=['POST'])
def send_email():
    email = request.form['email']
    name = request.form['name']
    date = request.form['date']
    time = request.form['time']

    if send_interview_email(email, name, date, time):
        flash('Interview invitation sent successfully!', 'success')
    else:
        flash('Failed to send email. Check your credentials or internet connection.', 'danger')

    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)

from flask import Flask, render_template, request, send_file
import os
import fitz  # PyMuPDF
import shutil
import zipfile

app = Flask(__name__)
UPLOAD_FOLDER = 'resumes'
SELECTED_FOLDER = 'selected_resumes'
ALLOWED_EXTENSIONS = {'pdf'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# Create folders if not exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(SELECTED_FOLDER, exist_ok=True)

# Mock skill list
required_skills = ['python', 'flask', 'html', 'css', 'sql', 'api', 'django']

# Helper to check extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Extract text from PDF
def extract_text_from_pdf(pdf_path):
    text = ""
    with fitz.open(pdf_path) as doc:
        for page in doc:
            text += page.get_text()
    return text.lower()

# Calculate match percentage
def calculate_match(text, skills):
    matched = [skill for skill in skills if skill in text]
    return len(matched) / len(skills) * 100, matched

@app.route('/', methods=['GET', 'POST'])
def index():
    results = []
    if request.method == 'POST':
        # Save resumes
        files = request.files.getlist('resumes')
        for file in files:
            if file and allowed_file(file.filename):
                filepath = os.path.join(UPLOAD_FOLDER, file.filename)
                file.save(filepath)

        # Clear previously selected
        shutil.rmtree(SELECTED_FOLDER)
        os.makedirs(SELECTED_FOLDER, exist_ok=True)

        # Match logic
        for filename in os.listdir(UPLOAD_FOLDER):
            file_path = os.path.join(UPLOAD_FOLDER, filename)
            text = extract_text_from_pdf(file_path)
            match_percent, matched_skills = calculate_match(text, required_skills)
            results.append({
                'name': filename,
                'match': round(match_percent, 2),
                'skills': matched_skills
            })
            if match_percent >= 80:
                shutil.copy(file_path, os.path.join(SELECTED_FOLDER, filename))

        results.sort(key=lambda x: x['match'], reverse=True)
    return render_template('index.html', results=results)

@app.route('/download')
def download_zip():
    zip_path = 'selected_resumes.zip'
    with zipfile.ZipFile(zip_path, 'w') as zipf:
        for file in os.listdir(SELECTED_FOLDER):
            zipf.write(os.path.join(SELECTED_FOLDER, file), arcname=file)
    return send_file(zip_path, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)

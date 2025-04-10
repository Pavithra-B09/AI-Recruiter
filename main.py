import os
import re
import smtplib
from tkinter import filedialog, Tk, Label, Button, Listbox, END, Entry
from PyPDF2 import PdfReader
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Gmail setup
EMAIL_ADDRESS = "inklude2024@gmail.com"
EMAIL_PASSWORD = "bskw whjddrbukpiv"  # Replace this with your 16-character app password

def extract_text_from_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text.lower()

def extract_email(text):
    email_regex = r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+"
    matches = re.findall(email_regex, text)
    return matches[0] if matches else None

def calculate_skill_match(text, required_skills):
    found_skills = {skill for skill in required_skills if skill in text}
    percentage = int((len(found_skills) / len(required_skills)) * 100)
    return percentage, found_skills

def send_email(to_email, found_skills, percentage, interview_date, interview_time):
    subject = "Interview Invitation from Inklude"
    body = f"""
    Dear Candidate,

    Greetings from Inklude!

    We are pleased to inform you that, based on your resume and skill match ({percentage}%), you have been shortlisted for the next round of our recruitment process.

    Interview Details:
    📅 Date: {interview_date}
    ⏰ Time: {interview_time}
    📍 Mode: In-person (venue details will be shared upon confirmation)

    Please confirm your availability by replying to this email.

    Best regards,
    Talent Acquisition Team
    Inklude
    inklude2024@gmail.com
    """

    msg = MIMEMultipart()
    msg['From'] = EMAIL_ADDRESS
    msg['To'] = to_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.send_message(msg)
            return True
    except Exception as e:
        print("Email error:", e)
        return False

def select_folder():
    folder = filedialog.askdirectory()
    if not folder:
        return
    listbox.delete(0, END)

    # Get input from user entries
    required_skills = set(skill_entry.get().lower().split(','))
    interview_date = date_entry.get()
    interview_time = time_entry.get()

    for file in os.listdir(folder):
        if file.endswith(".pdf"):
            path = os.path.join(folder, file)
            text = extract_text_from_pdf(path)
            match_percent, found_skills = calculate_skill_match(text, required_skills)

            if match_percent >= 80:
                email = extract_email(text)
                if email:
                    success = send_email(email, found_skills, match_percent, interview_date, interview_time)
                    result = f"{file} - {match_percent}% - Email Sent to {email}" if success else f"{file} - {match_percent}% - Email Failed"
                else:
                    result = f"{file} - {match_percent}% - No Email Found"
                listbox.insert(END, result)

# GUI setup
root = Tk()
root.title("Resume Shortlister & Email Sender")

Label(root, text="Enter Required Skills (comma-separated):").pack()
skill_entry = Entry(root, width=60)
skill_entry.pack(pady=5)

Label(root, text="Interview Date (e.g. April 10, 2025):").pack()
date_entry = Entry(root, width=40)
date_entry.pack(pady=5)

Label(root, text="Interview Time (e.g. 10:30 AM):").pack()
time_entry = Entry(root, width=40)
time_entry.pack(pady=5)

Button(root, text="Select Resume Folder", command=select_folder).pack(pady=10)

listbox = Listbox(root, width=100)
listbox.pack(pady=20)

root.mainloop()

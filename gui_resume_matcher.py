import os
import fitz  # PyMuPDF
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext

def extract_text_from_pdf(file_path):
    text = ""
    with fitz.open(file_path) as doc:
        for page in doc:
            text += page.get_text()
    return text.lower()

def match_skills(resume_text, required_skills):
    matched = [skill for skill in required_skills if skill.lower() in resume_text]
    match_percent = (len(matched) / len(required_skills)) * 100
    return match_percent, matched

def browse_folder():
    folder = filedialog.askdirectory()
    folder_path.set(folder)

def start_matching():
    folder = folder_path.get()
    if not folder:
        messagebox.showwarning("Warning", "Please select a folder with resumes.")
        return

    skills = skill_entry.get().split(",")
    required_skills = [s.strip().lower() for s in skills if s.strip()]

    if not required_skills:
        messagebox.showwarning("Warning", "Please enter at least one skill.")
        return

    results_box.delete(1.0, tk.END)
    for file in os.listdir(folder):
        if file.endswith(".pdf"):
            path = os.path.join(folder, file)
            text = extract_text_from_pdf(path)
            percent, matched = match_skills(text, required_skills)

            if percent >= 80:
                results_box.insert(tk.END, f"{file} - {percent:.2f}% matched\n")
                results_box.insert(tk.END, f"Skills matched: {', '.join(matched)}\n\n")

# -------------------- GUI Setup --------------------
root = tk.Tk()
root.title("Resume Matcher")
root.geometry("600x500")
root.configure(padx=10, pady=10)

tk.Label(root, text="Enter Required Skills (comma-separated):").pack(anchor="w")
skill_entry = tk.Entry(root, width=70)
skill_entry.pack(pady=5)

tk.Label(root, text="Select Resume Folder:").pack(anchor="w")
folder_path = tk.StringVar()
tk.Entry(root, textvariable=folder_path, width=50).pack(side="left", padx=(0, 5))
tk.Button(root, text="Browse", command=browse_folder).pack(side="left")

tk.Button(root, text="Start Matching", command=start_matching, bg="green", fg="white").pack(pady=10)

results_box = scrolledtext.ScrolledText(root, width=70, height=15)
results_box.pack()

root.mainloop()

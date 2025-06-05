from flask import Flask, render_template, request, redirect, url_for
import os
import re
import json
from uuid import uuid4
from werkzeug.utils import secure_filename
from pdfminer.high_level import extract_text
import spacy
from nameparser import HumanName

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads/'
app.config['HISTORY_FOLDER'] = 'summaries/'

# Load NLP model
nlp = spacy.load("en_core_web_sm")

# Ensure folders exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['HISTORY_FOLDER'], exist_ok=True)

def extract_details(text):
    email = re.findall(r"[\w\.-]+@[\w\.-]+", text)
    phone = re.findall(r"\+?\d[\d\s().-]{8,}\d", text)

    lines = text.splitlines()
    name = ""
    for line in lines[:5]:
        line = line.strip()
        if line and not any(char.isdigit() for char in line) and len(line.split()) <= 4:
            parsed_name = HumanName(line)
            if parsed_name.first and parsed_name.last:
                name = parsed_name.full_name
                break

    if not name:
        doc = nlp(text)
        for ent in doc.ents:
            if ent.label_ == "PERSON":
                parsed_name = HumanName(ent.text)
                if parsed_name.first and parsed_name.last:
                    name = parsed_name.full_name
                    break

    skills_list = ["Python", "Java", "C++", "SQL", "JavaScript", "React", "Flask", "Django"]
    # Ensure no duplicates
    skills = list({skill for skill in skills_list if skill.lower() in text.lower()})

    experience = []
    for line in text.split('\n'):
        if any(word in line.lower() for word in ["experience", "developer", "engineer", "intern"]):
            experience.append(line.strip())

    return {
        "name": name,
        "email": email[0] if email else "",
        "phone": phone[0] if phone else "",
        "skills": skills,
        "experience": experience
    }

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files['resume']
        if file and file.filename.endswith('.pdf'):
            filename = secure_filename(file.filename)
            unique_name = f"{uuid4().hex}_{filename}"
            path = os.path.join(app.config['UPLOAD_FOLDER'], unique_name)
            file.save(path)

            text = extract_text(path)
            data = extract_details(text)

            # Save to a uniquely named JSON file
            summary_path = os.path.join(app.config['HISTORY_FOLDER'], unique_name.replace('.pdf', '.json'))
            with open(summary_path, 'w') as f:
                json.dump(data, f)

            return redirect(url_for('summary', file=unique_name.replace('.pdf', '.json')))

    return render_template('index.html')

@app.route('/summary')
def summary():
    file = request.args.get('file')
    if not file:
        return redirect(url_for('history'))

    try:
        with open(os.path.join(app.config['HISTORY_FOLDER'], file), 'r') as f:
            data = json.load(f)
        return render_template('summary.html', data=data)
    except FileNotFoundError:
        return "Summary not found.", 404

@app.route('/history')
def history():
    summaries = []
    for fname in os.listdir(app.config['HISTORY_FOLDER']):
        if fname.endswith('.json'):
            with open(os.path.join(app.config['HISTORY_FOLDER'], fname), 'r') as f:
                data = json.load(f)
                summaries.append((fname, data))
    return render_template('history.html', summaries=summaries)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
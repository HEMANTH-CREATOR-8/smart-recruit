# SmartRecruit AI — Resume Matching & Job Recommendation System

A Flask + SQLite academic full-stack project. Candidates upload a PDF/DOCX resume, the system extracts text and a predefined set of skills, then ranks job descriptions using TF-IDF cosine similarity plus skill overlap. When a candidate analyzes a role, the app also shows alternative roles ranked by match score. Recruiters can publish roles and view candidate reports.

## Features
- Candidate and recruiter demo accounts with hashed passwords and session login/logout
- Resume text extraction for text-based PDF and DOCX files (5 MB limit)
- Skill detection from an editable skill dictionary in `app.py`
- Explainable match score: 60% TF-IDF similarity + 40% detected-skill overlap
- Alternative job recommendations and candidate application history
- Recruiter job posting and application-report dashboard
- SQLite persistence; sample jobs can be loaded without duplicate seeding
- Input checks, unique application constraint, safer unique upload filenames, and role checks

## Run on Windows / VS Code
1. Extract this ZIP to a folder, then open that folder in VS Code.
2. Open Terminal in VS Code and create a virtual environment:
   ```powershell
   py -m venv venv
   ```
3. Activate it. If PowerShell blocks activation, use Command Prompt instead (`venv\Scripts\activate.bat`), or run PowerShell's `venv\Scripts\python.exe -m pip install -r requirements.txt` without activating.
4. Install dependencies:
   ```powershell
   python -m pip install -r requirements.txt
   ```
5. Start the app:
   ```powershell
   python app.py
   ```
6. Open `http://127.0.0.1:5000` in your browser.
7. Click **Load Demo Jobs** once on the home page. Register a candidate, upload a text-based PDF/DOCX resume, and analyze a job. Separately register a recruiter demo account to post jobs and view reports.

## Suggested demo flow for tomorrow
1. Load the demo jobs.
2. Register a candidate using a demo email and a password of at least 8 characters.
3. Upload a sample resume with skills that overlap a demo job (Python, SQL, Django, etc.).
4. Click **Analyze Match** and explain the score breakdown and alternative roles.
5. Log out, register/log in as a recruiter, post a job, and show candidate reports.

## Project structure
```
SmartRecruitAI/
├── app.py                    # Flask routes, database models, matching engine
├── requirements.txt
├── README.md
├── templates/                # Jinja HTML pages
├── static/style.css          # Responsive UI styles
└── uploads/                  # Uploaded resumes (created automatically)
```

## Algorithm overview
1. Extract text from the candidate's resume.
2. Detect skill keywords using a configurable dictionary.
3. Vectorize resume and job text with TF-IDF (unigrams and bigrams, English stop words).
4. Compute cosine similarity and detected-skill overlap.
5. Combine: `match = 0.60 × text_similarity + 0.40 × skill_overlap`.
6. Rank alternative jobs by the combined score.

## Important limitations / responsible use
- This is a classroom prototype, not a production hiring system. Match scores are not calibrated probabilities and the 55% label is only a demo threshold.
- Do not use the score as the sole basis for hiring, rejection, or ranking real people. Human review is required; the system does not assess fairness or validate job performance.
- Skill extraction uses a predefined keyword list and may miss synonyms, context, and skills expressed differently.
- Scanned/image-only PDFs are not OCR processed. Use text-based PDFs or DOCX files.
- Recruiter registration is open to make a classroom demo easy. A real deployment must verify recruiter identity, add CSRF protection, rate limiting, privacy controls, malware scanning, secure secret configuration, and production hosting settings.
- The included development secret is for local use only. Set the `SECRET_KEY` environment variable before deployment and do not run with debug mode in production.

## Reset the demo
Stop the server, then delete `smart_recruiting.db` and files inside `uploads/` if you want a clean local demo. The database is recreated automatically on the next start.

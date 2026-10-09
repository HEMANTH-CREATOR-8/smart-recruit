"""SmartRecruit AI — academic resume matching and job recommendation demo."""
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pathlib import Path
from uuid import uuid4
import os, re
import fitz
from docx import Document

BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "dev-key-change-before-deployment"),
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{BASE_DIR / 'smart_recruiting.db'}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    UPLOAD_FOLDER=str(BASE_DIR / "uploads"),
    MAX_CONTENT_LENGTH=5 * 1024 * 1024,
)
Path(app.config["UPLOAD_FOLDER"]).mkdir(parents=True, exist_ok=True)
db = SQLAlchemy(app)
ALLOWED_EXTENSIONS = {"pdf", "docx"}
SKILLS = ["python", "java", "c++", "javascript", "typescript", "html", "css", "react", "angular", "node.js", "node", "django", "flask", "spring boot", "sql", "mysql", "postgresql", "mongodb", "machine learning", "deep learning", "nlp", "tensorflow", "pytorch", "scikit-learn", "pandas", "numpy", "data science", "power bi", "tableau", "git", "github", "docker", "aws", "azure", "rest api", "excel", "communication", "leadership"]

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(160), unique=True, nullable=False, index=True)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(30), nullable=False, default="candidate")
    resume_text = db.Column(db.Text, default="")
    resume_filename = db.Column(db.String(255), default="")
    applications = db.relationship("Application", backref="candidate", cascade="all, delete-orphan")

class Job(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    company = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(120), nullable=False, default="Remote")
    description = db.Column(db.Text, nullable=False)
    skills = db.Column(db.Text, nullable=False)
    applications = db.relationship("Application", backref="job", cascade="all, delete-orphan")

class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    candidate_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    job_id = db.Column(db.Integer, db.ForeignKey("job.id"), nullable=False)
    score = db.Column(db.Float, nullable=False, default=0)
    status = db.Column(db.String(40), nullable=False, default="Applied")
    __table_args__ = (db.UniqueConstraint("candidate_id", "job_id", name="unique_candidate_job"),)

def normalize(text):
    return re.sub(r"\s+", " ", (text or "").lower()).strip()

def extract_text(path):
    try:
        if path.lower().endswith(".pdf"):
            with fitz.open(path) as pdf:
                return "\n".join(page.get_text() for page in pdf).strip()
        if path.lower().endswith(".docx"):
            doc = Document(path)
            return "\n".join(p.text for p in doc.paragraphs).strip()
    except Exception as exc:
        app.logger.warning("Resume extraction failed: %s", exc)
    return ""

def extract_skills(text):
    t = normalize(text)
    return [skill for skill in SKILLS if re.search(r"(?<!\w)" + re.escape(skill) + r"(?!\w)", t)]

def score_match(resume, job):
    resume_text = normalize(resume)
    job_text = normalize(f"{job.title} {job.description} {job.skills}")
    if not resume_text or not job_text:
        return 0.0
    try:
        matrix = TfidfVectorizer(ngram_range=(1, 2), stop_words="english").fit_transform([resume_text, job_text])
        text_score = float(cosine_similarity(matrix[0:1], matrix[1:2])[0][0]) * 100
    except ValueError:
        text_score = 0.0
    resume_skills, job_skills = set(extract_skills(resume_text)), set(extract_skills(job_text))
    skill_score = 100 * len(resume_skills & job_skills) / len(job_skills) if job_skills else 0
    return round(0.60 * text_score + 0.40 * skill_score, 2)

def current_user():
    user_id = session.get("user_id")
    return db.session.get(User, user_id) if user_id else None

def role_required(role):
    user = current_user()
    if not user:
        flash("Please log in first.", "error")
        return None
    if user.role != role:
        flash("You do not have permission to access that feature.", "error")
        return None
    return user

@app.errorhandler(413)
def too_large(_error):
    flash("File is too large. Maximum resume size is 5 MB.", "error")
    return redirect(url_for("dashboard"))

@app.route("/")
def home():
    return render_template("index.html", jobs=Job.query.order_by(Job.id.desc()).all())

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "candidate")
        if not name or len(name) > 120 or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", email):
            flash("Enter a valid name and email address.", "error")
        elif len(password) < 8:
            flash("Password must contain at least 8 characters.", "error")
        elif role not in {"candidate", "recruiter"}:
            flash("Choose a valid account type.", "error")
        elif User.query.filter_by(email=email).first():
            flash("That email is already registered. Please log in.", "error")
        else:
            user = User(name=name, email=email, password=generate_password_hash(password), role=role)
            db.session.add(user); db.session.commit()
            flash("Account created. You can now log in.", "success")
            return redirect(url_for("login"))
    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password, request.form.get("password", "")):
            flash("Invalid email or password.", "error")
        else:
            session.clear(); session["user_id"] = user.id
            return redirect(url_for("dashboard"))
    return render_template("login.html")

@app.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    flash("You have been logged out.", "success")
    return redirect(url_for("home"))

@app.route("/dashboard")
def dashboard():
    user = current_user()
    if not user:
        flash("Please log in to open your dashboard.", "error")
        return redirect(url_for("login"))
    if user.role == "recruiter":
        jobs = Job.query.order_by(Job.id.desc()).all()
        applications = Application.query.order_by(Application.id.desc()).all()
        return render_template("recruiter_dashboard.html", jobs=jobs, applications=applications)
    apps = Application.query.filter_by(candidate_id=user.id).order_by(Application.id.desc()).all()
    jobs = Job.query.order_by(Job.id.desc()).all()
    applied_ids = {a.job_id for a in apps}
    return render_template("candidate_dashboard.html", user=user, apps=apps, jobs=jobs,
                           skills=extract_skills(user.resume_text), applied_ids=applied_ids)

@app.route("/resume", methods=["POST"])
def resume_upload():
    user = role_required("candidate")
    if not user: return redirect(url_for("login" if not current_user() else "dashboard"))
    file = request.files.get("resume")
    if not file or not file.filename:
        flash("Choose a PDF or DOCX resume first.", "error"); return redirect(url_for("dashboard"))
    original = secure_filename(file.filename)
    ext = original.rsplit(".", 1)[-1].lower() if "." in original else ""
    if ext not in ALLOWED_EXTENSIONS:
        flash("Only PDF and DOCX files are supported.", "error"); return redirect(url_for("dashboard"))
    stored_name = f"{uuid4().hex}.{ext}"
    path = os.path.join(app.config["UPLOAD_FOLDER"], stored_name)
    file.save(path)
    text = extract_text(path)
    if not text:
        os.remove(path)
        flash("Could not read text from that file. Use a text-based PDF or DOCX document.", "error")
        return redirect(url_for("dashboard"))
    if user.resume_filename:
        old_path = os.path.join(app.config["UPLOAD_FOLDER"], user.resume_filename)
        if os.path.isfile(old_path):
            try: os.remove(old_path)
            except OSError: pass
    user.resume_filename = stored_name
    user.resume_text = text[:100000]
    db.session.commit()
    flash(f"Resume analyzed. Detected {len(extract_skills(text))} skills from the supported skill list.", "success")
    return redirect(url_for("dashboard"))

@app.route("/jobs/<int:job_id>/apply", methods=["POST"])
def apply(job_id):
    user = role_required("candidate")
    if not user: return redirect(url_for("login" if not current_user() else "dashboard"))
    job = db.get_or_404(Job, job_id)
    if not user.resume_text:
        flash("Upload a resume before applying.", "error"); return redirect(url_for("dashboard"))
    if Application.query.filter_by(candidate_id=user.id, job_id=job.id).first():
        flash("You have already analyzed/applied for this job.", "error"); return redirect(url_for("dashboard"))
    score = score_match(user.resume_text, job)
    # Demo-only guidance label. A human must make all actual hiring decisions.
    status = "Strong Match — Review Suggested" if score >= 55 else "Explore Better-Fit Roles"
    application = Application(candidate_id=user.id, job_id=job.id, score=score, status=status)
    db.session.add(application); db.session.commit()
    return redirect(url_for("result", job_id=job.id))

@app.route("/result/<int:job_id>")
def result(job_id):
    user = current_user()
    if not user:
        flash("Please log in to view analysis.", "error"); return redirect(url_for("login"))
    if user.role != "candidate": return redirect(url_for("dashboard"))
    job = db.get_or_404(Job, job_id)
    application = Application.query.filter_by(candidate_id=user.id, job_id=job.id).first_or_404()
    recommendations = []
    for other in Job.query.filter(Job.id != job.id).all():
        score = score_match(user.resume_text, other)
        if score > 0: recommendations.append((other, score))
    recommendations.sort(key=lambda item: item[1], reverse=True)
    return render_template("result.html", job=job, application=application,
                           skills=extract_skills(user.resume_text), recommendations=recommendations[:5])

@app.route("/add-job", methods=["POST"])
def add_job():
    user = role_required("recruiter")
    if not user: return redirect(url_for("login" if not current_user() else "dashboard"))
    title = request.form.get("title", "").strip()
    company = request.form.get("company", "").strip()
    location = request.form.get("location", "Remote").strip() or "Remote"
    description = request.form.get("description", "").strip()
    skills = request.form.get("skills", "").strip()
    if not all([title, company, description, skills]) or any(len(v) > 5000 for v in [title, company, location, description, skills]):
        flash("Complete all required fields and keep each field under 5,000 characters.", "error")
    else:
        db.session.add(Job(title=title, company=company, location=location, description=description, skills=skills))
        db.session.commit(); flash("Job posted successfully.", "success")
    return redirect(url_for("dashboard"))

@app.route("/seed")
def seed():
    if Job.query.count() == 0:
        demo = [
            ("Python Developer", "TechNova", "Hyderabad", "Build backend services, automate workflows, and integrate REST APIs.", "Python, Django, SQL, REST API, Git"),
            ("Data Analyst", "Insight Labs", "Bengaluru", "Analyze business data and create reports and dashboards for stakeholders.", "Python, SQL, Pandas, Excel, Power BI"),
            ("Machine Learning Intern", "AI Works", "Remote", "Prepare datasets, train baseline models, and evaluate machine learning experiments.", "Python, machine learning, pandas, numpy, scikit-learn"),
            ("Frontend Developer", "WebCraft", "Chennai", "Develop accessible, responsive web pages and reusable interface components.", "HTML, CSS, JavaScript, React, Git"),
            ("Full Stack Developer Intern", "CodeSphere", "Pune", "Build full-stack web applications with APIs, database integration, and testing.", "Python, JavaScript, React, Django, MySQL, REST API")]
        for title, company, location, description, skills in demo:
            db.session.add(Job(title=title, company=company, location=location, description=description, skills=skills))
        db.session.commit(); flash("Five demo jobs have been added.", "success")
    else:
        flash("Demo jobs already exist; no duplicates were added.", "success")
    return redirect(url_for("home"))

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")

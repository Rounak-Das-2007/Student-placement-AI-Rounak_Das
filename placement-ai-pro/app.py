from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.utils import secure_filename
import sqlite3
import os
import re
import json
import joblib
import numpy as np
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "placement.db")
MODEL_PATH = os.path.join(BASE_DIR, "model", "placement_model.pkl")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")

app = Flask(__name__)
app.secret_key = "placement-ai-student-secret"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(os.path.join(BASE_DIR, "model"), exist_ok=True)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS assessments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            cgpa REAL,
            technical REAL,
            dsa REAL,
            communication REAL,
            projects INTEGER,
            internships INTEGER,
            score REAL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            company TEXT NOT NULL,
            role TEXT NOT NULL,
            salary TEXT DEFAULT '',
            status TEXT DEFAULT 'Saved',
            notes TEXT DEFAULT '',
            created_at TEXT NOT NULL,
            updated_at TEXT DEFAULT '',
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.commit()

    # Migration checks for columns in applications table
    cur = conn.cursor()
    cur.execute("PRAGMA table_info(applications)")
    cols = [col["name"] for col in cur.fetchall()]
    if "salary" not in cols:
        cur.execute("ALTER TABLE applications ADD COLUMN salary TEXT DEFAULT ''")
    if "notes" not in cols:
        cur.execute("ALTER TABLE applications ADD COLUMN notes TEXT DEFAULT ''")
    if "updated_at" not in cols:
        cur.execute("ALTER TABLE applications ADD COLUMN updated_at TEXT DEFAULT ''")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS roadmap_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            task_id TEXT NOT NULL,
            is_completed INTEGER DEFAULT 1,
            completed_at TEXT NOT NULL,
            UNIQUE(user_id, task_id),
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)
    conn.commit()
    conn.close()

ROADMAP_WEEKS = [
    {
        "id": "w1",
        "num": "01",
        "title": "Core CS & Programming Mastery",
        "desc": "Solidify object-oriented programming, DBMS schemas, SQL queries, and fundamental aptitude drills.",
        "icon": "⚡",
        "tasks": [
            {
                "id": "w1_t1",
                "day": "Day 1-2",
                "tag": "OOP Concepts",
                "title": "Master OOP Pillars (Java/Python/C++)",
                "desc": "Revise Encapsulation, Polymorphism, Abstraction, Inheritance, and memory allocation differences.",
                "tip": "Be prepared to write code showing runtime polymorphism vs compile-time polymorphism on a whiteboard.",
                "link": "https://www.geeksforgeeks.org/object-oriented-programming-in-cpp/"
            },
            {
                "id": "w1_t2",
                "day": "Day 2-3",
                "tag": "DBMS & SQL",
                "title": "Relational DB & Advanced SQL Queries",
                "desc": "Practice INNER, LEFT, RIGHT, FULL OUTER joins, subqueries, GROUP BY, HAVING, and indexing.",
                "tip": "Companies frequently test: 'Find the 2nd highest salary' using DENSE_RANK() or subqueries.",
                "link": "https://leetcode.com/problemset/database/"
            },
            {
                "id": "w1_t3",
                "day": "Day 4",
                "tag": "OS Fundamentals",
                "title": "Operating Systems & Concurrency",
                "desc": "Process vs Thread, Deadlocks (Coffman conditions), Mutex vs Semaphore, and Virtual Memory paging.",
                "tip": "Explain deadlock prevention vs deadlock avoidance (Banker's algorithm) concisely.",
                "link": "https://www.geeksforgeeks.org/operating-systems/"
            },
            {
                "id": "w1_t4",
                "day": "Day 5",
                "tag": "Computer Networks",
                "title": "Networking Protocols & Architecture",
                "desc": "OSI 7 Layers, TCP vs UDP 3-way handshake, DNS resolution, HTTP vs HTTPS, and Status Codes.",
                "tip": "Know step-by-step what happens when you type https://google.com into your browser address bar.",
                "link": "https://developer.mozilla.org/en-US/docs/Web/HTTP"
            },
            {
                "id": "w1_t5",
                "day": "Day 6",
                "tag": "Aptitude Drill",
                "title": "Quantitative & Logical Aptitude Workout",
                "desc": "Solve 30 practice problems on Time & Work, Speed & Distance, Percentages, and Syllogisms.",
                "tip": "Campus screening rounds filter 60%+ applicants purely through timed aptitude tests.",
                "link": "https://www.indiabix.com/aptitude/questions-and-answers/"
            },
            {
                "id": "w1_t6",
                "day": "Day 7",
                "tag": "Revision",
                "title": "Week 1 Self-Assessment & Core Cheat Sheet",
                "desc": "Summarize key SQL queries and OOP formulas into a 1-page revision sheet. Take a mock test.",
                "tip": "Active recall: explain each concept in simple words as if teaching a beginner.",
                "link": "https://www.geeksforgeeks.org/last-minute-notes-operating-systems/"
            }
        ]
    },
    {
        "id": "w2",
        "num": "02",
        "title": "High-Yield DSA & Problem Solving",
        "desc": "Learn pattern-based problem solving: Two Pointers, Sliding Window, Trees, and Dynamic Programming.",
        "icon": "🧠",
        "tasks": [
            {
                "id": "w2_t1",
                "day": "Day 8-9",
                "tag": "Arrays & Strings",
                "title": "Two Pointers & Sliding Window Patterns",
                "desc": "Solve Kadane's algorithm (Maximum Subarray), 2 Sum, 3 Sum, Longest Substring Without Repeating Characters.",
                "tip": "Always state time and space complexity upfront before typing code.",
                "link": "https://leetcode.com/explore/featured/card/array-and-string/"
            },
            {
                "id": "w2_t2",
                "day": "Day 10-11",
                "tag": "Hashing & Lists",
                "title": "Hash Maps, Sets & Linked List Manipulation",
                "desc": "Reverse a Linked List, Detect Cycle (Floyd's Tortoise and Hare), Merge Two Sorted Lists, LRU Cache basics.",
                "tip": "Handle edge cases cleanly: null pointers, single element, even/odd lengths.",
                "link": "https://leetcode.com/tag/linked-list/"
            },
            {
                "id": "w2_t3",
                "day": "Day 12-13",
                "tag": "Stacks & Queues",
                "title": "Monotonic Stacks & Queue Problems",
                "desc": "Valid Parentheses, Next Greater Element, Min Stack design, and Sliding Window Maximum.",
                "tip": "A monotonic stack is the #1 trick for 'next greater' / 'previous smaller' questions.",
                "link": "https://leetcode.com/tag/stack/"
            },
            {
                "id": "w2_t4",
                "day": "Day 14",
                "tag": "Binary Trees",
                "title": "Tree Traversals (BFS & DFS)",
                "desc": "Inorder, Preorder, Postorder traversals, Level Order (Queue), Max Depth, Invert Binary Tree, Validate BST.",
                "tip": "Master recursion patterns: Base condition -> Left branch -> Right branch -> Combine results.",
                "link": "https://leetcode.com/tag/tree/"
            },
            {
                "id": "w2_t5",
                "day": "Day 15",
                "tag": "Searching & Sorting",
                "title": "Binary Search on Answer & Quick/Merge Sort",
                "desc": "Rotated sorted array search, First/Last position in sorted array, QuickSort partitioning logic.",
                "tip": "Binary search isn't just for arrays—use it whenever the search space is monotonic.",
                "link": "https://leetcode.com/tag/binary-search/"
            },
            {
                "id": "w2_t6",
                "day": "Day 16",
                "tag": "Coding Drill",
                "title": "Timed 90-Minute 3-Problem Coding Contest",
                "desc": "Simulate a live online assessment (OA) with 1 Easy and 2 Medium algorithmic problems.",
                "tip": "Don't spend more than 25 minutes stuck on one problem; test with custom edge cases first.",
                "link": "https://leetcode.com/contest/"
            }
        ]
    },
    {
        "id": "w3",
        "num": "03",
        "title": "ATS Resume, Projects & System Design",
        "desc": "Elevate your resume keywords, craft STAR behavioral stories, and practice fundamental architecture.",
        "icon": "📄",
        "tasks": [
            {
                "id": "w3_t1",
                "day": "Day 17-18",
                "tag": "Resume AI",
                "title": "Quantify Projects with Metrics & Action Verbs",
                "desc": "Convert resume bullet points to XYZ format: 'Accomplished [X] as measured by [Y], by doing [Z]'.",
                "tip": "Use action verbs like 'Architected', 'Optimized', 'Automated' instead of 'Worked on'.",
                "link": "/resume"
            },
            {
                "id": "w3_t2",
                "day": "Day 19",
                "tag": "GitHub & Live Demo",
                "title": "Polish Project Repositories & Live URLs",
                "desc": "Ensure your top 2 projects have clean READMEs, screenshots, architecture diagrams, and deployed links.",
                "tip": "Recruiters and interviewers spend 30 seconds scanning your GitHub pin list—make it shine.",
                "link": "https://github.com"
            },
            {
                "id": "w3_t3",
                "day": "Day 20",
                "tag": "System Design",
                "title": "Basic System Design & Microservice Concepts",
                "desc": "Understand Client-Server, Caching (Redis), Load Balancers, Horizontal vs Vertical scaling, Relational vs NoSQL.",
                "tip": "Explain URL Shortener (TinyURL) or Rate Limiter high-level components with clear diagrams.",
                "link": "https://github.com/donnemartin/system-design-primer"
            },
            {
                "id": "w3_t4",
                "day": "Day 21",
                "tag": "STAR Stories",
                "title": "Craft 4 Core STAR Behavioral Stories",
                "desc": "Prepare stories for: (1) Toughest technical bug, (2) Conflict in team project, (3) Leadership moment, (4) Failure & recovery.",
                "tip": "Structure each answer: Situation (15%), Task (15%), Action (50%), Result (20%).",
                "link": "/interview"
            },
            {
                "id": "w3_t5",
                "day": "Day 22",
                "tag": "HR Prep",
                "title": "Standard HR Questions & 'Tell Me About Yourself'",
                "desc": "Craft an elevator pitch (90 seconds), answer 'Why this company?', and formulate 3 questions to ask interviewer.",
                "tip": "Never say 'I have no questions' at the end of an interview; ask about team tech roadmap or culture.",
                "link": "/interview"
            },
            {
                "id": "w3_t6",
                "day": "Day 23",
                "tag": "Mock Review",
                "title": "Mock Technical Interview & Peer Feedback",
                "desc": "Conduct a 45-minute live mock session with a classmate or friend with live code sharing.",
                "tip": "Think out loud continuously. Interviewers care more about your thought process than instant perfection.",
                "link": "/interview"
            }
        ]
    },
    {
        "id": "w4",
        "num": "04",
        "title": "Company Sprints & Placement Drive Execution",
        "desc": "Target company-specific patterns, run speed drills, organize applications in the Kanban pipeline, and win offers.",
        "icon": "🎯",
        "tasks": [
            {
                "id": "w4_t1",
                "day": "Day 24-25",
                "tag": "Company Archives",
                "title": "Company-Specific Previous Coding Archives",
                "desc": "Solve the 15 most frequent questions asked by TCS, Infosys, Accenture, Cognizant, or your dream tech tier.",
                "tip": "Service tier tests love string manipulations, hashing, and math series. Product tier tests love graphs and DP.",
                "link": "https://www.geeksforgeeks.org/company-preparation/"
            },
            {
                "id": "w4_t2",
                "day": "Day 26",
                "tag": "Pipeline Setup",
                "title": "Organize 10+ Target Roles in Application Pipeline",
                "desc": "Populate your Job Tracker with target campus drives and off-campus portals; verify deadlines and eligibility.",
                "tip": "Track application dates, CTC brackets, and referral contacts systematically in the Kanban board.",
                "link": "/jobs"
            },
            {
                "id": "w4_t3",
                "day": "Day 27",
                "tag": "Rapid-Fire Drill",
                "title": "Rapid-Fire 50 Core CS Interview Flashcards",
                "desc": "Test yourself on SQL queries, OOP definitions, OS memory states, and network status codes.",
                "tip": "Keep each definition under 20 seconds. Clear, crisp terminology builds instant interviewer confidence.",
                "link": "https://www.geeksforgeeks.org/top-10-algorithms-for-coding-interview/"
            },
            {
                "id": "w4_t4",
                "day": "Day 28",
                "tag": "Mock Assessment",
                "title": "Full-Length 2-Hour Placement Simulation",
                "desc": "Take a 60-min aptitude test followed by 60-min coding round under strict zero-distraction conditions.",
                "tip": "Manage time strictly. If stuck for 10 minutes on a question, mark for review and move on.",
                "link": "/assessment"
            },
            {
                "id": "w4_t5",
                "day": "Day 29",
                "tag": "Final Polish",
                "title": "Interview Kit & Documents Checklist",
                "desc": "Organize physical resume copies, college transcripts, ID cards, neat formal wear, and test your web camera/mic.",
                "tip": "Avoid last-night cramming. Sleep at least 7 hours before the drive day for mental sharpness.",
                "link": "#"
            },
            {
                "id": "w4_t6",
                "day": "Day 30",
                "tag": "Placement Drive",
                "title": "Drive Day Execution & Offer Conversion",
                "desc": "Approach interviews with calm confidence. Send thank-you notes and log your interview progress into Kanban.",
                "tip": "Celebrate every milestone! Preparation always compounds.",
                "link": "/jobs"
            }
        ]
    }
]

def get_roadmap_data(user_id):
    conn = get_db()
    rows = conn.execute(
        "SELECT task_id FROM roadmap_progress WHERE user_id = ? AND is_completed = 1", (user_id,)
    ).fetchall()
    conn.close()
    completed_set = {r["task_id"] for r in rows}

    total_tasks = 0
    completed_count = 0
    weeks_data = []

    for week in ROADMAP_WEEKS:
        week_tasks = []
        w_completed = 0
        for task in week["tasks"]:
            total_tasks += 1
            is_done = task["id"] in completed_set
            if is_done:
                completed_count += 1
                w_completed += 1
            t_copy = dict(task)
            t_copy["completed"] = is_done
            week_tasks.append(t_copy)

        w_pct = round((w_completed / len(week["tasks"])) * 100) if week["tasks"] else 0
        w_copy = dict(week)
        w_copy["tasks"] = week_tasks
        w_copy["completed_count"] = w_completed
        w_copy["total_count"] = len(week["tasks"])
        w_copy["percentage"] = w_pct
        weeks_data.append(w_copy)

    pct = round((completed_count / total_tasks) * 100) if total_tasks else 0
    return {
        "weeks": weeks_data,
        "total_tasks": total_tasks,
        "completed_count": completed_count,
        "percentage": pct
    }

def current_user():
    if "user_id" not in session:
        return None
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()
    conn.close()
    return user

def model_predict(cgpa, technical, dsa, communication, projects, internships):
    values = [float(cgpa), float(technical), float(dsa), float(communication), int(projects), int(internships)]
    if os.path.exists(MODEL_PATH):
        try:
            model = joblib.load(MODEL_PATH)
            prediction = float(model.predict([values])[0])
            return round(max(0, min(100, prediction)))
        except Exception:
            pass
    score = (
        float(cgpa) / 10 * 20 +
        float(technical) * 0.20 +
        float(dsa) * 0.20 +
        float(communication) * 0.15 +
        min(int(projects), 5) * 1.5 +
        min(int(internships), 3) * 2
    )
    return round(max(0, min(100, score)))

def recommendations(data):
    areas = [
        ("DSA", float(data["dsa"]), "Practice arrays, strings, linked lists and problem solving."),
        ("Technical Skills", float(data["technical"]), "Strengthen Java/Python, OOP and core CS concepts."),
        ("Communication", float(data["communication"]), "Practice HR answers, introductions and mock interviews."),
    ]
    areas.sort(key=lambda x: x[1])
    return areas[:3]

def dashboard_data(user_id):
    conn = get_db()
    assessments = conn.execute(
        "SELECT * FROM assessments WHERE user_id = ? ORDER BY id DESC", (user_id,)
    ).fetchall()
    applications = conn.execute(
        "SELECT * FROM applications WHERE user_id = ? ORDER BY id DESC", (user_id,)
    ).fetchall()
    conn.close()

    latest = assessments[0] if assessments else None
    if latest:
        score = latest["score"]
        recs = recommendations(latest)
    else:
        score = 0
        recs = [
            ("Profile", 0, "Complete your first placement assessment."),
            ("Resume", 0, "Upload your resume and improve ATS readiness."),
            ("Interview", 0, "Start your first mock interview.")
        ]

    pipeline_counts = {
        "Saved": 0,
        "Applied": 0,
        "Interviewing": 0,
        "Offered": 0,
        "Rejected": 0
    }
    for a in applications:
        st = a["status"] if a["status"] in pipeline_counts else "Saved"
        pipeline_counts[st] += 1

    roadmap = get_roadmap_data(user_id)

    return {
        "latest": latest,
        "score": round(score),
        "assessments": assessments,
        "applications": applications,
        "pipeline_counts": pipeline_counts,
        "roadmap": roadmap,
        "recommendations": recs
    }

@app.context_processor
def inject_user():
    return {"logged_user": current_user()}

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 4:
            flash("Please enter valid details. Password must be at least 4 characters.", "error")
            return redirect(url_for("register"))
        conn = get_db()
        try:
            cur = conn.execute(
                "INSERT INTO users (name,email,password,created_at) VALUES (?,?,?,?)",
                (name, email, password, datetime.now().isoformat())
            )
            conn.commit()
            session["user_id"] = cur.lastrowid
            return redirect(url_for("dashboard"))
        except sqlite3.IntegrityError:
            flash("An account with this email already exists.", "error")
        finally:
            conn.close()
    return render_template("auth.html", mode="register")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = get_db()
        user = conn.execute(
            "SELECT * FROM users WHERE email = ? AND password = ?", (email, password)
        ).fetchone()
        conn.close()
        if user:
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        flash("Invalid email or password.", "error")
    return render_template("auth.html", mode="login")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

@app.route("/dashboard")
def dashboard():
    if not current_user():
        return redirect(url_for("login"))
    return render_template("dashboard.html", data=dashboard_data(session["user_id"]))

@app.route("/assessment", methods=["GET", "POST"])
def assessment():
    user = current_user()
    if not user:
        return redirect(url_for("login"))
    result = None
    if request.method == "POST":
        try:
            values = {
                "cgpa": float(request.form.get("cgpa", 0)),
                "technical": float(request.form.get("technical", 0)),
                "dsa": float(request.form.get("dsa", 0)),
                "communication": float(request.form.get("communication", 0)),
                "projects": int(request.form.get("projects", 0)),
                "internships": int(request.form.get("internships", 0))
            }
            if not (0 <= values["cgpa"] <= 10):
                raise ValueError
            for key in ["technical", "dsa", "communication"]:
                if not (0 <= values[key] <= 100):
                    raise ValueError
            score = model_predict(**values)
            conn = get_db()
            conn.execute("""
                INSERT INTO assessments
                (user_id,cgpa,technical,dsa,communication,projects,internships,score,created_at)
                VALUES (?,?,?,?,?,?,?,?,?)
            """, (
                user["id"], values["cgpa"], values["technical"], values["dsa"],
                values["communication"], values["projects"], values["internships"],
                score, datetime.now().isoformat()
            ))
            conn.commit()
            conn.close()
            result = {
                "score": score,
                "level": "Excellent" if score >= 85 else "Good" if score >= 70 else "Needs Work",
                "recommendations": recommendations(values)
            }
        except Exception:
            flash("Please enter valid assessment values.", "error")
    return render_template("assessment.html", result=result)

@app.route("/resume", methods=["GET", "POST"])
def resume():
    if not current_user():
        return redirect(url_for("login"))
    result = None
    if request.method == "POST":
        file = request.files.get("resume")
        if not file or not file.filename:
            flash("Choose a resume file first.", "error")
            return redirect(url_for("resume"))
        filename = secure_filename(file.filename)
        path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        file.save(path)
        try:
            text = ""
            if filename.lower().endswith(".txt"):
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    text = f.read()
            else:
                text = filename.replace("_", " ").replace("-", " ")
            lower = text.lower()
            keywords = ["python", "java", "sql", "javascript", "react", "git", "dsa", "project", "internship"]
            found = [k for k in keywords if k in lower]
            score = min(100, 45 + len(found) * 6)
            result = {
                "score": score,
                "keywords": found,
                "missing": [k for k in keywords if k not in found],
                "message": "Good starting profile." if score >= 70 else "Add measurable projects, technical skills and internship details."
            }
        except Exception:
            flash("Resume analysis failed.", "error")
    return render_template("resume.html", result=result)

@app.route("/interview")
def interview():
    if not current_user():
        return redirect(url_for("login"))
    questions = [
        {"q": "Tell me about yourself.", "type": "HR"},
        {"q": "Explain OOP and its four main principles.", "type": "Technical"},
        {"q": "What is the difference between INNER JOIN and LEFT JOIN?", "type": "SQL"},
        {"q": "How would you approach a problem you cannot solve immediately?", "type": "HR"},
        {"q": "What is the time complexity of binary search?", "type": "DSA"}
    ]
    return render_template("interview.html", questions=questions)

@app.route("/jobs")
def jobs():
    if not current_user():
        return redirect(url_for("login"))
    user_id = session["user_id"]
    conn = get_db()
    apps = conn.execute(
        "SELECT * FROM applications WHERE user_id = ? ORDER BY id DESC", (user_id,)
    ).fetchall()
    conn.close()

    pipeline = {
        "Saved": [],
        "Applied": [],
        "Interviewing": [],
        "Offered": [],
        "Rejected": []
    }
    for app_row in apps:
        st = app_row["status"] if app_row["status"] in pipeline else "Saved"
        pipeline[st].append(dict(app_row))

    counts = {k: len(v) for k, v in pipeline.items()}
    counts["total"] = len(apps)

    jobs_data = [
        ("TCS", "Graduate Software Engineer", "Java • SQL • Aptitude", "7-9 LPA", 92),
        ("Infosys", "Systems Engineer", "Python • SQL • Communication", "6-8 LPA", 88),
        ("Accenture", "Associate Software Engineer", "Java • DSA • Cloud", "7-10 LPA", 84),
        ("Deloitte", "Analyst", "SQL • Excel • Communication", "7-11 LPA", 79),
        ("Wipro", "Project Engineer", "Java • DBMS • DSA", "5-7 LPA", 76),
        ("Capgemini", "Software Analyst", "Python • SQL • OOP", "5-8 LPA", 73)
    ]
    return render_template("jobs.html", jobs=jobs_data, pipeline=pipeline, counts=counts)

@app.post("/api/applications")
def add_application():
    if not current_user():
        return jsonify({"ok": False, "message": "Login required"}), 401
    payload = request.get_json(silent=True) or {}
    company = payload.get("company", "").strip()
    role = payload.get("role", "").strip()
    salary = payload.get("salary", "").strip()
    status = payload.get("status", "Saved").strip()
    notes = payload.get("notes", "").strip()

    if not company or not role:
        return jsonify({"ok": False, "message": "Company and role are required"}), 400

    valid_statuses = ["Saved", "Applied", "Interviewing", "Offered", "Rejected"]
    if status not in valid_statuses:
        status = "Saved"

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO applications (user_id, company, role, salary, status, notes, created_at, updated_at) VALUES (?,?,?,?,?,?,?,?)",
        (session["user_id"], company, role, salary, status, notes, now, now)
    )
    conn.commit()
    new_id = cur.lastrowid
    conn.close()
    return jsonify({
        "ok": True,
        "application": {
            "id": new_id,
            "company": company,
            "role": role,
            "salary": salary,
            "status": status,
            "notes": notes,
            "created_at": now
        }
    })

@app.post("/api/applications/<int:app_id>/status")
def update_application_status(app_id):
    if not current_user():
        return jsonify({"ok": False, "message": "Login required"}), 401
    payload = request.get_json(silent=True) or {}
    status = payload.get("status", "").strip()
    notes = payload.get("notes")

    valid_statuses = ["Saved", "Applied", "Interviewing", "Offered", "Rejected"]
    if status not in valid_statuses:
        return jsonify({"ok": False, "message": "Invalid status"}), 400

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    conn = get_db()
    if notes is not None:
        conn.execute(
            "UPDATE applications SET status = ?, notes = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (status, notes.strip(), now, app_id, session["user_id"])
        )
    else:
        conn.execute(
            "UPDATE applications SET status = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (status, now, app_id, session["user_id"])
        )
    conn.commit()
    conn.close()
    return jsonify({"ok": True, "status": status})

@app.delete("/api/applications/<int:app_id>")
def delete_application(app_id):
    if not current_user():
        return jsonify({"ok": False, "message": "Login required"}), 401
    conn = get_db()
    conn.execute("DELETE FROM applications WHERE id = ? AND user_id = ?", (app_id, session["user_id"]))
    conn.commit()
    conn.close()
    return jsonify({"ok": True})

@app.route("/roadmap")
def roadmap():
    if not current_user():
        return redirect(url_for("login"))
    roadmap_data = get_roadmap_data(session["user_id"])
    return render_template("roadmap.html", roadmap=roadmap_data)

@app.post("/api/roadmap/toggle")
def toggle_roadmap_task():
    if not current_user():
        return jsonify({"ok": False, "message": "Login required"}), 401
    payload = request.get_json(silent=True) or {}
    task_id = payload.get("task_id", "").strip()
    if not task_id:
        return jsonify({"ok": False, "message": "task_id required"}), 400

    user_id = session["user_id"]
    conn = get_db()
    existing = conn.execute(
        "SELECT id, is_completed FROM roadmap_progress WHERE user_id = ? AND task_id = ?",
        (user_id, task_id)
    ).fetchone()

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    if existing:
        new_status = 0 if existing["is_completed"] == 1 else 1
        conn.execute(
            "UPDATE roadmap_progress SET is_completed = ?, completed_at = ? WHERE id = ?",
            (new_status, now, existing["id"])
        )
        is_completed = (new_status == 1)
    else:
        conn.execute(
            "INSERT INTO roadmap_progress (user_id, task_id, is_completed, completed_at) VALUES (?, ?, 1, ?)",
            (user_id, task_id, now)
        )
        is_completed = True

    conn.commit()
    conn.close()

    stats_data = get_roadmap_data(user_id)
    return jsonify({
        "ok": True,
        "task_id": task_id,
        "is_completed": is_completed,
        "completed_count": stats_data["completed_count"],
        "total_tasks": stats_data["total_tasks"],
        "percentage": stats_data["percentage"]
    })

@app.route("/api/stats")
def stats():
    if not current_user():
        return jsonify({"ok": False}), 401
    data = dashboard_data(session["user_id"])
    return jsonify({
        "ok": True,
        "score": data["score"],
        "applications": len(data["applications"]),
        "assessments": len(data["assessments"]),
        "pipeline": data["pipeline_counts"],
        "roadmap_pct": data["roadmap"]["percentage"]
    })

init_db()

if __name__ == "__main__":
    app.run(debug=True)

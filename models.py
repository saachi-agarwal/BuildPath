"""
models.py
----------
All database logic for BuildPath, using plain sqlite3 (no heavy ORM,
kept simple and readable for a 3rd-semester student).

Note on "accounts": BuildPath has no login/password system. Instead,
a student creates a lightweight profile (name + career goal + skills),
and we remember which profile is "active" using a Flask session.
This keeps things simple while still supporting multiple demo profiles
switching between each other, as the spec asks for.

Tables:
- students            : one row per student profile
- student_skills      : each skill a student has, with proficiency 1-5
- student_interests    : each interest tag a student picked
- projects            : the project catalog (~40 seeded projects)
- project_progress    : tracks status + task checklist per student/project
- project_feedback     : feedback submitted after finishing a project
"""

import sqlite3
import json
from datetime import datetime

DATABASE_NAME = "buildpath.db"


def get_db_connection():
    """Opens a connection to the SQLite database with name-based row access."""
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Creates all tables if they don't already exist. Called once on startup."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # ---------- STUDENTS ----------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            career_goal TEXT NOT NULL,
            experience_level TEXT NOT NULL,
            weekly_hours INTEGER NOT NULL,
            preferred_duration_weeks INTEGER NOT NULL,
            created_at TEXT NOT NULL
        )
    """)

    # ---------- STUDENT SKILLS ----------
    # proficiency is 1 (beginner) to 5 (expert)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_skills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            skill_name TEXT NOT NULL,
            proficiency INTEGER NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
    """)

    # ---------- STUDENT INTERESTS ----------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS student_interests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            interest TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students (id)
        )
    """)

    # ---------- PROJECTS (the catalog) ----------
    # List-like fields (required_skills, learned_skills, career_relevance,
    # interests, technologies, learning_outcomes, roadmap) are stored as
    # JSON text and converted to/from Python lists in the helper functions below.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            category TEXT NOT NULL,
            difficulty TEXT NOT NULL,
            estimated_hours INTEGER NOT NULL,
            duration_weeks INTEGER NOT NULL,
            required_skills TEXT NOT NULL,
            learned_skills TEXT NOT NULL,
            prerequisites TEXT NOT NULL,
            career_relevance TEXT NOT NULL,
            interests TEXT NOT NULL,
            real_world_problem TEXT NOT NULL,
            technologies TEXT NOT NULL,
            learning_outcomes TEXT NOT NULL,
            roadmap TEXT NOT NULL
        )
    """)

    # ---------- PROJECT PROGRESS ----------
    # task_progress is a JSON list of true/false, one per roadmap step.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            project_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'not_started',
            task_progress TEXT NOT NULL,
            started_at TEXT,
            completed_at TEXT,
            FOREIGN KEY (student_id) REFERENCES students (id),
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
    """)

    # ---------- PROJECT FEEDBACK ----------
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS project_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            project_id INTEGER NOT NULL,
            difficulty_rating INTEGER NOT NULL,
            enjoyment_rating INTEGER NOT NULL,
            actual_hours INTEGER NOT NULL,
            learned_expected_skills INTEGER NOT NULL,
            would_build_again INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students (id),
            FOREIGN KEY (project_id) REFERENCES projects (id)
        )
    """)

    conn.commit()
    conn.close()


# ============================================================
# STUDENT FUNCTIONS
# ============================================================

def create_student(name, career_goal, experience_level, weekly_hours, preferred_duration_weeks):
    """Creates a new student profile and returns its new ID."""
    conn = get_db_connection()
    cursor = conn.execute(
        """
        INSERT INTO students (name, career_goal, experience_level, weekly_hours, preferred_duration_weeks, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (name, career_goal, experience_level, weekly_hours, preferred_duration_weeks,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    new_id = cursor.lastrowid
    conn.close()
    return new_id


def get_student(student_id):
    """Fetches a single student profile by ID."""
    conn = get_db_connection()
    student = conn.execute("SELECT * FROM students WHERE id = ?", (student_id,)).fetchone()
    conn.close()
    return student


def get_all_students():
    """Fetches every student profile — used for the 'switch demo profile' picker."""
    conn = get_db_connection()
    students = conn.execute("SELECT * FROM students ORDER BY id ASC").fetchall()
    conn.close()
    return students


# ============================================================
# SKILLS & INTERESTS
# ============================================================

def add_student_skill(student_id, skill_name, proficiency):
    """Adds one skill row for a student."""
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO student_skills (student_id, skill_name, proficiency) VALUES (?, ?, ?)",
        (student_id, skill_name, proficiency),
    )
    conn.commit()
    conn.close()


def get_student_skills(student_id):
    """Returns a dict of {skill_name: proficiency} for a student."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT skill_name, proficiency FROM student_skills WHERE student_id = ?", (student_id,)
    ).fetchall()
    conn.close()
    return {row["skill_name"]: row["proficiency"] for row in rows}


def add_student_interest(student_id, interest):
    """Adds one interest tag for a student."""
    conn = get_db_connection()
    conn.execute(
        "INSERT INTO student_interests (student_id, interest) VALUES (?, ?)",
        (student_id, interest),
    )
    conn.commit()
    conn.close()


def get_student_interests(student_id):
    """Returns a list of interest strings for a student."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT interest FROM student_interests WHERE student_id = ?", (student_id,)
    ).fetchall()
    conn.close()
    return [row["interest"] for row in rows]


# ============================================================
# PROJECTS (catalog)
# ============================================================

def _row_to_project_dict(row):
    """
    Converts a raw database row into a clean Python dictionary,
    parsing the JSON-text list fields back into real Python lists.
    """
    return {
        "id": row["id"],
        "title": row["title"],
        "category": row["category"],
        "difficulty": row["difficulty"],
        "estimated_hours": row["estimated_hours"],
        "duration_weeks": row["duration_weeks"],
        "required_skills": json.loads(row["required_skills"]),
        "learned_skills": json.loads(row["learned_skills"]),
        "prerequisites": row["prerequisites"],
        "career_relevance": json.loads(row["career_relevance"]),
        "interests": json.loads(row["interests"]),
        "real_world_problem": row["real_world_problem"],
        "technologies": json.loads(row["technologies"]),
        "learning_outcomes": json.loads(row["learning_outcomes"]),
        "roadmap": json.loads(row["roadmap"]),
    }


def insert_project(project_dict):
    """
    Inserts one project into the catalog. Used by seed_data.py.
    project_dict is expected to have all the fields listed in the schema,
    with list fields as actual Python lists (they get JSON-encoded here).
    """
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO projects (
            title, category, difficulty, estimated_hours, duration_weeks,
            required_skills, learned_skills, prerequisites, career_relevance,
            interests, real_world_problem, technologies, learning_outcomes, roadmap
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            project_dict["title"],
            project_dict["category"],
            project_dict["difficulty"],
            project_dict["estimated_hours"],
            project_dict["duration_weeks"],
            json.dumps(project_dict["required_skills"]),
            json.dumps(project_dict["learned_skills"]),
            project_dict["prerequisites"],
            json.dumps(project_dict["career_relevance"]),
            json.dumps(project_dict["interests"]),
            project_dict["real_world_problem"],
            json.dumps(project_dict["technologies"]),
            json.dumps(project_dict["learning_outcomes"]),
            json.dumps(project_dict["roadmap"]),
        ),
    )
    conn.commit()
    conn.close()


def get_all_projects():
    """Returns every project in the catalog as a list of dictionaries."""
    conn = get_db_connection()
    rows = conn.execute("SELECT * FROM projects").fetchall()
    conn.close()
    return [_row_to_project_dict(row) for row in rows]


def get_project_by_id(project_id):
    """Returns one project as a dictionary, or None if not found."""
    conn = get_db_connection()
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    conn.close()
    return _row_to_project_dict(row) if row else None


def count_projects():
    """Returns how many projects are currently in the catalog (used to check if seeding is needed)."""
    conn = get_db_connection()
    count = conn.execute("SELECT COUNT(*) as c FROM projects").fetchone()["c"]
    conn.close()
    return count


# ============================================================
# PROGRESS TRACKING
# ============================================================

def start_project(student_id, project_id, num_roadmap_steps):
    """
    Creates a progress row when a student starts a project.
    task_progress starts as a list of False, one per roadmap step.
    """
    conn = get_db_connection()
    task_progress = json.dumps([False] * num_roadmap_steps)
    conn.execute(
        """
        INSERT INTO project_progress (student_id, project_id, status, task_progress, started_at)
        VALUES (?, ?, 'in_progress', ?, ?)
        """,
        (student_id, project_id, task_progress, datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
    )
    conn.commit()
    conn.close()


def get_progress(student_id, project_id):
    """Returns the progress row (as a dict) for one student+project, or None if not started."""
    conn = get_db_connection()
    row = conn.execute(
        "SELECT * FROM project_progress WHERE student_id = ? AND project_id = ?",
        (student_id, project_id),
    ).fetchone()
    conn.close()

    if row is None:
        return None

    return {
        "id": row["id"],
        "status": row["status"],
        "task_progress": json.loads(row["task_progress"]),
        "started_at": row["started_at"],
        "completed_at": row["completed_at"],
    }


def get_all_progress_for_student(student_id):
    """Returns all progress rows for a student (used on the dashboard)."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM project_progress WHERE student_id = ?", (student_id,)
    ).fetchall()
    conn.close()

    return [
        {
            "id": row["id"],
            "project_id": row["project_id"],
            "status": row["status"],
            "task_progress": json.loads(row["task_progress"]),
            "started_at": row["started_at"],
            "completed_at": row["completed_at"],
        }
        for row in rows
    ]


def toggle_task(progress_id, task_index):
    """Flips one roadmap task between done/not done."""
    conn = get_db_connection()
    row = conn.execute("SELECT task_progress FROM project_progress WHERE id = ?", (progress_id,)).fetchone()

    if row is None:
        conn.close()
        return

    tasks = json.loads(row["task_progress"])
    if 0 <= task_index < len(tasks):
        tasks[task_index] = not tasks[task_index]

    conn.execute(
        "UPDATE project_progress SET task_progress = ? WHERE id = ?",
        (json.dumps(tasks), progress_id),
    )
    conn.commit()
    conn.close()


def mark_project_completed(progress_id):
    """Marks a project as completed with today's date."""
    conn = get_db_connection()
    conn.execute(
        "UPDATE project_progress SET status = 'completed', completed_at = ? WHERE id = ?",
        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), progress_id),
    )
    conn.commit()
    conn.close()


# ============================================================
# FEEDBACK
# ============================================================

def add_feedback(student_id, project_id, difficulty_rating, enjoyment_rating,
                  actual_hours, learned_expected_skills, would_build_again):
    """Saves feedback submitted after a student finishes a project."""
    conn = get_db_connection()
    conn.execute(
        """
        INSERT INTO project_feedback
        (student_id, project_id, difficulty_rating, enjoyment_rating, actual_hours,
         learned_expected_skills, would_build_again, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            student_id, project_id, difficulty_rating, enjoyment_rating, actual_hours,
            int(learned_expected_skills), int(would_build_again),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    conn.commit()
    conn.close()


def get_feedback_for_student(student_id):
    """Returns all feedback a student has submitted — used to personalize future recommendations."""
    conn = get_db_connection()
    rows = conn.execute(
        "SELECT * FROM project_feedback WHERE student_id = ?", (student_id,)
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]

"""
routes.py
----------
Every URL in BuildPath and what happens when a student visits it.

No login/password system — a student creates a lightweight profile,
and we remember which one is "active" using session["student_id"].
Switching between demo profiles is just picking a name from a list.
"""

from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, session, flash

import models
import recommender

main = Blueprint("main", __name__)

# ============================================================
# PREDEFINED OPTIONS shown in the profile form dropdowns/checkboxes
# ============================================================
SKILL_OPTIONS = [
    "Python", "JavaScript", "HTML/CSS", "SQL", "Java", "C++",
    "React", "Node.js", "Flask", "Git", "Statistics",
    "Machine Learning", "Pandas", "Networking", "Flutter",
]

CAREER_GOALS = [
    "AI/ML Engineer", "Data Scientist", "Web Developer",
    "Backend Developer", "Full Stack Developer",
    "Cybersecurity Analyst", "App Developer",
]

INTEREST_OPTIONS = [
    "Healthcare", "Education", "Finance", "Productivity", "Entertainment",
    "Social Good", "E-commerce", "College/Student Life",
]

EXPERIENCE_LEVELS = ["Beginner", "Intermediate", "Advanced"]


def profile_required(f):
    """Redirects to the profile picker if no student profile is active yet."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "student_id" not in session:
            flash("Please create or select a profile first.", "error")
            return redirect(url_for("main.profile_switch"))
        return f(*args, **kwargs)
    return decorated_function


# ============================================================
# HOME PAGE
# ============================================================
@main.route("/")
def home():
    return render_template("home.html")


# ============================================================
# SWITCH / PICK A DEMO PROFILE
# ============================================================
@main.route("/profiles")
def profile_switch():
    students = models.get_all_students()
    return render_template("profile_switch.html", students=students)


@main.route("/profiles/select/<int:student_id>")
def select_profile(student_id):
    student = models.get_student(student_id)
    if student is None:
        flash("Profile not found.", "error")
        return redirect(url_for("main.profile_switch"))

    session["student_id"] = student_id
    flash(f"Switched to {student['name']}'s profile.", "success")
    return redirect(url_for("main.dashboard"))


# ============================================================
# CREATE NEW PROFILE
# ============================================================
@main.route("/profiles/new")
def new_profile():
    return render_template(
        "profile_new.html",
        skill_options=SKILL_OPTIONS,
        career_goals=CAREER_GOALS,
        interest_options=INTEREST_OPTIONS,
        experience_levels=EXPERIENCE_LEVELS,
    )


@main.route("/profiles/create", methods=["POST"])
def create_profile():
    name = request.form.get("name", "").strip()
    career_goal = request.form.get("career_goal", "").strip()
    experience_level = request.form.get("experience_level", "").strip()
    weekly_hours = request.form.get("weekly_hours", "").strip()
    preferred_duration_weeks = request.form.get("preferred_duration_weeks", "").strip()

    if not name or not career_goal or not experience_level or not weekly_hours or not preferred_duration_weeks:
        flash("Please fill in all profile fields.", "error")
        return redirect(url_for("main.new_profile"))

    student_id = models.create_student(
        name=name,
        career_goal=career_goal,
        experience_level=experience_level,
        weekly_hours=int(weekly_hours),
        preferred_duration_weeks=int(preferred_duration_weeks),
    )

    # Save each selected skill with its proficiency (1-5 dropdown per skill)
    for skill in SKILL_OPTIONS:
        proficiency = request.form.get(f"skill_{skill}", "0")
        if proficiency and int(proficiency) > 0:
            models.add_student_skill(student_id, skill, int(proficiency))

    # Save selected interests (checkboxes)
    selected_interests = request.form.getlist("interests")
    for interest in selected_interests:
        models.add_student_interest(student_id, interest)

    session["student_id"] = student_id
    flash(f"Welcome, {name}! Your profile is ready.", "success")
    return redirect(url_for("main.dashboard"))


# ============================================================
# DASHBOARD
# ============================================================
@main.route("/dashboard")
@profile_required
def dashboard():
    student = models.get_student(session["student_id"])
    student_skills = models.get_student_skills(student["id"])
    student_interests = models.get_student_interests(student["id"])
    all_projects = models.get_all_projects()

    # Skill gap analysis
    skill_gap = recommender.calculate_skill_gap(student_skills, student["career_goal"], all_projects)

    # Figure out which projects are already started/completed, to exclude
    # them from "top recommendations" and to build the progress lists
    all_progress = models.get_all_progress_for_student(student["id"])
    in_progress_ids = {p["project_id"] for p in all_progress if p["status"] == "in_progress"}
    completed_ids = {p["project_id"] for p in all_progress if p["status"] == "completed"}
    started_ids = in_progress_ids | completed_ids

    recommendations = recommender.get_recommendations(
        student, student_skills, student_interests, all_projects, exclude_project_ids=started_ids
    )[:6]  # top 6 recommendations

    project_lookup = {p["id"]: p for p in all_projects}
    in_progress_projects = [project_lookup[pid] for pid in in_progress_ids if pid in project_lookup]
    completed_projects = [project_lookup[pid] for pid in completed_ids if pid in project_lookup]

    return render_template(
        "dashboard.html",
        student=student,
        skill_gap=skill_gap,
        recommendations=recommendations,
        in_progress_projects=in_progress_projects,
        completed_projects=completed_projects,
    )


# ============================================================
# PROJECT DETAIL
# ============================================================
@main.route("/project/<int:project_id>")
@profile_required
def project_detail(project_id):
    student = models.get_student(session["student_id"])
    student_skills = models.get_student_skills(student["id"])
    student_interests = models.get_student_interests(student["id"])

    project = models.get_project_by_id(project_id)
    if project is None:
        flash("Project not found.", "error")
        return redirect(url_for("main.dashboard"))

    # Recompute this project's score breakdown so we can explain "why recommended"
    score_breakdown = recommender.score_project(student, student_skills, student_interests, project)

    progress = models.get_progress(student["id"], project_id)

    return render_template(
        "project_detail.html",
        project=project,
        score=score_breakdown,
        progress=progress,
    )


# ============================================================
# START A PROJECT
# ============================================================
@main.route("/project/<int:project_id>/start", methods=["POST"])
@profile_required
def start_project(project_id):
    student = models.get_student(session["student_id"])
    project = models.get_project_by_id(project_id)

    if project is None:
        flash("Project not found.", "error")
        return redirect(url_for("main.dashboard"))

    existing = models.get_progress(student["id"], project_id)
    if existing is None:
        models.start_project(student["id"], project_id, len(project["roadmap"]))
        flash(f"Started: {project['title']}", "success")

    return redirect(url_for("main.project_detail", project_id=project_id))


# ============================================================
# TOGGLE A ROADMAP TASK
# ============================================================
@main.route("/project/<int:project_id>/toggle-task/<int:task_index>", methods=["POST"])
@profile_required
def toggle_task(project_id, task_index):
    student = models.get_student(session["student_id"])
    progress = models.get_progress(student["id"], project_id)

    if progress is not None:
        models.toggle_task(progress["id"], task_index)

    return redirect(url_for("main.project_detail", project_id=project_id))


# ============================================================
# COMPLETE A PROJECT -> goes to feedback form
# ============================================================
@main.route("/project/<int:project_id>/complete", methods=["POST"])
@profile_required
def complete_project(project_id):
    student = models.get_student(session["student_id"])
    progress = models.get_progress(student["id"], project_id)

    if progress is not None:
        models.mark_project_completed(progress["id"])

    return redirect(url_for("main.feedback_form", project_id=project_id))


# ============================================================
# FEEDBACK FORM
# ============================================================
@main.route("/project/<int:project_id>/feedback")
@profile_required
def feedback_form(project_id):
    project = models.get_project_by_id(project_id)
    if project is None:
        flash("Project not found.", "error")
        return redirect(url_for("main.dashboard"))
    return render_template("feedback.html", project=project)


@main.route("/project/<int:project_id>/feedback/submit", methods=["POST"])
@profile_required
def submit_feedback(project_id):
    student = models.get_student(session["student_id"])

    difficulty_rating = int(request.form.get("difficulty_rating", 3))
    enjoyment_rating = int(request.form.get("enjoyment_rating", 3))
    actual_hours = int(request.form.get("actual_hours", 0))
    learned_expected_skills = request.form.get("learned_expected_skills") == "yes"
    would_build_again = request.form.get("would_build_again") == "yes"

    models.add_feedback(
        student_id=student["id"],
        project_id=project_id,
        difficulty_rating=difficulty_rating,
        enjoyment_rating=enjoyment_rating,
        actual_hours=actual_hours,
        learned_expected_skills=learned_expected_skills,
        would_build_again=would_build_again,
    )

    flash("Thanks for the feedback! Your next recommendations will reflect this.", "success")
    return redirect(url_for("main.dashboard"))

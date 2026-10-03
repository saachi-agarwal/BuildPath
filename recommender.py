"""
recommender.py
----------------
The BuildPath recommendation engine.

This is deliberately NOT an LLM call — it's plain, explainable Python
logic, which is exactly what makes it possible to show the student
*why* each project was recommended (a requirement of the spec, and
much easier to explain in a viva than "the AI decided").

Scoring formula (each project gets a score out of 100):
    Skill Match       40%
    Career Relevance  25%
    Interest Match    15%
    Difficulty Fit    10%
    Time Fit          10%

A small optional content-based boost (TF-IDF + cosine similarity,
comparing the student's career goal/interests text against each
project's problem description) is blended in on top, as the spec
allows for — but the core score above is what actually drives most
of the ranking and what we explain to the student.
"""

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# A rough difficulty ladder used to compare "project difficulty"
# against "student experience level"
DIFFICULTY_LEVEL = {"Easy": 1, "Medium": 2, "Hard": 3}
EXPERIENCE_LEVEL = {"Beginner": 1, "Intermediate": 2, "Advanced": 3}


def calculate_skill_match(student_skills, project):
    """
    Skill Match (40%): how many of the project's required skills
    the student already has, weighted by their proficiency.
    Returns a 0-1 score plus the lists used to explain it.
    """
    required = project["required_skills"]

    if not required:
        return 1.0, [], []

    known = []
    missing = []
    total_proficiency = 0

    for skill in required:
        proficiency = student_skills.get(skill, 0)
        if proficiency > 0:
            known.append(skill)
            total_proficiency += proficiency
        else:
            missing.append(skill)

    # Average proficiency (out of 5) across required skills the student
    # actually knows, scaled down by how many required skills are missing.
    coverage = len(known) / len(required)
    avg_proficiency = (total_proficiency / len(known) / 5) if known else 0

    score = coverage * 0.6 + avg_proficiency * 0.4
    return score, known, missing


def calculate_career_relevance(student_career_goal, project):
    """Career Relevance (25%): does this project relate to the student's chosen career goal?"""
    if student_career_goal in project["career_relevance"]:
        return 1.0
    return 0.0


def calculate_interest_match(student_interests, project):
    """Interest Match (15%): how many of the student's interests this project touches on."""
    if not student_interests:
        return 0.5  # neutral score if the student picked no interests

    overlap = set(student_interests) & set(project["interests"])
    return len(overlap) / len(student_interests) if student_interests else 0


def calculate_difficulty_fit(experience_level, project):
    """
    Difficulty Fit (10%): projects roughly matching the student's experience
    level score highest; a full score for exact match, partial credit for
    being one level off (to avoid being overly strict).
    """
    exp_num = EXPERIENCE_LEVEL.get(experience_level, 1)
    diff_num = DIFFICULTY_LEVEL.get(project["difficulty"], 1)
    gap = abs(exp_num - diff_num)

    if gap == 0:
        return 1.0
    elif gap == 1:
        return 0.6
    else:
        return 0.2


def calculate_time_fit(weekly_hours, preferred_duration_weeks, project):
    """
    Time Fit (10%): does the project's expected duration fit within
    what the student said they have available?
    """
    available_hours = weekly_hours * preferred_duration_weeks

    if available_hours <= 0:
        return 0.5

    ratio = project["estimated_hours"] / available_hours

    if ratio <= 1.0:
        return 1.0  # comfortably fits
    elif ratio <= 1.5:
        return 0.6  # a bit of a stretch
    else:
        return 0.2  # unrealistic given their time budget


def calculate_content_similarity(student_career_goal, student_interests, project):
    """
    Optional content-based boost using TF-IDF + cosine similarity,
    comparing the student's career goal/interests as text against
    the project's real-world problem description and technologies.
    This adds a small amount of nuance beyond exact tag matching.
    """
    student_text = student_career_goal + " " + " ".join(student_interests)
    project_text = project["real_world_problem"] + " " + " ".join(project["technologies"])

    try:
        vectorizer = TfidfVectorizer(stop_words="english")
        tfidf_matrix = vectorizer.fit_transform([student_text, project_text])
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return float(similarity)
    except ValueError:
        # Happens if the text is too short/empty for TF-IDF to build a vocabulary
        return 0.0


def score_project(student, student_skills, student_interests, project):
    """
    Combines all five weighted factors (+ a small content-similarity
    boost) into one final score out of 100, and returns a breakdown
    dictionary that the templates use to explain the recommendation.
    """
    skill_score, known_skills, missing_skills = calculate_skill_match(student_skills, project)
    career_score = calculate_career_relevance(student["career_goal"], project)
    interest_score = calculate_interest_match(student_interests, project)
    difficulty_score = calculate_difficulty_fit(student["experience_level"], project)
    time_score = calculate_time_fit(student["weekly_hours"], student["preferred_duration_weeks"], project)
    content_score = calculate_content_similarity(student["career_goal"], student_interests, project)

    weighted_total = (
        skill_score * 0.40
        + career_score * 0.25
        + interest_score * 0.15
        + difficulty_score * 0.10
        + time_score * 0.10
    )

    # Content similarity is a small extra nudge (max +5 points), it never
    # dominates the explainable weighted score above.
    final_score = round((weighted_total * 100) + (content_score * 5), 1)
    final_score = min(final_score, 100)

    return {
        "project": project,
        "final_score": final_score,
        "skill_score_pct": round(skill_score * 100),
        "career_score_pct": round(career_score * 100),
        "interest_score_pct": round(interest_score * 100),
        "difficulty_score_pct": round(difficulty_score * 100),
        "time_score_pct": round(time_score * 100),
        "known_skills": known_skills,
        "missing_skills": missing_skills,
        "matched_interests": list(set(student_interests) & set(project["interests"])),
    }


def get_recommendations(student, student_skills, student_interests, all_projects, exclude_project_ids=None):
    """
    Scores every project in the catalog and returns them sorted by
    score, highest first. exclude_project_ids lets the dashboard skip
    projects the student has already started/completed.
    """
    exclude_project_ids = exclude_project_ids or set()

    scored = [
        score_project(student, student_skills, student_interests, project)
        for project in all_projects
        if project["id"] not in exclude_project_ids
    ]

    scored.sort(key=lambda x: x["final_score"], reverse=True)
    return scored


def calculate_skill_gap(student_skills, career_goal, all_projects):
    """
    Builds a simple skill-gap analysis for the dashboard: skills the
    student already has, and important skills they're missing for
    their chosen career — based on which skills show up most often
    in projects relevant to that career goal.
    """
    relevant_projects = [p for p in all_projects if career_goal in p["career_relevance"]]

    skill_frequency = {}
    for project in relevant_projects:
        for skill in project["required_skills"]:
            skill_frequency[skill] = skill_frequency.get(skill, 0) + 1

    known_skills = list(student_skills.keys())
    missing_skills = [
        skill for skill, _ in sorted(skill_frequency.items(), key=lambda x: x[1], reverse=True)
        if skill not in student_skills
    ]

    improving_skills = [skill for skill, level in student_skills.items() if level < 3]

    return {
        "known_skills": known_skills,
        "improving_skills": improving_skills,
        "missing_skills": missing_skills[:8],  # top 8 most relevant missing skills
    }

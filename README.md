# BuildPath

BuildPath is a project-based learning recommender for college students and
beginner programmers. It answers the question every student eventually asks:
**"I know what career I want — but what project should I actually build next?"**

A student creates a lightweight profile (career goal, experience level, skills
with proficiency, interests, and available time), and BuildPath:

- Analyzes their **skill gap** against their chosen career path
- Recommends the best-fit projects from a catalog of 35 real-world projects,
  using an **explainable weighted scoring system** (not an LLM black box)
- Shows exactly **why** each project was recommended (skill match, career
  relevance, interest match, difficulty fit, time fit)
- Gives every project a **step-by-step roadmap** the student can check off
- Collects feedback after each completed project to improve future
  recommendations

## Features

- Lightweight multi-profile system (no passwords — switch between demo profiles)
- Skill-gap analysis (known / improving / missing skills)
- Explainable recommendation engine: 40% skill match, 25% career relevance,
  15% interest match, 10% difficulty fit, 10% time fit, plus a small
  TF-IDF/cosine-similarity content boost
- 35-project catalog across AI/ML, Data Science, Web Development, Backend
  Development, Cybersecurity, App Development, Productivity, and
  College/Student Problems
- Per-project roadmap with a checkable task list
- Post-completion feedback form

## Installation

```
git clone https://github.com/saachi-agarwal/buildpath.git
cd buildpath
pip install -r requirements.txt
```

Create a `.env` file in the project root with:
```
SECRET_KEY=any_random_text_here
```

## How to Run

```
python app.py
```

Then open `http://127.0.0.1:5000` in your browser. The project catalog is
seeded automatically into `buildpath.db` the first time the app runs.

## Folder Structure

```
BuildPath/
├── app.py              # Entry point — creates the app, seeds the database
├── models.py            # All database tables and queries (SQLite)
├── seed_data.py          # The 35-project catalog
├── recommender.py        # The weighted scoring / recommendation engine
├── routes.py             # Every URL/page and what it does
├── requirements.txt
├── templates/            # HTML pages (Jinja2)
└── static/
    ├── css/style.css     # Styling
    └── js/main.js        # Small UI interactions
```

## Technology Used

- **Backend:** Python, Flask
- **Database:** SQLite
- **Recommendation engine:** Plain Python weighted scoring + scikit-learn
  (TF-IDF, cosine similarity) for a small content-based boost
- **Frontend:** HTML, CSS, Jinja2 templating

## Future Improvements

- Let students add their own custom projects to the catalog
- Weight the recommendation engine using past feedback, not just the
  initial profile
- Add a visual learning-path graph (e.g. Python → Pandas → ML)
- Export a completed project's roadmap as a shareable certificate/summary

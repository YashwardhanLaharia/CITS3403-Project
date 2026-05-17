# SplitMate

A collaborative expense-splitting web app built for CITS3403 Agile Web Development at UWA. SplitMate helps groups of people track shared expenses and figure out who owes what, so nobody has to do the maths themselves.

Think share houses, group holidays, dinners out - anywhere a group of people are splitting costs over time.

## Team

| Name | UWA ID | GitHub |
|------|--------|--------|
| Yashwardhan Laharia | 24295462 | [YashwardhanLaharia](https://github.com/YashwardhanLaharia) |
| Aman Sohail | 24307949 | [amansohail22](https://github.com/amansohail22) |
| Stefan Ciutina | 24466541 | [stfn-c](https://github.com/stfn-c) |

## What it does

- **Accounts** - sign up, log in, manage your profile
- **Groups** - create a group or join one with an invite code
- **Expenses** - log shared expenses with amounts, categories, and dates
- **Dashboard** - see who's paid what, spending breakdowns by category, and recent activity
- **Settlements** - automatic calculation of who owes whom and how much

## Tech stack

| Layer | Technology |
|-------|------------|
| Frontend | HTML, CSS, JavaScript, Bootstrap |
| Backend | Flask, Jinja2 |
| Database | SQLite via SQLAlchemy |
| Async | AJAX for live updates |
| Testing | unittest, Selenium |

## Getting started

**Prerequisites:** Python 3.10+

```bash
# Clone the repo
git clone https://github.com/YashwardhanLaharia/CITS-3403-Project.git
cd CITS-3403-Project

# Set up a virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up the database
flask db upgrade

# Run the app
flask run
```

The app will be available at `http://localhost:5000`.

## Running tests

```bash
# Unit tests
python -m pytest tests/

# Selenium tests (requires the app to be running)
python -m pytest tests/selenium/
```

## How we work

We follow a structured branching and issue workflow. Every feature gets an issue, every issue gets a branch, and every branch gets a PR. Details are in [`documents/planning.md`](documents/planning.md).

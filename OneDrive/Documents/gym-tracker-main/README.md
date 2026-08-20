# Gym Tracker – Ayush

A local-first, personal fitness tracking system built with Python, SQLite, and Streamlit.
Track your daily metrics (weight, sleep, activity), log workouts and exercises, and visualize progress locally.

## Project Structure

- `gym_log.db`: Auto-generated SQLite database.
- `schema.sql`: SQL schema defining all tables.
- `db/`: Database configuration and initialization code.
- `scripts/`: Python CLI scripts for adding tracking data from the terminal.
- `app/`: Streamlit dashboard codebase.
- `data/`: Per-day JSON files (`YYYY-MM-DD.json`) — the canonical, git-tracked history of every logged day.

## Setup Instructions

1. **Install Dependencies**
   Ensure you have Python installed, then install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

2. **Initialize the Database**
   Before running anything, create the SQLite database using:
   ```bash
   python db/init_db.py
   ```
   This will read `schema.sql` and produce `gym_log.db` in this folder.

## Usage

### 1. Data Logging (CLI)
You can log data using the minimal terminal scripts in the `scripts/` directory:

- **Log Daily Metrics** (Sleep, weight, general activity):
  ```bash
  python scripts/insert_day.py
  ```

- **Log a Workout** (Exercises, sets, weights):
  ```bash
  python scripts/insert_workout.py
  ```

- **Log a Meal** (Macros and calories):
  ```bash
  python scripts/insert_meal.py
  ```

### 2. Streamlit Dashboard
To view your progress visually, start the local Streamlit server:

```bash
streamlit run app/app.py
```
This will open up a localhost web page in your default browser where you can view charts mapping weight, sleep, habits, and exercise progression.

## Data History (no DB backups needed)
Every logged day lives as its own JSON file in `data/YYYY-MM-DD.json`, in the exact schema `scripts/import_json.py` consumes. The database can be rebuilt from scratch at any time:

```bash
python3 db/init_db.py
for f in data/20*.json; do python3 scripts/import_json.py "$f"; done
```

Keep the JSON files committed to git — they are the backup. To sync files from the DB (e.g. after a manual DB edit): `python3 scripts/export_days.py`.

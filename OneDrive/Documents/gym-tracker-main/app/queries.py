"""Data loading for the dashboard. Every function returns a pandas DataFrame."""

import glob
import os
import sqlite3
import subprocess
import sys

import pandas as pd
import streamlit as st

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.environ.get("GYM_LOG_DB_PATH", os.path.join(ROOT, "gym_log.db"))


def _json_files():
    return sorted(glob.glob(os.path.join(ROOT, "data", "20*.json")))


def _rebuild_db():
    """Rebuild gym_log.db atomically: build to a sibling temp path, then swap.

    If any import fails partway, the partial DB is discarded and DB_PATH is left
    untouched (or removed if it didn't exist). Without this, a partial rebuild
    would leave the real DB with only the imports that succeeded, plus a fresh
    mtime — permanently defeating the "is any JSON newer than the db?" check.
    """
    tmp_path = DB_PATH + ".rebuild.tmp"
    if os.path.exists(tmp_path):
        os.remove(tmp_path)
    env = {**os.environ, "GYM_LOG_DB_PATH": tmp_path}
    try:
        subprocess.run([sys.executable, os.path.join(ROOT, "db", "init_db.py")],
                       cwd=ROOT, check=True, env=env)
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "seed_aliases.py")],
                       cwd=ROOT, check=True, env=env)
        for f in _json_files():
            subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "import_json.py"), f],
                           cwd=ROOT, check=True, capture_output=True, env=env)
    except Exception:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
    os.replace(tmp_path, DB_PATH)


def ensure_db(force=False):
    """Build gym_log.db from the committed per-day JSON history.

    The .db file is gitignored, so on a fresh clone (e.g. Streamlit Community
    Cloud) the database is reconstructed from data/YYYY-MM-DD.json — the JSONs
    are the canonical history. The container persists across redeploys, so a
    plain "build once" check would never pick up JSON files added by later
    pushes; rebuild whenever any JSON is newer than the db, or when forced
    (e.g. the dashboard's "Refresh data" button).
    """
    if force or not os.path.exists(DB_PATH):
        _rebuild_db()
        return
    db_mtime = os.path.getmtime(DB_PATH)
    if any(os.path.getmtime(f) > db_mtime for f in _json_files()):
        _rebuild_db()


def _read(sql, params=()):
    conn = sqlite3.connect(DB_PATH)
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


@st.cache_data(ttl=300)
def load_daily():
    """One row per calendar day (continuous index): intake, macros, weight, sleep, activity."""
    df = _read("""
        SELECT d.date,
               d.overall_rpe, d.gym_minutes,
               bm.weight, bm.body_fat_pct, bm.fat_mass_kg,
               bm.skeletal_muscle_mass_kg, bm.muscle_mass_kg, bm.visceral_fat, bm.bmr_kcal,
               sl.total_sleep_minutes,
               a.move_calories, a.exercise_minutes, a.steps, a.distance_km,
               ds.total_calories AS intake, ds.total_protein AS protein,
               ds.total_carbs AS carbs, ds.total_fat AS fat, ds.total_fiber AS fiber
        FROM days d
        LEFT JOIN body_metrics bm ON bm.day_id = d.id
        LEFT JOIN sleep_logs sl ON sl.day_id = d.id
        LEFT JOIN activity_logs a ON a.day_id = d.id
        LEFT JOIN daily_summary ds ON ds.day_id = d.id
        ORDER BY d.date
    """)
    df["date"] = pd.to_datetime(df["date"])
    df = df.set_index("date")
    full_range = pd.date_range(df.index.min(), df.index.max(), freq="D")
    return df.reindex(full_range)


@st.cache_data(ttl=300)
def load_sets():
    """One row per lifting set with exercise metadata and date."""
    df = _read("""
        SELECT d.date, ee.exercise_name, ee.muscle_group, ee.equipment,
               es.set_number, es.weight, es.reps
        FROM exercise_sets es
        JOIN exercise_entries ee ON es.exercise_entry_id = ee.id
        JOIN workouts w ON ee.workout_id = w.id
        JOIN days d ON w.day_id = d.id
        WHERE es.weight IS NOT NULL AND es.reps IS NOT NULL
        ORDER BY d.date
    """)
    df["date"] = pd.to_datetime(df["date"])
    df["est_1rm"] = df["weight"] * (1 + df["reps"] / 30.0)  # Epley
    return df


@st.cache_data(ttl=300)
def load_workout_days():
    df = _read("""
        SELECT d.date, w.duration_minutes, w.notes, d.overall_rpe
        FROM workouts w JOIN days d ON w.day_id = d.id ORDER BY d.date
    """)
    df["date"] = pd.to_datetime(df["date"])
    return df


@st.cache_data(ttl=300)
def load_micros():
    """One row per day with estimated micronutrient intake (may be empty)."""
    df = _read("""
        SELECT d.date, m.calcium_mg, m.iron_mg, m.zinc_mg, m.b12_ug, m.potassium_mg,
               m.sodium_mg, m.vitamin_c_mg, m.vitamin_d_ug, m.omega3_g, m.magnesium_mg
        FROM micros m JOIN days d ON m.day_id = d.id ORDER BY d.date
    """)
    if not df.empty:
        df["date"] = pd.to_datetime(df["date"])
        df = df.set_index("date")
    return df


@st.cache_data(ttl=300)
def load_recent_meals(days=14):
    return _read("""
        SELECT d.date, m.meal_type, m.description, m.calories, m.protein, m.fiber
        FROM meals m JOIN days d ON m.day_id = d.id
        WHERE d.date >= date((SELECT MAX(date) FROM days), ?)
        ORDER BY d.date DESC, m.id
    """, (f"-{days} days",))

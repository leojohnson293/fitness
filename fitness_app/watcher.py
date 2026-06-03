"""
JSON Watcher — Fitness Tracker
================================
Watches a folder for new JSON files, parses them, and posts
the data to your FastAPI app automatically.

Install dependencies:
    pip install watchdog requests

Run:
    python watcher.py

Then AirDrop JSON files to your Mac and they'll be logged automatically.
Processed files are moved to a 'processed' subfolder so they don't get
imported twice.

JSON formats supported
----------------------

Meal:
    {
        "type": "meal",
        "date": "2026-05-04",
        "meal_type": "Breakfast",
        "description": "4 egg omelette + 150g Greek yogurt",
        "calories": 450,
        "protein_g": 55,
        "carbs_g": 10,
        "fat_g": 28,
        "fibre_g": 2
    }

Weight:
    {
        "type": "weight",
        "date": "2026-05-04",
        "weight_kg": 82.8,
        "waist_cm": 84.5,
        "notes": "Morning fasted"
    }

Workout:
    {
        "type": "workout",
        "date": "2026-05-04",
        "session_type": "Upper A — Push (calisthenics)",
        "duration_min": 60,
        "rpe": 7,
        "notes": "Felt strong, new PB on ring dips",
        "sets": [
            {"exercise": "Ring push-up", "set_number": 1, "reps": 10, "weight_kg": 0, "notes": "clean"},
            {"exercise": "Ring push-up", "set_number": 2, "reps": 9, "weight_kg": 0}
        ]
    }
"""

import json
import shutil
import time
import requests
from datetime import date
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# ── Config ────────────────────────────────────────────────────────────────────

# Folder to watch — defaults to ~/Downloads (where AirDrop saves files)
WATCH_FOLDER = Path.home() / "Downloads"

# Where processed files are moved after successful import
PROCESSED_FOLDER = WATCH_FOLDER / "fitness_processed"

# Your FastAPI base URL
API_URL = "http://localhost:8000"

# ── Colours for terminal output ───────────────────────────────────────────────
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

def log(msg, colour=RESET):
    timestamp = time.strftime("%H:%M:%S")
    print(f"{colour}{BOLD}[{timestamp}]{RESET} {colour}{msg}{RESET}")


# ── API calls ─────────────────────────────────────────────────────────────────

def post_meal(data: dict):
    payload = {
        "log_date":    data.get("date", str(date.today())),
        "meal_type":   data.get("meal_type"),
        "description": data.get("description"),
        "calories":    data.get("calories"),
        "protein_g":   data.get("protein_g"),
        "carbs_g":     data.get("carbs_g"),
        "fat_g":       data.get("fat_g"),
        "fibre_g":     data.get("fibre_g"),
    }
    r = requests.post(f"{API_URL}/meals", json=payload)
    r.raise_for_status()
    return r.json()


def post_weight(data: dict):
    payload = {
        "log_date":  data.get("date", str(date.today())),
        "weight_kg": data["weight_kg"],
        "waist_cm":  data.get("waist_cm"),
        "notes":     data.get("notes"),
    }
    r = requests.post(f"{API_URL}/weight", json=payload)
    r.raise_for_status()
    return r.json()


def post_workout(data: dict):
    payload = {
        "log_date":     data.get("date", str(date.today())),
        "session_type": data.get("session_type"),
        "duration_min": data.get("duration_min"),
        "rpe":          data.get("rpe"),
        "notes":        data.get("notes"),
        "sets":         data.get("sets", []),
    }
    r = requests.post(f"{API_URL}/workouts", json=payload)
    r.raise_for_status()
    return r.json()


# ── File processor ────────────────────────────────────────────────────────────

def process_file(path: Path):
    log(f"Found: {path.name}", YELLOW)

    # Small delay to make sure AirDrop has finished writing the file
    time.sleep(1)

    try:
        with open(path, "r") as f:
            data = json.load(f)
    except Exception as e:
        log(f"Could not parse {path.suffix.upper()} in {path.name}: {e}", RED)
        return

    if not isinstance(data, dict):
        log(f"Skipping {path.name} — not a valid JSON dictionary", RED)
        return

    entry_type = str(data.get("type", "")).lower()

    try:
        if entry_type == "meal":
            result = post_meal(data)
            log(f"✓ Meal logged — {result.get('description', '')} ({result.get('calories', '?')} kcal)", GREEN)

        elif entry_type == "weight":
            result = post_weight(data)
            log(f"✓ Weight logged — {result.get('weight_kg')} kg", GREEN)

        elif entry_type == "workout":
            result = post_workout(data)
            sets_count = len(result.get("sets", []))
            log(f"✓ Workout logged — {result.get('session_type', '')} · {sets_count} sets", GREEN)

        else:
            log(f"Skipping {path.name} — unknown type '{entry_type}' (expected: meal, weight, workout)", RED)
            return

        # Move to processed folder
        PROCESSED_FOLDER.mkdir(exist_ok=True)
        dest = PROCESSED_FOLDER / path.name
        # Avoid overwriting if filename already exists
        if dest.exists():
            stem = path.stem
            suffix = path.suffix
            dest = PROCESSED_FOLDER / f"{stem}_{int(time.time())}{suffix}"
        shutil.move(str(path), str(dest))
        log(f"  Moved to fitness_processed/{dest.name}", YELLOW)

    except requests.exceptions.ConnectionError:
        log("Could not reach API — is uvicorn running?", RED)
    except requests.exceptions.HTTPError as e:
        log(f"API error: {e.response.status_code} — {e.response.text}", RED)
    except KeyError as e:
        log(f"Missing required field in JSON: {e}", RED)
    except Exception as e:
        log(f"Unexpected error: {e}", RED)


# ── Watchdog handler ──────────────────────────────────────────────────────────

class JSONHandler(FileSystemEventHandler):
    def on_created(self, event):
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() == ".json":
            # Ignore files already in the processed subfolder
            if "fitness_processed" not in str(path):
                process_file(path)

    def on_moved(self, event):
        # AirDrop sometimes triggers a move event instead of create
        if event.is_directory:
            return
        path = Path(event.dest_path)
        if path.suffix.lower() == ".json":
            if "fitness_processed" not in str(path):
                process_file(path)


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    PROCESSED_FOLDER.mkdir(exist_ok=True)

    print(f"\n{BOLD}Fitness JSON Watcher{RESET}")
    print(f"Watching: {WATCH_FOLDER}")
    print(f"API:      {API_URL}")
    print(f"Processed files → {PROCESSED_FOLDER}")
    print(f"\nAirDrop a .json file to your Mac to log it automatically.")
    print(f"Press Ctrl+C to stop.\n")

    observer = Observer()
    observer.schedule(JSONHandler(), str(WATCH_FOLDER), recursive=False)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        log("Stopping watcher...", YELLOW)
        observer.stop()

    observer.join()
    log("Stopped.", YELLOW)

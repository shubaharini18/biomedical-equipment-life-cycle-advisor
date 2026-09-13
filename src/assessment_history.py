"""Simple local JSON-backed assessment history for the biomedical equipment advisor."""

import json
from pathlib import Path

HISTORY_FILE = Path(__file__).resolve().parents[1] / "data" / "assessment_history.json"


def ensure_history_file():
    """Create the history file if it does not already exist."""
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if not HISTORY_FILE.exists():
        HISTORY_FILE.write_text("[]\n", encoding="utf-8")


def load_assessment_history():
    """Load stored assessments or return an empty list if the file is missing/empty."""
    try:
        if not HISTORY_FILE.exists():
            return []

        content = HISTORY_FILE.read_text(encoding="utf-8").strip()
        if not content:
            return []

        data = json.loads(content)
        if isinstance(data, list):
            return data

        return []
    except (json.JSONDecodeError, OSError, ValueError):
        return []


def save_assessment(assessment_entry):
    """Append one assessment entry to the local JSON history file."""
    ensure_history_file()
    history = load_assessment_history()
    history.append(assessment_entry)
    HISTORY_FILE.write_text(json.dumps(history, indent=2), encoding="utf-8")


def clear_assessment_history():
    """Remove all stored assessments from the local JSON history file."""
    ensure_history_file()
    HISTORY_FILE.write_text("[]\n", encoding="utf-8")

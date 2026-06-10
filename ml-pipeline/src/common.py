from pathlib import Path

import yaml

PIPELINE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PIPELINE_DIR / "data"
MODELS_DIR = PIPELINE_DIR / "models"
REPORTS_DIR = PIPELINE_DIR / "reports"

FEATURES = [
    "progress_pct",
    "days_since_last_login",
    "quiz_avg",
    "lessons_per_week",
    "chat_messages",
]
TARGET = "dropped_out"


def load_params():
    with open(PIPELINE_DIR / "params.yaml") as f:
        return yaml.safe_load(f)

"""Resolve bot data independently of the machine and launch directory."""

import os
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
_data_directory = Path(os.environ.get('EXERCISE_BOT_DATA_DIR') or 'data').expanduser()
DATA_DIR = (PROJECT_ROOT / _data_directory).resolve()
EXERCISE_LOG_DIR = DATA_DIR / 'exercise_logs'
SCHEDULE_DIR = EXERCISE_LOG_DIR / 'schedule'


def find_schedule_image(preferred_path):
    """Find the optional schedule image, allowing common image extensions."""
    preferred = Path(preferred_path)
    candidates = dict.fromkeys([
        preferred,
        *(preferred.with_suffix(suffix) for suffix in ('.jpg', '.jpeg', '.png', '.webp', '.gif')),
    ])
    return next((path for path in candidates if path.is_file()), None)

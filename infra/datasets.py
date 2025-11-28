# infra/datasets.py

import csv
from pathlib import Path
from typing import List, Dict

GOLDEN_SET_PATH = Path("data/golden_set.csv")


def load_golden_set() -> List[Dict[str, str]]:
    """Load the golden evaluation dataset from CSV."""
    rows: List[Dict[str, str]] = []
    if not GOLDEN_SET_PATH.exists():
        raise FileNotFoundError(f"Golden set not found at {GOLDEN_SET_PATH}")

    with GOLDEN_SET_PATH.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

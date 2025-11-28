from __future__ import annotations

"""
Helper utilities to apply a PlannerEngine changeset:

- Deep-merge a config_patch into a base ADK config JSON
- Write a new config file (e.g., travel_planner_config_v2.json)
- Append new_testcases to the golden CSV (e.g., travel_golden_v1.csv)

Intended to be used after running:

  Supervisor > improve [version]

where PlannerEngine.propose_changeset(...) returns something like:

{
  "base_config_path": "v2_adk/travel_planner/configs/travel_planner_config_v1.json",
  "new_config_path": "v2_adk/travel_planner/configs/travel_planner_config_v2.json",
  "golden_csv_path": "v2_adk/travel_planner/tests/golden/travel_golden_v1.csv",
  "config_patch": { ... nested dict ... },
  "new_testcases": [
      {
        "id": "4",
        "input_json": "{\"destination\": \"Rome\", ...}",
        "judge_question": "...",
        "expected_behavior": "..."
      },
      ...
  ]
}

If your actual changeset schema is slightly different, you can adapt the
keys below (config_patch_key, new_testcases_key, etc.).
"""

import csv
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


# --------------------------------------------------------------------
# Data model
# --------------------------------------------------------------------
@dataclass
class Changeset:
    base_config_path: Path
    new_config_path: Path
    golden_csv_path: Path
    config_patch: Dict[str, Any]
    new_testcases: List[Dict[str, Any]]

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "Changeset":
        """
        Create a Changeset from a dictionary, with sensible defaults.

        Required keys (recommended PlannerEngine output):
          - base_config_path (str)
          - new_config_path (str)
          - golden_csv_path (str)
          - config_patch (dict)
          - new_testcases (list[dict])
        """
        try:
            base_config = Path(data["base_config_path"])
            new_config = Path(data["new_config_path"])
            golden = Path(data["golden_csv_path"])
        except KeyError as e:
            raise ValueError(
                f"Changeset dict missing required path key: {e}"
            ) from e

        config_patch = data.get("config_patch") or {}
        if not isinstance(config_patch, dict):
            raise ValueError("changeset['config_patch'] must be a dict")

        new_testcases = data.get("new_testcases") or []
        if not isinstance(new_testcases, list):
            raise ValueError("changeset['new_testcases'] must be a list")

        return Changeset(
            base_config_path=base_config,
            new_config_path=new_config,
            golden_csv_path=golden,
            config_patch=config_patch,
            new_testcases=new_testcases,
        )


# --------------------------------------------------------------------
# Deep merge for JSON config patches
# --------------------------------------------------------------------
def _deep_merge_dict(base: Dict[str, Any], patch: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively merge `patch` into `base`.

    - For dict values: recurse.
    - For non-dict values: patch overwrites base.
    - Mutates and returns `base` for convenience.
    """
    for key, patch_val in patch.items():
        if (
            key in base
            and isinstance(base[key], dict)
            and isinstance(patch_val, dict)
        ):
            _deep_merge_dict(base[key], patch_val)
        else:
            base[key] = patch_val
    return base


def apply_config_patch(
    base_config_path: Path,
    new_config_path: Path,
    config_patch: Dict[str, Any],
) -> None:
    """
    Load base_config_path (JSON), apply config_patch, and write new_config_path.
    """
    if not base_config_path.exists():
        raise FileNotFoundError(f"Base config not found: {base_config_path}")

    with base_config_path.open("r", encoding="utf-8") as f:
        base_cfg = json.load(f)

    if not isinstance(base_cfg, dict):
        raise ValueError(f"Base config JSON must be an object: {base_config_path}")

    merged_cfg = _deep_merge_dict(base_cfg, config_patch)

    new_config_path.parent.mkdir(parents=True, exist_ok=True)
    with new_config_path.open("w", encoding="utf-8") as f:
        json.dump(merged_cfg, f, indent=2, ensure_ascii=False)

    print(f"[apply_changeset] Wrote new config: {new_config_path}")


# --------------------------------------------------------------------
# Golden CSV utilities
# --------------------------------------------------------------------
def _read_existing_testcases(golden_csv_path: Path) -> List[Dict[str, Any]]:
    """
    Read existing golden CSV rows into a list of dicts.

    Expected columns:
      - id
      - input_json
      - judge_question
      - expected_behavior

    Returns [] if file does not exist.
    """
    if not golden_csv_path.exists():
        print(f"[apply_changeset] Golden CSV not found, will create new: {golden_csv_path}")
        return []

    rows: List[Dict[str, Any]] = []
    with golden_csv_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Skip empty rows
            if not row.get("id"):
                continue
            rows.append(row)
    return rows


def _next_id(existing_rows: List[Dict[str, Any]]) -> int:
    """
    Compute the next integer ID based on existing rows.

    If IDs are not numeric or file is empty, start from 1.
    """
    max_id = 0
    for r in existing_rows:
        rid = r.get("id")
        if rid is None:
            continue
        try:
            num = int(str(rid))
            if num > max_id:
                max_id = num
        except ValueError:
            # Ignore non-numeric IDs
            continue
    return max_id + 1


def append_new_testcases(
    golden_csv_path: Path,
    new_testcases: List[Dict[str, Any]],
    required_fields: Optional[List[str]] = None,
) -> None:
    """
    Append new testcases to golden CSV.

    new_testcases should contain dicts with at least:
      - input_json
      - judge_question
      - expected_behavior

    If `id` is missing, it will be auto-assigned (incremental integer).
    """
    if not new_testcases:
        print("[apply_changeset] No new_testcases provided; skipping CSV update.")
        return

    existing_rows = _read_existing_testcases(golden_csv_path)
    next_id_val = _next_id(existing_rows)

    # Determine fieldnames
    if existing_rows:
        fieldnames = list(existing_rows[0].keys())
    else:
        # Fresh file
        fieldnames = ["id", "input_json", "judge_question", "expected_behavior"]

    required_fields = required_fields or ["input_json", "judge_question", "expected_behavior"]

    # Normalize new testcases
    rows_to_append: List[Dict[str, Any]] = []
    for tc in new_testcases:
        row: Dict[str, Any] = {}

        # Ensure id
        tc_id = tc.get("id")
        if tc_id is None:
            tc_id = str(next_id_val)
            next_id_val += 1

        row["id"] = str(tc_id)

        # Copy known/required fields
        for f in required_fields:
            if f not in tc:
                raise ValueError(f"New testcase missing required field '{f}': {tc}")
            row[f] = tc[f]

        # Copy any extra fields but keep ordering stable
        for k, v in tc.items():
            if k in row:
                continue
            # Only keep keys that are part of fieldnames, or extend fieldnames dynamically
            if k not in fieldnames:
                fieldnames.append(k)
            row[k] = v

        rows_to_append.append(row)

    # If file existed, we append; else we create
    file_exists = golden_csv_path.exists()
    golden_csv_path.parent.mkdir(parents=True, exist_ok=True)

    with golden_csv_path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        if not file_exists:
            writer.writeheader()
        for row in rows_to_append:
            writer.writerow(row)

    print(f"[apply_changeset] Appended {len(rows_to_append)} new testcases to {golden_csv_path}")


# --------------------------------------------------------------------
# Orchestrator: apply full changeset
# --------------------------------------------------------------------
def apply_changeset(changeset: Changeset) -> None:
    """
    Apply both config_patch and new_testcases from a Changeset.

    Steps:
      1. Patch base_config_path → new_config_path
      2. Append new_testcases to golden_csv_path
    """
    print("[apply_changeset] Applying config patch...")
    apply_config_patch(
        base_config_path=changeset.base_config_path,
        new_config_path=changeset.new_config_path,
        config_patch=changeset.config_patch,
    )

    print("[apply_changeset] Appending new testcases...")
    append_new_testcases(
        golden_csv_path=changeset.golden_csv_path,
        new_testcases=changeset.new_testcases,
    )

    print("[apply_changeset] Done.")


# --------------------------------------------------------------------
# CLI entrypoint (optional)
# --------------------------------------------------------------------
def _parse_args():
    import argparse

    parser = argparse.ArgumentParser(
        description="Apply a PlannerEngine changeset to config + golden CSV."
    )
    parser.add_argument(
        "--changeset",
        type=str,
        required=True,
        help="Path to a JSON file containing the changeset dict.",
    )
    return parser.parse_args()


def main_cli() -> None:
    args = _parse_args()
    changeset_path = Path(args.changeset)

    if not changeset_path.exists():
        raise FileNotFoundError(f"Changeset file not found: {changeset_path}")

    with changeset_path.open("r", encoding="utf-8") as f:
        data = json.load(f)

    cs = Changeset.from_dict(data)
    apply_changeset(cs)


if __name__ == "__main__":
    main_cli()

#!/usr/bin/env python3
"""Turn the newest dated roster into a small, public-safe JSON snapshot."""

import argparse
import csv
import json
import math
import re
import sys
import unicodedata
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILENAME = re.compile(r"Participants_(\d{8})(?:-(\d{6}))?\.csv\Z")
POINTS = re.compile(r"-\s*(\d+(?:\.\d+)?)\s*pts?\s*$", re.IGNORECASE)
TASK_ID = re.compile(r"C#\s*(\d+)\b")
BONUS_COLUMN = re.compile(r"^Bonus\s*-", re.IGNORECASE)
COMPLETION_TIME = re.compile(r"[0-9]{8}-[0-9]{6}\Z")
REQUIRED_COLUMNS = {"Name", "Total Score", "Percentage"}


class DataError(ValueError):
    """An actionable input error, suitable for the build log."""


def filename_timestamp(path):
    match = FILENAME.fullmatch(Path(path).name)
    if not match:
        return None
    try:
        return datetime.strptime(match[1] + (match[2] or "000000"), "%Y%m%d%H%M%S")
    except ValueError:
        return None


def select_latest(root):
    """Inspect repository-root CSVs; never consult modification times."""
    candidates = []
    for path in Path(root).glob("Participants_*.csv"):
        stamp = filename_timestamp(path)
        if path.is_file() and stamp is not None:
            candidates.append((stamp, path.name, path))
    if not candidates:
        raise DataError(
            "No valid Participants_*.csv found in the repository root. Use "
            "Participants_YYYYMMDD.csv or Participants_YYYYMMDD-HHMMSS.csv "
            "with a valid calendar date and time."
        )
    return max(candidates)[2]


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError, OverflowError):
        return None


def compact(value):
    return int(value) if value.is_integer() else value


def name_key(name):
    normalized = unicodedata.normalize("NFKD", name.casefold())
    return "".join(c for c in normalized if not unicodedata.combining(c))


def parse_completion_time(value):
    """Return a valid CSV completion timestamp, or None for missing/bad input."""
    if not isinstance(value, str) or not COMPLETION_TIME.fullmatch(value.strip()):
        return None
    try:
        return datetime.strptime(value.strip(), "%Y%m%d-%H%M%S")
    except ValueError:
        return None


def ranking_key(participant):
    finished = all(participant["tasks"])
    # Unknown finish times follow known times, but still precede non-finishers.
    # Scores do not break ties between finishers; times never rank non-finishers.
    return (
        not finished,
        (participant["_completionTime"] or datetime.max) if finished else datetime.max,
        0 if finished else -participant["score"],
        -participant["completedTasks"],
        name_key(participant["name"]),
        participant["name"],
    )


def load_config(root):
    path = Path(root) / "leaderboard.config.json"
    if not path.exists():
        return {}
    try:
        config = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(config, dict):
            raise ValueError("configuration must be an object")
        if "max_score" in config:
            maximum = number(config["max_score"])
            if isinstance(config["max_score"], bool) or maximum is None or not 0 < maximum <= 9007199254740991:
                raise ValueError("max_score must be a positive, finite number within JavaScript's safe range")
            config["max_score"] = maximum
        fallback = config.get("fallback_task_points", {})
        if not isinstance(fallback, dict):
            raise ValueError("fallback_task_points must be an object")
        for key, value in fallback.items():
            parsed = number(value)
            if not key.isdigit() or isinstance(value, bool) or parsed is None or parsed <= 0:
                raise ValueError("task IDs must be numeric strings and points must be positive")
        return config
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise DataError(f"Invalid leaderboard.config.json: {exc}") from exc


def prepare(root=ROOT):
    root = Path(root)
    source = select_latest(root)
    config = load_config(root)
    fallback = config.get("fallback_task_points", {})
    warnings = Counter()
    participants = []
    try:
        with source.open(encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle, strict=True)
            headers = reader.fieldnames or []
            if len(headers) != len(set(headers)):
                raise DataError(f"{source.name}: duplicate column headers are not allowed.")
            missing = REQUIRED_COLUMNS - set(headers)
            if missing:
                raise DataError(f"{source.name}: missing required columns: {', '.join(sorted(missing))}.")
            task_columns = [h for h in headers if h.startswith("C#")]
            bonus_columns = [h for h in headers if BONUS_COLUMN.match(h.strip())]
            if not task_columns:
                raise DataError(f"{source.name}: no task columns beginning with C# were found.")
            # This is a display/validation cap, never a participant score calculation.
            # Only required headers supply the fallback cap; bonus weights never raise it.
            max_score = config.get("max_score")
            if max_score is None:
                weights = []
                for header in task_columns:
                    match = POINTS.search(header)
                    weight = number(match[1]) if match else None
                    if weight is None or weight <= 0:
                        task_id = TASK_ID.match(header)
                        weight = number(fallback.get(task_id[1])) if task_id else None
                        if weight is None or weight <= 0:
                            raise DataError(
                                f"{source.name}: cannot determine points for {header!r}. "
                                "Set max_score in leaderboard.config.json, end the header "
                                "with '- N pts', or configure fallback_task_points."
                            )
                        warnings["Task weights taken from the validated fallback configuration"] += 1
                    weights.append(weight)
                max_score = sum(weights)
            if not math.isfinite(max_score) or not 0 < max_score <= 9007199254740991:
                raise DataError(f"{source.name}: the maximum score must be positive and within JavaScript's safe numeric range.")

            for row_number, row in enumerate(reader, start=2):
                name = row.get("Name")
                if not isinstance(name, str) or not name.strip():
                    warnings["Rows without a name skipped"] += 1
                    continue
                if None in row:
                    warnings["Rows with extra cells skipped"] += 1
                    continue
                tasks = []
                for column in task_columns:
                    value = number(row.get(column))
                    tasks.append(value == 1)
                    if value not in (0, 1):
                        warnings["Missing or invalid task values treated as incomplete"] += 1
                bonus_tasks = []
                for column in bonus_columns:
                    value = number(row.get(column))
                    bonus_tasks.append(value == 1)
                    if value not in (0, 1):
                        warnings["Missing or invalid bonus values treated as incomplete"] += 1
                # The CSV is authoritative. Do not infer or add points from task flags.
                score = number(row.get("Total Score"))
                fraction = number(row.get("Percentage"))
                if score is None or not 0 <= score <= max_score:
                    warnings["Rows with invalid Total Score skipped; correct the source CSV"] += 1
                    continue
                if fraction is None or not 0 <= fraction <= 1:
                    warnings["Rows with invalid Percentage skipped; correct the source CSV"] += 1
                    continue
                # The private completion timestamp is removed after ranking.
                participants.append({
                    "id": f"participant-{row_number}",
                    "name": name,
                    "score": compact(score),
                    "progress": round(fraction * 100, 6),
                    "completedTasks": sum(tasks),
                    "tasks": tasks,
                    "bonusTasks": bonus_tasks,
                    "completedBonusTasks": sum(bonus_tasks),
                    "_completionTime": parse_completion_time(row.get("Completion Time (YYYYMMDD-HHMMSS)")) if all(tasks) else None,
                })
    except (OSError, UnicodeError, csv.Error) as exc:
        raise DataError(f"Cannot read {source.name}: {exc}") from exc
    if not participants:
        raise DataError(f"{source.name}: no valid named participants were found. Each row needs a finite Total Score from 0 to {compact(max_score)} and Percentage from 0 to 1.")
    participants.sort(key=ranking_key)
    score_counts = Counter(participant["score"] for participant in participants)
    score_ranks = {}
    for rank, participant in enumerate(participants, start=1):
        del participant["_completionTime"]
        # Keep the sorted position for navigation. Equal source scores share
        # the first position at which that score appears, without reordering.
        participant["rank"] = rank
        participant["displayRank"] = score_ranks.setdefault(participant["score"], rank)
        participant["tieCount"] = score_counts[participant["score"]]
    return {
        "schemaVersion": 3,
        "metadata": {
            "sourceFile": source.name,
            "generatedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "participantCount": len(participants),
            "taskCount": len(task_columns),
            "bonusTaskCount": len(bonus_columns),
            "maxScore": compact(max_score),
        },
        "participants": participants,
    }, warnings


def write_data(root=ROOT):
    """Replace output atomically; never leave an old roster behind after failure."""
    destination = Path(root) / "site/data/leaderboard.json"
    try:
        data, warnings = prepare(root)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(".json.tmp")
        temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        temporary.replace(destination)
        return data, warnings
    except (DataError, OSError):
        destination.unlink(missing_ok=True)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT, help="Repository root (defaults to this project)")
    args = parser.parse_args()
    try:
        data, warnings = write_data(args.root)
    except (DataError, OSError) as exc:
        print(f"Data preparation failed: {exc}", file=sys.stderr)
        return 1
    meta = data["metadata"]
    bonus_label = "bonus activity" if meta["bonusTaskCount"] == 1 else "bonus activities"
    print(f"Prepared {meta['participantCount']} participants, {meta['taskCount']} required tasks, "
          f"{meta['bonusTaskCount']} {bonus_label}, "
          f"{meta['maxScore']} points from {meta['sourceFile']}.")
    for warning, count in warnings.items():
        print(f"Warning: {warning} ({count}).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

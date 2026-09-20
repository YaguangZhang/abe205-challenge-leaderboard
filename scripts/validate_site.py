#!/usr/bin/env python3
"""Check the generated artifact and relative asset paths using only stdlib."""

import json
import sys
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag in {"script", "img", "link"}:
            url = attrs.get("src") or attrs.get("href")
            if url:
                self.assets.append(url)


def validate(root=ROOT):
    site = Path(root) / "site"
    for relative in ["index.html", "styles.css", "app.js", "assets/favicon.svg", "data/leaderboard.json"]:
        path = site / relative
        if not path.is_file() or not path.stat().st_size:
            raise ValueError(f"Missing or empty asset: {relative}")
    parser = AssetParser()
    parser.feed((site / "index.html").read_text(encoding="utf-8"))
    for url in parser.assets:
        parsed = urlsplit(url)
        if parsed.scheme or parsed.netloc or parsed.path.startswith("/"):
            raise ValueError(f"Expected a project-relative, self-contained asset: {url}")
        if not (site / parsed.path).is_file():
            raise ValueError(f"Asset does not exist: {url}")
    data = json.loads((site / "data/leaderboard.json").read_text(encoding="utf-8"))
    meta = data["metadata"]
    if data["schemaVersion"] != 3 or meta["participantCount"] != len(data["participants"]) or not data["participants"]:
        raise ValueError("Generated roster is empty or inconsistent")
    score_counts = Counter(participant["score"] for participant in data["participants"])
    score_ranks = {}
    for position, participant in enumerate(data["participants"], start=1):
        display_rank = score_ranks.setdefault(participant["score"], position)
        if participant["rank"] != position or participant["displayRank"] != display_rank or participant["tieCount"] != score_counts[participant["score"]]:
            raise ValueError("Generated ranks or score ties are inconsistent")
        if len(participant["tasks"]) != meta["taskCount"] or sum(participant["tasks"]) != participant["completedTasks"]:
            raise ValueError("Generated task counts are inconsistent")
        if len(participant["bonusTasks"]) != meta["bonusTaskCount"] or sum(participant["bonusTasks"]) != participant["completedBonusTasks"]:
            raise ValueError("Generated bonus counts are inconsistent")
    public_files = {"index.html", "styles.css", "app.js", "assets/favicon.svg", "data/leaderboard.json", "data/.gitkeep", ".nojekyll"}
    for path in site.rglob("*"):
        if path.is_symlink() or (path.is_file() and path.relative_to(site).as_posix() not in public_files):
            raise ValueError(f"Unexpected public artifact: {path.relative_to(site)}")


def main():
    try:
        validate()
    except (ValueError, OSError, KeyError, TypeError) as exc:
        print(f"Site validation failed: {exc}", file=sys.stderr)
        return 1
    print("Static site validated: generated roster, relative assets, and public files.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

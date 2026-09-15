import argparse
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from app import (
    MAX_STORY_CHARACTERS,
    create_session,
    fetch_stories,
    month_bounds,
    normalize_username,
    parse_qualifying_commenters,
    parse_story_character_count,
)


WEEKDAY_ALIASES = {
    "pn": 0,
    "wt": 1,
    "sr": 2,
    "czw": 3,
    "pt": 4,
    "sob": 5,
    "nd": 6,
}
WEEKDAY_NAMES = (
    "poniedziałek",
    "wtorek",
    "środa",
    "czwartek",
    "piątek",
    "sobota",
    "niedziela",
)


def load_duty_schedule(path: Path) -> dict[str, set[int]]:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except OSError as error:
        raise RuntimeError(f"Nie mozna odczytac grafiku dyzurow: {path}") from error
    except yaml.YAMLError as error:
        raise RuntimeError(f"Niepoprawny YAML grafiku dyzurow: {path}") from error

    entries = data.get("dyzurni") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not entries:
        raise RuntimeError("Grafik musi zawierac niepusta liste 'dyzurni'.")

    schedule: dict[str, set[int]] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise RuntimeError("Kazdy dyzurny musi zawierac pola 'name' i 'days'.")
        username = entry.get("name")
        raw_days = entry.get("days")
        if not isinstance(username, str) or not username.strip() or not isinstance(raw_days, list):
            raise RuntimeError("Kazdy dyzurny musi zawierac niepuste 'name' i liste 'days'.")
        try:
            weekdays = {WEEKDAY_ALIASES[day.strip().casefold()] for day in raw_days}
        except (AttributeError, KeyError) as error:
            raise RuntimeError("Dni dyzuru podaj jako np. pn, wt, sr.") from error
        if not weekdays:
            raise RuntimeError("Kazdy dyzurny musi miec co najmniej jeden poprawny dzien.")
        schedule.setdefault(username.strip(), set()).update(weekdays)
    return schedule


def build_report(month: str, duty_schedule: dict[str, set[int]]) -> dict[str, object]:
    start, end = month_bounds(month)
    progress = lambda _text, _current, _total: None
    session = create_session()
    users = {
        normalize_username(username): {
            "username": username,
            "weekdays": weekdays,
            "eligible": 0,
            "commented": 0,
            "own_stories": 0,
        }
        for username, weekdays in duty_schedule.items()
    }

    try:
        stories = fetch_stories(session, month, progress)
        for story in stories:
            relevant = [
                user
                for user in users.values()
                if story.published_at.weekday() in user["weekdays"]
            ]
            if not relevant:
                continue

            response = session.get(story.url, timeout=30)
            response.raise_for_status()
            if (character_count := parse_story_character_count(response.text)) is None:
                continue
            if character_count >= MAX_STORY_CHARACTERS:
                continue

            commenters = parse_qualifying_commenters(response.text, 10)
            author = normalize_username(story.author)
            for user in relevant:
                if normalize_username(str(user["username"])) == author:
                    user["own_stories"] += 1
                    continue
                user["eligible"] += 1
                if normalize_username(str(user["username"])) in commenters:
                    user["commented"] += 1
            time.sleep(0.75)
    finally:
        session.close()

    results = []
    for user in users.values():
        eligible = int(user["eligible"])
        commented = int(user["commented"])
        percentage = round(commented / eligible * 100, 1) if eligible else 0.0
        results.append(
            {
                "username": user["username"],
                "weekdays": [WEEKDAY_NAMES[day] for day in sorted(user["weekdays"])],
                "eligible": eligible,
                "commented": commented,
                "ownStories": user["own_stories"],
                "percentage": percentage,
                "passed": eligible == 0 or commented / eligible >= 0.5,
            }
        )

    now = datetime.now(ZoneInfo("Europe/Warsaw"))
    return {
        "month": month,
        "period": f"{start:%d.%m.%Y} - {(end - timedelta(days=1)):%d.%m.%Y}",
        "updatedAt": now.isoformat(timespec="seconds"),
        "results": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--month", default=datetime.now(ZoneInfo("Europe/Warsaw")).strftime("%Y-%m")
    )
    parser.add_argument("--output", default="docs/report.json")
    parser.add_argument(
        "--schedule",
        default=os.getenv("DUTY_SCHEDULE_FILE", str(Path.home() / "dyzurni.yaml")),
    )
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(
            build_report(args.month, load_duty_schedule(Path(args.schedule))),
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

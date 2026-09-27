import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from app import create_session, fetch_contest_stories, normalize_username, parse_comment_counts


CONTEST_ID = 220
CONTEST_NAME = "Magia, miecz i przygoda"
MIN_WORDS = 10


def parse_since(value: str) -> datetime:
    try:
        return datetime.strptime(value, "%Y-%m-%d")
    except ValueError as error:
        raise ValueError("Data początkowa musi mieć format RRRR-MM-DD.") from error


def build_contest_report(since: datetime) -> dict[str, object]:
    session = create_session()
    users: dict[str, dict[str, object]] = {}
    stories_data: list[dict[str, object]] = []

    def user(name: str) -> dict[str, object]:
        key = normalize_username(name)
        return users.setdefault(
            key,
            {
                "username": name,
                "submittedStories": 0,
                "storiesCommented": set(),
                "comments": 0,
                "substantiveComments": 0,
                "ownStoryComments": 0,
            },
        )

    try:
        stories = fetch_contest_stories(session, CONTEST_ID, since, lambda *_: None)
        for story in stories:
            author = user(story.author)
            author["submittedStories"] = int(author["submittedStories"]) + 1
            response = session.get(story.url, timeout=30)
            response.raise_for_status()
            commenters = parse_comment_counts(response.text, MIN_WORDS)
            story_commenters = []
            for key, (name, comments, substantive) in commenters.items():
                commenter = user(name)
                commenter["comments"] = int(commenter["comments"]) + comments
                commenter["substantiveComments"] = int(commenter["substantiveComments"]) + substantive
                commenter["storiesCommented"].add(story.url)
                if key == normalize_username(story.author):
                    commenter["ownStoryComments"] = int(commenter["ownStoryComments"]) + comments
                story_commenters.append(
                    {
                        "username": name,
                        "comments": comments,
                        "substantiveComments": substantive,
                    }
                )
            stories_data.append(
                {
                    "title": story.title,
                    "url": story.url,
                    "author": story.author,
                    "publishedAt": story.published_at.isoformat(timespec="minutes"),
                    "comments": sum(item["comments"] for item in story_commenters),
                    "substantiveComments": sum(
                        item["substantiveComments"] for item in story_commenters
                    ),
                    "commenters": sorted(
                        story_commenters,
                        key=lambda item: (-int(item["comments"]), str(item["username"]).casefold()),
                    ),
                }
            )
            time.sleep(0.75)
    finally:
        session.close()

    user_data = []
    for entry in users.values():
        user_data.append(
            {
                "username": entry["username"],
                "submittedStories": entry["submittedStories"],
                "storiesCommented": len(entry["storiesCommented"]),
                "comments": entry["comments"],
                "substantiveComments": entry["substantiveComments"],
                "ownStoryComments": entry["ownStoryComments"],
            }
        )
    user_data.sort(
        key=lambda item: (-int(item["comments"]), -int(item["submittedStories"]), str(item["username"]).casefold())
    )
    stories_data.sort(key=lambda item: str(item["publishedAt"]), reverse=True)
    now = datetime.now(ZoneInfo("Europe/Warsaw"))
    return {
        "contest": CONTEST_NAME,
        "contestId": CONTEST_ID,
        "since": since.date().isoformat(),
        "updatedAt": now.isoformat(timespec="seconds"),
        "summary": {
            "stories": len(stories_data),
            "authors": len({normalize_username(str(story["author"])) for story in stories_data}),
            "comments": sum(int(story["comments"]) for story in stories_data),
            "substantiveComments": sum(int(story["substantiveComments"]) for story in stories_data),
        },
        "users": user_data,
        "stories": stories_data,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--since", default="2026-09-27")
    parser.add_argument("--output", default="docs/nf-konkurs-magia-i-miecz/report.json")
    args = parser.parse_args()
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(build_contest_report(parse_since(args.since)), ensure_ascii=False, indent=2)
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

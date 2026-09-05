import calendar
import ctypes
import re
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Callable
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk


BASE_URL = "https://www.fantastyka.pl"
LIST_URL = f"{BASE_URL}/opowiadania/wszystkie/w/w/w/0/d"
DATE_RE = re.compile(r"(\d{2}\.\d{2}\.\d{2,4}),\s*g\.\s*(\d{2}:\d{2})")
WORD_RE = re.compile(r"\b\w+(?:['-]\w+)*\b", re.UNICODE)
STORY_KIND_RE = re.compile(
    r"(?:^|\|)\s*(opowiadanie|szort|drabble|wiersz|fragment)\s*(?:,|\|)",
    re.IGNORECASE,
)
ALLOWED_STORY_KINDS = {"opowiadanie", "szort"}
STORY_LENGTH_RE = re.compile(r"znaki:\s*(\d+)", re.IGNORECASE)
MAX_STORY_CHARACTERS = 80_000
WEEKDAY_NAMES = (
    "poniedzialek",
    "wtorek",
    "sroda",
    "czwartek",
    "piatek",
    "sobota",
    "niedziela",
)
WEEKDAY_LABELS = (
    "poniedziałek",
    "wtorek",
    "środa",
    "czwartek",
    "piątek",
    "sobota",
    "niedziela",
)
Progress = Callable[[str, int, int], None]


@dataclass(frozen=True)
class Story:
    title: str
    url: str
    author: str
    published_at: datetime


@dataclass(frozen=True)
class Report:
    username: str
    month: str
    weekdays: tuple[int, ...]
    all_stories: int
    eligible: int
    commented: int
    own_stories: int
    day_results: tuple[tuple[date, int, int], ...]
    min_words: int

    @property
    def percentage(self) -> float:
        return self.commented / self.eligible * 100 if self.eligible else 0.0

    @property
    def passed(self) -> bool:
        return self.eligible > 0 and self.commented / self.eligible >= 0.5


def normalize_username(value: str) -> str:
    return " ".join(value.split()).casefold().rstrip(":")


def parse_datetime(text: str) -> datetime | None:
    match = DATE_RE.search(text)
    if not match:
        return None
    date_part, time_part = match.groups()
    year_format = "%Y" if len(date_part.rsplit(".", 1)[-1]) == 4 else "%y"
    return datetime.strptime(
        f"{date_part} {time_part}", f"%d.%m.{year_format} %H:%M"
    )


def month_bounds(value: str) -> tuple[datetime, datetime]:
    try:
        parsed = datetime.strptime(value, "%Y-%m")
    except ValueError as error:
        raise ValueError("Miesiąc musi mieć format RRRR-MM, np. 2026-08.") from error
    last_day = calendar.monthrange(parsed.year, parsed.month)[1]
    start = datetime(parsed.year, parsed.month, 1)
    return start, datetime(parsed.year, parsed.month, last_day) + timedelta(days=1)


def parse_story_list(html: str) -> tuple[list[Story], str | None]:
    soup = BeautifulSoup(html, "html.parser")
    stories: list[Story] = []
    for row in soup.select("section.no-headline div.lista"):
        if any(
            marker.get_text(" ", strip=True).casefold() == "przyklejony"
            for marker in row.select("span.zielony")
        ):
            continue

        link = row.select_one('.teksty > a.tytul[href^="/opowiadania/pokaz/"]')
        metadata = row.select_one(".teksty > div")
        if link is None or metadata is None or not link.get("href"):
            continue
        kind_match = STORY_KIND_RE.search(metadata.get_text(" ", strip=True))
        if (
            kind_match is None
            or kind_match.group(1).casefold() not in ALLOWED_STORY_KINDS
            or metadata.select_one("a.konkurs") is not None
        ):
            continue
        published_at = parse_datetime(metadata.get_text(" ", strip=True))
        if published_at is None:
            continue
        author_link = row.select_one(".autor > a")
        author = author_link.get_text(" ", strip=True) if author_link else "Anonim"
        stories.append(
            Story(
                title=link.get_text(" ", strip=True),
                url=urljoin(BASE_URL, str(link["href"])),
                author=author.rstrip(":"),
                published_at=published_at,
            )
        )

    pagination = soup.select_one("section.paginacja")
    next_link = (
        pagination.select_one('a[title="następna strona"]') if pagination else None
    )
    next_url = (
        urljoin(BASE_URL, str(next_link["href"]))
        if next_link is not None and next_link.get("href")
        else None
    )
    return stories, next_url


def has_qualifying_comment(html: str, username: str, min_words: int) -> bool:
    expected = normalize_username(username)
    return expected in parse_qualifying_commenters(html, min_words)


def parse_qualifying_commenters(html: str, min_words: int) -> set[str]:
    soup = BeautifulSoup(html, "html.parser")
    commenters: set[str] = set()
    for article in soup.select("section.kom > article"):
        link = article.select_one("p.naglowek-kom a.login")
        body = article.select_one("div.avek-tekst")
        if link is None or body is None:
            continue
        commenter = normalize_username(link.get_text(" ", strip=True))
        aside = body.select_one("aside")
        if aside is not None:
            aside.decompose()
        for signature in body.select("p.sygnaturka"):
            signature.decompose()
        content = " ".join(body.get_text(" ", strip=True).split())
        if len(WORD_RE.findall(content)) >= min_words:
            commenters.add(commenter)
    return commenters


def parse_story_character_count(html: str) -> int | None:
    soup = BeautifulSoup(html, "html.parser")
    details = soup.select_one("article.tekst p.data")
    if details is None:
        return None
    match = STORY_LENGTH_RE.search(details.get_text(" ", strip=True))
    return int(match.group(1)) if match else None


def create_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=3,
        backoff_factor=0.7,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=("GET",),
    )
    session.mount("https://", HTTPAdapter(max_retries=retries))
    session.headers["User-Agent"] = "NFDutyWindows/1.0 (+public activity report)"
    return session


def fetch_stories(
    session: requests.Session, month: str, progress: Progress
) -> list[Story]:
    start, end = month_bounds(month)
    selected: list[Story] = []
    url: str | None = LIST_URL
    page = 0
    while url:
        page += 1
        progress(f"Pobieranie listy tekstów, strona {page}...", page, 0)
        response = session.get(url, timeout=30)
        response.raise_for_status()
        stories, next_url = parse_story_list(response.text)
        selected.extend(story for story in stories if start <= story.published_at < end)
        if stories and min(story.published_at for story in stories) < start:
            break
        url = next_url
        if url:
            time.sleep(0.75)
    return selected


def analyze(
    username: str,
    month: str,
    weekdays: tuple[int, ...],
    min_words: int,
    progress: Progress,
) -> Report:
    if not username.strip():
        raise ValueError("Podaj dokładny nick użytkownika na Fantastyka.pl.")
    if not weekdays:
        raise ValueError("Zaznacz co najmniej jeden dzień dyżuru.")
    if min_words < 1:
        raise ValueError("Minimalna liczba słów musi być większa od zera.")

    session = create_session()
    try:
        stories = fetch_stories(session, month, progress)
        assigned = [story for story in stories if story.published_at.weekday() in weekdays]
        expected = normalize_username(username)
        own_stories = 0
        eligible = 0
        commented = 0
        qualified_pool = 0
        by_day: dict[date, list[int]] = {}

        for index, story in enumerate(assigned, start=1):
            progress(
                f"Sprawdzanie {index}/{len(assigned)}: {story.title}",
                index,
                len(assigned),
            )
            response = session.get(story.url, timeout=30)
            response.raise_for_status()
            character_count = parse_story_character_count(response.text)
            if character_count is None or character_count >= MAX_STORY_CHARACTERS:
                time.sleep(0.75)
                continue
            qualified_pool += 1
            if normalize_username(story.author) == expected:
                own_stories += 1
                time.sleep(0.75)
                continue

            eligible += 1
            day_result = by_day.setdefault(story.published_at.date(), [0, 0])
            day_result[0] += 1
            if has_qualifying_comment(response.text, username, min_words):
                commented += 1
                day_result[1] += 1
            time.sleep(0.75)

        day_results = tuple(
            (day, values[0], values[1]) for day, values in sorted(by_day.items())
        )
        return Report(
            username=username.strip(),
            month=month,
            weekdays=weekdays,
            all_stories=qualified_pool,
            eligible=eligible,
            commented=commented,
            own_stories=own_stories,
            day_results=day_results,
            min_words=min_words,
        )
    finally:
        session.close()


def format_report(report: Report) -> str:
    start, end = month_bounds(report.month)
    weekdays = ", ".join(WEEKDAY_NAMES[day] for day in report.weekdays)
    own_note = f", wlasne pominiete: {report.own_stories}" if report.own_stories else ""
    lines = [
        "**Raport dyzurnych NF**",
        f"Okres publikacji: **{start:%d.%m.%Y} - {(end - timedelta(days=1)):%d.%m.%Y}**",
        f"- **{report.username}** | dni dyzuru: **{weekdays}** | "
        f"wynik: **{report.commented}/{report.eligible} "
        f"({report.percentage:.1f}%)** | "
        f"zaliczenie: **{'TAK' if report.passed else 'NIE'}**{own_note}",
    ]
    lines.append(
        "Zaliczenie: co najmniej jeden widoczny komentarz zawierajacy minimum "
        f"**{report.min_words} slow** (bez naglowka i sygnatury)."
    )
    lines.append(
        "Zakres: opowiadania i szorty; bez drabbli, wierszy, fragmentow "
        "i tekstow konkursowych; dlugosc ponizej 80 000 znakow."
    )
    return "\n".join(lines)


class App:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("NF Dyżury")
        self.root.minsize(760, 620)
        self.root.geometry("820x680")
        self.username = tk.StringVar()
        self.month = tk.StringVar(value=datetime.now().strftime("%Y-%m"))
        self.min_words = tk.IntVar(value=10)
        self.weekdays = [tk.BooleanVar(value=True) for _ in WEEKDAY_NAMES]
        self.status = tk.StringVar(value="Gotowe")
        self._build_ui()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=18)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(7, weight=1)

        ttk.Label(frame, text="NF Dyżury", font=("Segoe UI", 20, "bold")).grid(
            row=0, column=0, columnspan=3, sticky="w", pady=(0, 4)
        )
        ttk.Label(
            frame,
            text="Raport publicznych komentarzy pod tekstami z Fantastyka.pl",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(0, 18))

        ttk.Label(frame, text="Dokładny nick NF:").grid(row=2, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.username).grid(
            row=2, column=1, columnspan=2, sticky="ew", padx=(12, 0), pady=4
        )

        ttk.Label(frame, text="Miesiąc (RRRR-MM):").grid(row=3, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.month, width=16).grid(
            row=3, column=1, sticky="w", padx=(12, 0), pady=4
        )
        words_frame = ttk.Frame(frame)
        words_frame.grid(row=3, column=2, sticky="e")
        ttk.Label(words_frame, text="Minimum słów:").pack(side="left")
        ttk.Spinbox(
            words_frame, from_=1, to=100, textvariable=self.min_words, width=5
        ).pack(side="left", padx=(8, 0))

        ttk.Label(frame, text="Dni dyżuru:").grid(
            row=4, column=0, sticky="nw", pady=(10, 0)
        )
        days_frame = ttk.Frame(frame)
        days_frame.grid(row=4, column=1, columnspan=2, sticky="w", padx=(12, 0), pady=(8, 8))
        for index, name in enumerate(WEEKDAY_LABELS):
            ttk.Checkbutton(
                days_frame, text=name.capitalize(), variable=self.weekdays[index]
            ).grid(row=index // 4, column=index % 4, sticky="w", padx=(0, 16), pady=2)

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(8, 8))
        self.run_button = ttk.Button(
            button_frame, text="Generuj raport", command=self.start
        )
        self.run_button.pack(side="left")
        ttk.Button(button_frame, text="Kopiuj wynik", command=self.copy_result).pack(
            side="left", padx=8
        )
        ttk.Button(button_frame, text="Wyczyść", command=self.clear_result).pack(
            side="left"
        )

        self.progress = ttk.Progressbar(frame, mode="determinate")
        self.progress.grid(row=6, column=0, columnspan=3, sticky="ew", pady=(0, 4))
        ttk.Label(frame, textvariable=self.status).grid(
            row=7, column=0, columnspan=3, sticky="nw", pady=(0, 8)
        )

        self.output = scrolledtext.ScrolledText(
            frame, wrap="word", font=("Consolas", 10), height=18
        )
        self.output.grid(row=8, column=0, columnspan=3, sticky="nsew")
        frame.rowconfigure(8, weight=1)

    def start(self) -> None:
        try:
            min_words = int(self.min_words.get())
        except (tk.TclError, ValueError):
            messagebox.showerror("Błąd", "Podaj poprawną minimalną liczbę słów.")
            return
        weekdays = tuple(
            index for index, selected in enumerate(self.weekdays) if selected.get()
        )
        self.run_button.config(state="disabled")
        self.progress.config(value=0, maximum=100)
        self.status.set("Rozpoczynam...")
        thread = threading.Thread(
            target=self._worker,
            args=(self.username.get(), self.month.get(), weekdays, min_words),
            daemon=True,
        )
        thread.start()

    def _worker(
        self, username: str, month: str, weekdays: tuple[int, ...], min_words: int
    ) -> None:
        try:
            report = analyze(username, month, weekdays, min_words, self._progress)
            result = format_report(report)
            self.root.after(0, self._finish, result, None)
        except Exception as error:
            self.root.after(0, self._finish, "", str(error))

    def _progress(self, text: str, current: int, total: int) -> None:
        self.root.after(0, self._set_progress, text, current, total)

    def _set_progress(self, text: str, current: int, total: int) -> None:
        self.status.set(text)
        if total:
            self.progress.config(mode="determinate", maximum=total, value=current)
        else:
            self.progress.config(mode="indeterminate")
            self.progress.start(12)

    def _finish(self, result: str, error: str | None) -> None:
        self.progress.stop()
        self.progress.config(mode="determinate")
        self.run_button.config(state="normal")
        if error:
            self.status.set("Wystąpił błąd")
            messagebox.showerror("Nie udało się wygenerować raportu", error)
            return
        self.output.delete("1.0", "end")
        self.output.insert("1.0", result)
        self.status.set("Raport gotowy")

    def copy_result(self) -> None:
        result = self.output.get("1.0", "end").strip()
        if not result:
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(result)
        self.status.set("Wynik skopiowany do schowka")

    def clear_result(self) -> None:
        self.output.delete("1.0", "end")
        self.status.set("Gotowe")


def main() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except (AttributeError, OSError):
        pass
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()

from datetime import date

from app import (
    Report,
    format_report,
    has_qualifying_comment,
    month_bounds,
    parse_qualifying_commenters,
    parse_story_character_count,
    parse_story_list,
)


def test_comment_requires_ten_words_and_ignores_signature() -> None:
    html = """
    <section class="kom">
      <article><div class="avek-tekst">
        <aside><p class="naglowek-kom"><a class="login">OldGuard</a></p></aside>
        <p>jeden dwa trzy cztery piec szesc siedem osiem dziewiec dziesiec</p>
        <p class="sygnaturka">podpis nie jest liczony</p>
      </div></article>
    </section>
    """
    assert has_qualifying_comment(html, "oldguard", 10)
    assert not has_qualifying_comment(html, "oldguard", 11)


def test_qualifying_commenters_returns_every_matching_author() -> None:
    html = """
    <section class="kom">
      <article><p class="naglowek-kom"><a class="login">OldGuard</a></p><div class="avek-tekst"><p>jeden dwa trzy cztery piec szesc siedem osiem dziewiec dziesiec</p></div></article>
      <article><p class="naglowek-kom"><a class="login">Ambush</a></p><div class="avek-tekst"><p>jeden dwa trzy cztery piec szesc siedem osiem dziewiec dziesiec</p></div></article>
    </section>
    """
    assert parse_qualifying_commenters(html, 10) == {"oldguard", "ambush"}


def test_story_list_skips_sticky() -> None:
    html = """
    <section class="paginacja"></section>
    <section class="no-headline"><article>
      <div class="lista"><div class="autor"><a>A:</a></div><div class="teksty">
        <a class="tytul" href="/opowiadania/pokaz/1">X</a>
        <div>opowiadanie, fantasy | 01.01.20, g. 10:00 <span class="zielony">przyklejony</span></div>
      </div></div>
      <div class="lista"><div class="autor"><a href="/profil/3">C:</a></div><div class="teksty">
        <a class="tytul" href="/opowiadania/pokaz/3">Konkurs</a>
        <div><a class="konkurs">Śmiercią im do twarzy?</a> | opowiadanie, science-fiction | 02.08.26, g. 12:00</div>
      </div></div>
      <div class="lista"><div class="autor"><a href="/profil/4">D:</a></div><div class="teksty">
        <a class="tytul" href="/opowiadania/pokaz/4">Wiersz</a>
        <div>wiersz, inne | 02.08.26, g. 12:00</div>
      </div></div>
      <div class="lista"><div class="autor"><a href="/profil/2">B:</a></div><div class="teksty">
        <a class="tytul" href="/opowiadania/pokaz/2">Y</a>
        <div>opowiadanie, fantasy | 02.08.26, g. 12:00</div>
      </div></div>
    </article></section>
    """
    stories, next_url = parse_story_list(html)
    assert len(stories) == 1
    assert stories[0].author == "B"
    assert next_url is None


def test_month_bounds() -> None:
    start, end = month_bounds("2026-02")
    assert start.strftime("%d.%m.%Y") == "01.02.2026"
    assert end.strftime("%d.%m.%Y") == "01.03.2026"


def test_story_character_count_boundary_data() -> None:
    html = """
    <article class="tekst">
      <p class="data">autor | 02.08.26, g. 12:00 | znaki: 80000</p>
    </article>
    """
    assert parse_story_character_count(html) == 80000


def test_report_uses_aggregate_half_threshold_and_bot_format() -> None:
    report = Report(
        username="barniusz",
        month="2026-08",
        weekdays=(3,),
        all_stories=4,
        eligible=4,
        commented=2,
        own_stories=1,
        day_results=((date(2026, 8, 6), 1, 0), (date(2026, 8, 13), 3, 2)),
        min_words=10,
    )

    output = format_report(report)

    assert report.passed is True
    assert "**Raport dyzurnych NF**" in output
    assert "**barniusz** | dni dyzuru: **czwartek**" in output
    assert "wynik: **2/4 (50.0%)** | zaliczenie: **TAK**" in output
    assert "wlasne pominiete: 1" in output
    assert "Dni z wynikiem" not in output
    assert "Ponizej 50%" not in output


def test_empty_duty_pool_is_passed() -> None:
    report = Report(
        username="OneTwo",
        month="2026-08",
        weekdays=(6,),
        all_stories=0,
        eligible=0,
        commented=0,
        own_stories=0,
        day_results=(),
        min_words=10,
    )

    assert report.passed is True
    assert "zaliczenie: **TAK**" in format_report(report)

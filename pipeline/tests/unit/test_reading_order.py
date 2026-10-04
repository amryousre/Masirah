"""Reading order on two-column layouts (T036, FR-004).

A two-column CV must be read one column after the other, never line by line across both: the
second is how a naive top-to-bottom sort reads it, and it splices a sidebar's phone number into a
job title. The rules below are what tells a column from the other things that sit side by side
on a CV page: a date at the end of a job's line, and a table of labels and values.
"""

from pathlib import Path

import pytest

from masirah_pipeline.adapters.native_text import read_native_text
from masirah_pipeline.adapters.reading_order import Line, reading_order

CORPUS = Path(__file__).resolve().parents[1] / "fixtures" / "cvs"
HEIGHT = 10.0


def line(x0: float, top: float, x1: float, text: str) -> Line:
    return Line(x0=x0, top=top, x1=x1, bottom=top + HEIGHT, text=text)


def read(lines: list[Line], *, right_to_left: bool = False) -> list[str]:
    """Each row as its pieces' text joined by " | ", in reading order."""
    rows = reading_order(lines, right_to_left=right_to_left)
    return [" | ".join(piece.text for piece in row) for row in rows]


def column(x0: float, x1: float, name: str, tops: list[float]) -> list[Line]:
    return [line(x0, top, x1, f"{name}{n}") for n, top in enumerate(tops, 1)]


# Two columns whose lines are offset from each other and share two gaps by coincidence (around
# 60 and 120), which is where a cut across the whole page would wrongly slice both columns.
LEFT = column(40, 300, "left", [0, 14, 28, 42, 70, 84, 98, 128, 142, 156])
RIGHT = column(340, 550, "right", [5, 19, 33, 47, 75, 89, 103, 133])


class TestColumns:
    def test_two_columns_are_read_one_after_the_other(self) -> None:
        assert read(LEFT + RIGHT) == [ln.text for ln in LEFT + RIGHT]

    def test_a_right_to_left_page_starts_with_the_right_column(self) -> None:
        assert read(LEFT + RIGHT, right_to_left=True) == [ln.text for ln in RIGHT + LEFT]

    def test_the_order_lines_arrive_in_does_not_matter(self) -> None:
        shuffled = [*reversed(RIGHT), *LEFT[::2], *reversed(LEFT[1::2])]
        assert read(shuffled) == [ln.text for ln in LEFT + RIGHT]

    def test_a_heading_across_both_columns_comes_first(self) -> None:
        heading = line(40, -30, 550, "name across the page")
        assert read([*LEFT, *RIGHT, heading]) == [heading.text] + [ln.text for ln in LEFT + RIGHT]

    def test_a_line_across_both_columns_below_them_comes_last(self) -> None:
        footer = line(40, 200, 550, "footer across the page")
        assert read([footer, *LEFT, *RIGHT]) == [ln.text for ln in LEFT + RIGHT] + [footer.text]

    def test_a_column_that_ends_early_is_still_a_column(self) -> None:
        """A sidebar shorter than the main column must not be split where it runs out."""
        main = column(40, 300, "main", [top * 14 for top in range(20)])
        sidebar = column(340, 550, "side", [3, 17, 31, 45])
        assert read(main + sidebar) == [ln.text for ln in main + sidebar]

    def test_a_column_with_a_gap_in_it_is_still_one_column(self) -> None:
        """A sidebar with a blank stretch beside the main column's text stays in one piece."""
        main = column(40, 300, "main", [top * 14 for top in range(12)])
        sidebar = column(340, 550, "side", [3, 17, 31, 115, 129, 143])
        assert read(main + sidebar) == [ln.text for ln in main + sidebar]


class TestNotColumns:
    def test_a_date_stays_on_its_jobs_line(self) -> None:
        """Dates set to the right of each job title are part of the job, not a second column."""
        lines = [
            line(40, 0, 200, "Sales Executive"),
            line(450, 0, 550, "2020 - 2023"),
            line(50, 14, 540, "Managed 40 pharmacies across the Delta region"),
            line(50, 28, 500, "Opened 25 new accounts"),
            line(40, 50, 220, "Medical Representative"),
            line(450, 50, 550, "2017 - 2020"),
            line(50, 64, 530, "Visited 140 doctors a month"),
        ]
        assert read(lines) == [
            "Sales Executive | 2020 - 2023",
            "Managed 40 pharmacies across the Delta region",
            "Opened 25 new accounts",
            "Medical Representative | 2017 - 2020",
            "Visited 140 doctors a month",
        ]

    def test_a_date_stays_with_its_job_when_nothing_crosses_between_them(self) -> None:
        """Jobs listed with no description: nothing crosses the space before the dates."""
        lines = [
            line(40, 0, 200, "Sales Executive"),
            line(450, 0, 550, "2020 - 2023"),
            line(40, 14, 220, "Medical Representative"),
            line(450, 14, 550, "2017 - 2020"),
            line(40, 28, 180, "Pharmacist"),
            line(450, 28, 550, "2015 - 2017"),
        ]
        assert read(lines) == [
            "Sales Executive | 2020 - 2023",
            "Medical Representative | 2017 - 2020",
            "Pharmacist | 2015 - 2017",
        ]

    def test_a_table_of_labels_and_values_is_read_row_by_row(self) -> None:
        lines = [
            line(40, 0, 100, "Phone:"),
            line(160, 0, 300, "+20 100 000 0101"),
            line(40, 14, 100, "Email:"),
            line(160, 14, 320, "name@example.com"),
            line(40, 28, 100, "City:"),
            line(160, 28, 240, "Alexandria"),
        ]
        assert read(lines) == [
            "Phone: | +20 100 000 0101",
            "Email: | name@example.com",
            "City: | Alexandria",
        ]

    def test_pieces_of_one_row_are_read_in_the_pages_direction(self) -> None:
        lines = [line(400, 0, 550, "first on the right"), line(40, 1, 200, "then the left")]
        assert read(lines, right_to_left=True) == ["first on the right | then the left"]
        assert read(lines) == ["then the left | first on the right"]

    def test_an_empty_page_has_no_rows(self) -> None:
        assert reading_order([], right_to_left=False) == []


def paragraphs(name: str) -> list[str]:
    """The document's text as non-empty lines."""
    text = read_native_text((CORPUS / f"{name}.pdf").read_bytes())
    return [row.strip() for row in text.splitlines() if row.strip()]


def assert_in_sequence(rows: list[str], expected: list[str]) -> None:
    """The expected lines appear one directly after another."""
    starts = [n for n, row in enumerate(rows) if row == expected[0]]
    assert starts, f"{expected[0]!r} not found"
    assert any(rows[n : n + len(expected)] == expected for n in starts), rows


@pytest.mark.parametrize(
    ("name", "expected"),
    [
        # The sidebar's contact labels keep their values, the main column's job keeps its dates.
        ("en-native-03", ["PHONE:", "0100 000 0103"]),
        ("en-native-03", ["EMAIL:", "y.nabil@example.com"]),
        ("en-native-03", ["AHBS Product lead", "Jan 2021 \N{EN DASH} Current"]),
        (
            "en-native-03",
            ["I started working at", "Alexandria university as a software"],
        ),
        # The sidebar's skills are not threaded between the main column's courses.
        ("en-native-05", ["Skills", "PHP - OOP - MVC", "Laravel", "MYSQL", "Html - Html5"]),
        (
            "en-native-05",
            [
                "Backend Developer ― Ipda3 Tech Mansoura, Dakahlia",
                "From February 2022 to May 2022",
            ],
        ),
        ("en-native-06", ["PHONE", "01000000107", "Mail"]),
        # The main column's own column of dates is read on each job's row.
        (
            "en-native-06",
            [
                "EXPERIENCE",
                "2020\tEtmam /Asnani Technologies",
                "Backend Software Engineer(Asp.Net / C# / RestfulApis)",
            ],
        ),
        # An Arabic page is read right to left: the right-hand sidebar whole, then the main
        # column, and a job title before the date set to its left.
        (
            "syn-ar-native-02",
            ["بيانات التواصل", "الجيزة، مصر", "٠١٠٠ ٠٠٠ ٠٢٠٢", "mona.khaled@example.com"],
        ),
        (
            "syn-ar-native-02",
            ["اللغات", "العربية - اللغة الأم", "الإنجليزية - ممتاز", "منى خالد إبراهيم"],
        ),
        (
            "syn-ar-native-02",
            [
                "الخبرة العملية",
                "مطورة واجهات أمامية (Front-End Developer)\tيناير ٢٠٢٢ - الآن",
                "شركة سحابة للحلول الرقمية",
            ],
        ),
    ],
    ids=lambda value: value if isinstance(value, str) else value[0][:24],
)
def test_corpus_columns_are_not_interleaved(name: str, expected: list[str]) -> None:
    assert_in_sequence(paragraphs(name), expected)

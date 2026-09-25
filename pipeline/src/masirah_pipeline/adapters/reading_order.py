"""The order a person reads the lines of one page in (FR-004).

A CV page is read column by column: a two-column template's sidebar is read whole, then its main
column, never one line from each in turn. Two other things also sit side by side on a CV page and
must not be split into columns: a date at the end of a job's line, and a table of labels and
values. What tells them apart:

- A column boundary is a vertical strip of empty page that no line crosses, running down a
  stretch of the page. A line across it (a heading over both columns) ends the stretch.
- Things on one row of a table, or a job and its date, share a baseline. Two separate columns
  line up only by chance, so a split whose sides mostly line up is rows, not columns.

Within a column, lines are read top to bottom, and pieces of one row in the page's direction.
"""

from collections.abc import Sequence
from dataclasses import dataclass

# Empty page narrower than this, in points, is the space between words rather than between
# columns.
MIN_GUTTER = 8.0
# A column has at least this many lines. One line beside another is a row.
MIN_COLUMN_LINES = 2
# Lines whose bottoms are this close, in points, sit on one row.
SAME_ROW = 2.0
# When this share of one side's lines sit on a row with a line across the split, the two sides
# are rows of a table or of a list of jobs and dates, not two columns.
ROWS_SHARE = 0.6

Interval = tuple[float, float]


@dataclass(frozen=True)
class Line:
    """One line of text and its box, measured in points from the page's top-left corner."""

    x0: float
    top: float
    x1: float
    bottom: float
    text: str


def reading_order(lines: Sequence[Line], *, right_to_left: bool) -> list[list[Line]]:
    """The page's rows in reading order, each holding its pieces in reading order."""
    rows: list[list[Line]] = []
    for block in _blocks(list(lines), right_to_left):
        rows += _rows(block, right_to_left)
    return rows


def _blocks(lines: list[Line], right_to_left: bool) -> list[list[Line]]:
    """The lines split into blocks read one after another, each column its own block."""
    blocks: list[list[Line]] = []
    for section, gaps in _sections(lines):
        columns = _columns(section, gaps)
        if columns is None:
            blocks.append(section)
            continue
        first, second = reversed(columns) if right_to_left else columns
        blocks += _blocks(first, right_to_left) + _blocks(second, right_to_left)
    return blocks


def _sections(lines: list[Line]) -> list[tuple[list[Line], list[Interval]]]:
    """Consecutive stretches of the page, each with the vertical strips no line in it crosses.

    A stretch grows band by band down the page for as long as some strip stays uncrossed, so a
    gap shared by both columns by chance does not cut them, and ends at a line crossing every
    remaining strip.
    """
    if not lines:
        return []
    left, right = min(line.x0 for line in lines), max(line.x1 for line in lines)
    sections: list[tuple[list[Line], list[Interval]]] = []
    current: list[Line] = []
    gaps: list[Interval] = []
    for band in _bands(lines):
        free = _uncovered(band, left, right)
        shared = _intersection(gaps, free)
        if current and shared:
            current, gaps = current + band, shared
        else:
            if current:
                sections.append((current, gaps))
            current, gaps = band, free
    sections.append((current, gaps))
    return sections


def _bands(lines: list[Line]) -> list[list[Line]]:
    """Lines grouped where their vertical extents overlap, top to bottom."""
    bands: list[list[Line]] = []
    bottom = float("-inf")
    for line in sorted(lines, key=lambda line: (line.top, line.x0)):
        if bands and line.top < bottom:
            bands[-1].append(line)
            bottom = max(bottom, line.bottom)
        else:
            bands.append([line])
            bottom = line.bottom
    return bands


def _uncovered(lines: list[Line], left: float, right: float) -> list[Interval]:
    """The strips between left and right that none of the lines cross, if wide enough."""
    strips: list[Interval] = []
    edge = left
    for line in sorted(lines, key=lambda line: line.x0):
        if line.x0 > edge:
            strips.append((edge, line.x0))
        edge = max(edge, line.x1)
    strips.append((edge, right))
    return [(start, end) for start, end in strips if end - start >= MIN_GUTTER]


def _intersection(first: list[Interval], second: list[Interval]) -> list[Interval]:
    overlaps = [(max(a0, b0), min(a1, b1)) for a0, a1 in first for b0, b1 in second]
    return [(start, end) for start, end in overlaps if end - start >= MIN_GUTTER]


def _columns(lines: list[Line], gaps: list[Interval]) -> tuple[list[Line], list[Line]] | None:
    """The lines either side of the widest gutter, when the two sides are columns."""
    for start, end in sorted(gaps, key=lambda gap: gap[0] - gap[1]):
        before = [line for line in lines if line.x1 <= start]
        after = [line for line in lines if line.x0 >= end]
        if min(len(before), len(after)) < MIN_COLUMN_LINES:
            continue
        if _share_rows(before, after):
            return None
        return before, after
    return None


def _share_rows(first: list[Line], second: list[Line]) -> bool:
    fewer, more = sorted((first, second), key=len)
    on_a_row = sum(
        any(abs(line.bottom - other.bottom) <= SAME_ROW for other in more) for line in fewer
    )
    return on_a_row >= ROWS_SHARE * len(fewer)


def _rows(lines: list[Line], right_to_left: bool) -> list[list[Line]]:
    """Lines grouped into rows top to bottom, each row's pieces in the page's direction."""
    rows: list[list[Line]] = []
    for line in sorted(lines, key=lambda line: (line.top, line.x0)):
        if rows and _same_row(rows[-1][0], line):
            rows[-1].append(line)
        else:
            rows.append([line])
    for row in rows:
        row.sort(key=lambda line: -line.x1 if right_to_left else line.x0)
    return rows


def _same_row(first: Line, second: Line) -> bool:
    overlap = min(first.bottom, second.bottom) - max(first.top, second.top)
    height = min(first.bottom - first.top, second.bottom - second.top)
    return overlap >= height / 2

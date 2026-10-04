"""Right-to-left lines put back into the order they are read in.

Chromium, and the online CV builders that print through it, store an Arabic line in a PDF in the
order its glyphs appear from left to right. The text layer then reads every Arabic word
backwards, while the Latin words and numbers inside the line read forwards. This module reverses
that. Laying a line out is the Unicode Bidirectional Algorithm's reordering step (UAX #9, rule
L2), and applying that step to its own output gives back its input, so the repair is the same
step with each character's level worked out from the stored line.

The levels follow the algorithm's rules in simplified form. Where the stored line cannot show what
the algorithm saw, the spans a CV template sets its fields in, two rules of this module's own
stand in: groups of Latin digits joined by single spaces are one number, as a phone number is in
its own left-to-right span, and a symbol such as "|" between fields starts each field afresh.
"""

import re
import unicodedata

RIGHT, LEFT, NUMBER, SEPARATOR, TERMINATOR, MARK, NEUTRAL = range(7)

MIRRORED = {
    **{"(": ")", ")": "(", "[": "]", "]": "[", "{": "}", "}": "{", "<": ">", ">": "<"},
    **{"«": "»", "»": "«"},
}
# Punctuation around a word, which a word stored backwards carries at the other end.
EDGES = re.compile(r"^\W+|\W+$")


def logical_line(stored: str, *, right_to_left: bool) -> str:
    """The line in reading order. right_to_left is the direction of the paragraph it is in.

    The characters are the stored ones, reordered. Normalising Arabic presentation forms into
    letters has to come afterwards: a lam-alef ligature is one character, and split into two
    letters first it would be reversed along with its word.
    """
    chars = _without_split_marks(stored)
    levels = _levels(chars, right_to_left)
    return "".join(
        MIRRORED.get(chars[i], chars[i]) if levels[i] % 2 else chars[i] for i in _reordered(levels)
    )


def is_right_to_left(char: str) -> bool:
    return unicodedata.bidirectional(char) in ("R", "AL")


def laid_out_right_to_left(text: str) -> bool:
    """Whether any of the text is displayed right to left, so storing it in visual order would
    have changed it. Arabic-Indic digits count: groups of them are laid out right to left."""
    return any(unicodedata.bidirectional(char) in ("R", "AL", "AN") for char in text)


def stored_backwards(words: list[str]) -> bool:
    """Whether Arabic words are stored in visual order, from the stored words themselves.

    The article ال begins a large share of Arabic words, and few end in لا. Stored backwards, the
    two swap. The lam can be fused with the letter after it into one ligature (الإ is stored as
    ا and ﻹ), so each character is normalised on its own.
    """
    trimmed = [word for word in (EDGES.sub("", word) for word in words) if len(word) > 2]
    forwards = sum(_article(word[0], word[1]) for word in trimmed)
    return sum(_article(word[-1], word[-2]) for word in trimmed) > forwards


def _article(alef: str, lam: str) -> bool:
    return unicodedata.normalize("NFKC", alef) == "ا" and (
        unicodedata.normalize("NFKC", lam).startswith("ل")
    )


def _without_split_marks(stored: str) -> str:
    """Drops a space stored before a combining mark: read backwards, the mark comes before its
    letter, and a PDF reader can take the gap between them for a space."""
    return "".join(
        char
        for n, char in enumerate(stored)
        if not (char == " " and stored[n + 1 : n + 2] and _kind(stored[n + 1]) == MARK)
    )


def _kind(char: str) -> int:
    match unicodedata.bidirectional(char):
        case "R" | "AL":
            return RIGHT
        case "L":
            return LEFT
        case "EN" | "AN":
            return NUMBER
        case "ES" | "CS":
            return SEPARATOR
        case "ET":
            return TERMINATOR
        case "NSM":
            return MARK
        case _:
            return NEUTRAL


def _levels(chars: str, right_to_left: bool) -> list[int]:
    kinds = [_kind(char) for char in chars]
    _attach_marks(kinds)
    _join_numbers(chars, kinds)
    _numbers_after_latin(chars, kinds, right_to_left)
    _resolve_neutrals(kinds, right_to_left)
    # Rules I1 and I2. A number left after W7 follows right-to-left text, so it sits one level
    # above that text in either paragraph direction.
    latin = 2 if right_to_left else 0
    return [{RIGHT: 1, LEFT: latin}.get(kind, 2) for kind in kinds]


def _attach_marks(kinds: list[int]) -> None:
    """A mark belongs to its letter, which follows it when stored backwards."""
    for n, kind in enumerate(kinds):
        if kind == MARK:
            neighbours = kinds[n + 1 : n + 2] + kinds[max(n - 1, 0) : n]
            kinds[n] = next((k for k in neighbours if k in (RIGHT, LEFT)), NEUTRAL)


def _join_numbers(chars: str, kinds: list[int]) -> None:
    """Rules W4 and W5: a single separator between digits, or a sign beside them, is part of
    the number.

    A single space between groups of Latin digits is too, which is this module's own rule. CV
    templates set a phone number inside a left-to-right span, where the algorithm keeps its
    groups in order, and the stored line does not show the span. Arabic-Indic digit groups are
    reordered even inside such a span, so they are left to the algorithm's rules.
    """
    for n in range(1, len(kinds) - 1):
        between_digits = kinds[n - 1] == NUMBER and kinds[n + 1] == NUMBER
        latin_digits = _latin_digit(chars[n - 1]) and _latin_digit(chars[n + 1])
        if between_digits and (kinds[n] == SEPARATOR or (chars[n] == " " and latin_digits)):
            kinds[n] = NUMBER
    for n, kind in enumerate(kinds):
        if kind == TERMINATOR and NUMBER in kinds[max(n - 1, 0) : n + 2]:
            kinds[n] = NUMBER
    for n, kind in enumerate(kinds):
        if kind in (SEPARATOR, TERMINATOR):
            kinds[n] = NEUTRAL


def _numbers_after_latin(chars: str, kinds: list[int], right_to_left: bool) -> None:
    """Rule W7: European digits after Latin text are Latin, so "Laravel 7" and "ITI، 2020" stay
    one left-to-right run.

    The algorithm looks back to the last strong character in reading order, which the stored
    line does not give. A symbol such as "|" between fields starts afresh, as the start of the
    line does: templates set each field in its own span, and the algorithm lays each span out on
    its own.
    """
    start = RIGHT if right_to_left else LEFT
    previous = start
    for n, kind in enumerate(kinds):
        if kind in (RIGHT, LEFT):
            previous = kind
        elif unicodedata.bidirectional(chars[n]) == "ON":
            previous = start
        elif kind == NUMBER and previous == LEFT and _latin_digit(chars[n]):
            kinds[n] = LEFT


def _latin_digit(char: str) -> bool:
    return unicodedata.bidirectional(char) == "EN"


def _resolve_neutrals(kinds: list[int], right_to_left: bool) -> None:
    """Rules N1 and N2: neutrals between two runs of one direction take it, and otherwise the
    paragraph's. Numbers count as right-to-left here."""
    base = RIGHT if right_to_left else LEFT
    n = 0
    while n < len(kinds):
        if kinds[n] != NEUTRAL:
            n += 1
            continue
        end = n
        while end < len(kinds) and kinds[end] == NEUTRAL:
            end += 1
        before = _direction(kinds[n - 1]) if n > 0 else base
        after = _direction(kinds[end]) if end < len(kinds) else base
        kinds[n:end] = [before if before == after else base] * (end - n)
        n = end


def _direction(kind: int) -> int:
    return RIGHT if kind == NUMBER else kind


def _reordered(levels: list[int]) -> list[int]:
    """Rule L2: from the highest level down to 1, reverse every run at that level or above."""
    order = list(range(len(levels)))
    for level in range(max(levels, default=0), 0, -1):
        n = 0
        while n < len(order):
            if levels[order[n]] < level:
                n += 1
                continue
            end = n
            while end < len(order) and levels[order[end]] >= level:
                end += 1
            order[n:end] = reversed(order[n:end])
            n = end
    return order

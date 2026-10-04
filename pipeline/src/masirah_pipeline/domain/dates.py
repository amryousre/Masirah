"""Hijri and Gregorian dates and Arabic-Indic numerals (T044, FR-009).

normalise_date turns a date as a CV writes it into the one comparable form the profile uses:
YYYY-MM, or YYYY when only a year is given, or "present" for a role still held. It reads English,
Egyptian and Levantine Arabic month names, Arabic-Indic digits, day-first numeric dates (as Egypt
writes them) and Hijri dates, which become Gregorian.

A Hijri month spans two Gregorian months, so it becomes the one its middle falls in, and a Hijri
year the Gregorian year its middle falls in. The conversion uses the arithmetic Islamic calendar,
which can differ from the observed calendar by a day or two: never enough to move a month's middle.
"""

import re
from datetime import date

PRESENT = "present"

# Gregorian years a CV date can sensibly name, and Hijri years written without a marker.
GREGORIAN_YEARS = range(1900, 2101)
MAX_DAY = 31
HIJRI_YEARS = range(1300, 1501)

ARABIC_INDIC = {base + n: str(n) for base in (0x0660, 0x06F0) for n in range(10)}
ARABIC_INDIC |= {0x066B: ".", 0x066C: ","}  # Arabic decimal and thousands separators

STILL_HELD = {
    "present", "current", "currently", "now", "till now", "until now", "to date", "till date",
    "ongoing", "today", "حتي الان", "الان", "حاليا", "حتي تاريخه", "حتي اليوم", "مستمر",
}  # fmt: skip

GREGORIAN_MONTHS = {
    1: "jan january يناير كانون الثاني",
    2: "feb february فبراير شباط",
    3: "mar march مارس اذار",
    4: "apr april ابريل نيسان",
    5: "may مايو ايار",
    6: "jun june يونيو يونيه حزيران",
    7: "jul july يوليو يوليه تموز",
    8: "aug august اغسطس اب",
    9: "sep sept september سبتمبر ايلول",
    10: "oct october اكتوبر تشرين الاول",
    11: "nov november نوفمبر تشرين الثاني",
    12: "dec december ديسمبر كانون الاول",
}
HIJRI_MONTHS = {
    1: "محرم",
    2: "صفر",
    3: "ربيع الاول",
    4: "ربيع الاخر ربيع الثاني",
    5: "جمادي الاولي",
    6: "جمادي الاخره جمادي الثانيه",
    7: "رجب",
    8: "شعبان",
    9: "رمضان",
    10: "شوال",
    11: "ذو القعده ذي القعده",
    12: "ذو الحجه ذي الحجه",
}
# Two-word names are listed as pairs; every other word is a name on its own.
TWO_WORD = re.compile(r"(?:كانون|تشرين|ربيع|جمادي|ذو|ذي) \S+")

HIJRI_MARKER = re.compile(r"(?<=\d)\s*ه(?:ـ)?(?!\w)|(?<!\w)ه(?:ـ)?(?!\w)")
ARABIC_MARKS = re.compile("[ؐ-ًؚ-ٰٟـ]")
ARABIC_LETTERS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ة": "ه", "ى": "ي"})
NUMBER = re.compile(r"\d+")
# The arithmetic Islamic calendar's epoch, as a Julian day, and the Julian day of Gregorian day 1.
ISLAMIC_EPOCH = 1948439.5
GREGORIAN_ORDINAL_EPOCH = 1721424.5


def interpret_numerals(text: str) -> str:
    """Arabic-Indic and Persian digits, and the Arabic separators, as their ASCII forms."""
    return text.translate(ARABIC_INDIC)


def normalise_date(written: str) -> str | None:
    text = _fold(interpret_numerals(written))
    if text in STILL_HELD:
        return PRESENT
    hijri = bool(HIJRI_MARKER.search(text))
    text = HIJRI_MARKER.sub(" ", text)
    month, hijri_month, text = _month_name(text)
    hijri = hijri or hijri_month
    numbers = [int(number) for number in NUMBER.findall(text)]
    found = _year_month_and_day(numbers, month)
    if found is None:
        return None
    year, month, day = found
    if not hijri and year in HIJRI_YEARS:
        hijri = True
    if hijri:
        return _from_hijri(year, month) if year in HIJRI_YEARS else None
    if year not in GREGORIAN_YEARS or not _a_real_day(year, month, day):
        return None
    return f"{year}" if month is None else f"{year}-{month:02d}"


def _a_real_day(year: int, month: int | None, day: int | None) -> bool:
    """A day the date names must exist, though it is not kept: 31 February is no date."""
    if month is None or day is None:
        return True
    try:
        date(year, month, day)
    except ValueError:
        return False
    return True


def _fold(text: str) -> str:
    text = ARABIC_MARKS.sub("", text).translate(ARABIC_LETTERS).casefold()
    text = re.sub(r"[.,;]", " ", text)
    return " ".join(text.split())


def _names(table: dict[int, str]) -> dict[str, int]:
    names: dict[str, int] = {}
    for month, spellings in table.items():
        pairs = TWO_WORD.findall(spellings)
        rest = TWO_WORD.sub(" ", spellings).split()
        names |= dict.fromkeys(pairs + rest, month)
    return names


GREGORIAN_NAMES = _names(GREGORIAN_MONTHS)
HIJRI_NAMES = _names(HIJRI_MONTHS)


def _month_name(text: str) -> tuple[int | None, bool, str]:
    """The month a name in the text gives, whether it is a Hijri month, and the text without it."""
    for names, hijri in ((HIJRI_NAMES, True), (GREGORIAN_NAMES, False)):
        for name in sorted(names, key=len, reverse=True):
            pattern = rf"(?<!\w){re.escape(name)}(?!\w)"
            if re.search(pattern, text):
                return names[name], hijri, re.sub(pattern, " ", text, count=1)
    return None, False, text


def _year_month_and_day(
    numbers: list[int], named: int | None
) -> tuple[int, int | None, int | None] | None:
    """The year, month and day among a date's numbers, given any month named in words."""
    years = [n for n in numbers if n >= 1000]
    others = [n for n in numbers if n < 1000]
    if len(years) != 1:
        return None
    year = years[0]
    if named is not None:
        # A month in words may come with its day, as in 15 March 2021.
        if not others:
            return year, named, None
        if len(others) == 1 and 1 <= others[0] <= MAX_DAY:
            return year, named, others[0]
        return None
    if not others:
        return year, None, None
    day: int | None = None
    if len(others) == 1:
        month = others[0]
    elif len(others) == 2:
        # Day before month, as Egypt writes it, unless the second number cannot be a month.
        day, month = others if others[1] <= 12 else reversed(others)
    else:
        return None
    return (year, month, day) if 1 <= month <= 12 else None


def _from_hijri(year: int, month: int | None) -> str:
    if month is None:
        middle = (_hijri_day(year, 1, 1) + _hijri_day(year + 1, 1, 1)) / 2
        return f"{_gregorian(middle).year}"
    gregorian = _gregorian(_hijri_day(year, month, 15))
    return f"{gregorian.year}-{gregorian.month:02d}"


def _hijri_day(year: int, month: int, day: int) -> float:
    """The Julian day of a date in the arithmetic Islamic calendar."""
    return (
        day
        + -(-59 * (month - 1) // 2)  # ceil(29.5 x (month - 1))
        + (year - 1) * 354
        + (3 + 11 * year) // 30
        + ISLAMIC_EPOCH
        - 1
    )


def _gregorian(julian_day: float) -> date:
    return date.fromordinal(int(julian_day - GREGORIAN_ORDINAL_EPOCH))

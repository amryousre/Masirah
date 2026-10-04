"""Which language a CV is in, and whether version 1.0 supports it (T046, ADR 0005).

Arabic and English are supported. A CV in another language is flagged unsupported rather than
parsed, but never on the strength of a minority of its text: an English CV that quotes a few
French sentences is still English (SC-015).

Each line votes, weighted by its letters:
- A line mostly in a script other than Arabic or Latin, such as Cyrillic, votes for an
  unsupported language.
- Arabic-script lines are Arabic, Persian or Urdu, decided once for the whole CV from the letters
  and words those languages do not share. A single line holds too little to tell them apart.
- A Latin-script line votes by its function words (the, and, of; le, et, de), and failing those
  by its accented letters (é, ñ, ü), which English does not use. A phrase of a few plain words
  that nothing else claims, such as a job title, is English. A name or a single skill does not
  vote.

A CV is flagged when most of the votes are for unsupported languages. The same votes decide
whether a supported CV is Arabic, English or mixed, so an Arabic CV listing its skills in Latin
letters is still Arabic.
"""

import re
import unicodedata
from collections import Counter
from dataclasses import dataclass

SUPPORTED = frozenset({"ar", "en"})
OTHER_SCRIPT = "other"
# A CV is mixed when Arabic and English each hold at least this share of the lines that voted.
MIXED_SHARE = 0.2
# A CV is unsupported when more than this share of the votes are for other languages.
UNSUPPORTED_SHARE = 0.5
# A line votes by its function words only when its leading language has at least this many.
MIN_VOTES = 2
# A Latin line of at least this many plain words, claimed by no other language, is English.
PHRASE_WORDS = 3
# Persian or Urdu evidence across a CV needed to call its Arabic script Persian or Urdu.
MIN_EVIDENCE = 2

LATIN_FUNCTION_WORDS = {
    "en": "the and of in with for to at on an is my from as by our we i this that are or was",
    "fr": "le la les des du de et en pour avec dans une un au aux sur par est je qui que ou "
    "mon ma mes l d chez",
    "es": "el los las del y con para en una un por que es mi más al se",
    "de": "der die das und mit für von zu im ist ein eine den dem bei auf als",
    "it": "il lo gli di e con per in una un che è del della dei nel",
    "pt": "o os as do da dos das e com para em uma um que é no na",
}
# Accented letters English does not use, each counted for the language it most suggests.
ACCENTS = {
    **dict.fromkeys("éèêëàâîïôûùçœæÿ", "fr"),
    **dict.fromkeys("ñáíóú¿¡", "es"),
    **dict.fromkeys("äöüß", "de"),
    **dict.fromkeys("ãõ", "pt"),
    **dict.fromkeys("ìò", "it"),
}
ARABIC_WORDS = frozenset(
    ["في", "من", "على", "الى", "إلى", "عن", "مع", "التي", "الذي", "هذه", "هذا", "كان"]
)
PERSIAN_WORDS = frozenset(
    [
        "است",
        "را",
        "این",
        "که",
        "كه",
        "برای",
        "با",
        "از",
        "به",
        "می",
        "های",
        "ها",
        "در",
        "شرکت",
        "شركت",
    ]
)
# Letters Persian or Urdu use and Arabic does not, the Persian yeh and kaf included.
PERSIAN_LETTERS = frozenset("پچژگیک")
URDU_LETTERS = frozenset("ٹڈڑںے")

LATIN_WORDS = {
    language: frozenset(words.split()) for language, words in LATIN_FUNCTION_WORDS.items()
}
WORD = re.compile(r"[^\W\d_]+")


@dataclass(frozen=True)
class LanguageVerdict:
    """The CV's language: ar, en or mixed when supported, or the unsupported language found."""

    language: str
    supported: bool


@dataclass
class _Arabic:
    """Arabic-script lines, whose language is decided for the CV as a whole."""

    letters: int = 0
    arabic: int = 0
    persian: int = 0
    urdu: int = 0

    def add(self, line: str, words: list[str], letters: int) -> None:
        self.letters += letters
        self.arabic += sum(word in ARABIC_WORDS for word in words)
        self.persian += sum(word in PERSIAN_WORDS for word in words)
        self.persian += sum(char in PERSIAN_LETTERS for char in line)
        self.urdu += sum(char in URDU_LETTERS for char in line)

    @property
    def language(self) -> str:
        if self.urdu >= MIN_EVIDENCE:
            return "ur"
        if self.persian >= MIN_EVIDENCE and self.persian > self.arabic:
            return "fa"
        return "ar"


def detect_language(text: str) -> LanguageVerdict:
    votes: Counter[str] = Counter()
    arabic_script = _Arabic()
    arabic_letters = latin_letters = 0
    for line in text.splitlines():
        scripts = Counter(_script(char) for char in line if char.isalpha())
        letters = sum(scripts.values())
        if not letters:
            continue
        arabic_letters += scripts["arabic"]
        latin_letters += scripts["latin"]
        words = [word.casefold() for word in WORD.findall(line)]
        if scripts[OTHER_SCRIPT] > letters / 2:
            votes[OTHER_SCRIPT] += letters
        elif scripts["arabic"] > letters / 2:
            arabic_script.add(line, words, letters)
        elif (language := _latin_language(line, words)) is not None:
            votes[language] += letters
    if arabic_script.letters:
        votes[arabic_script.language] += arabic_script.letters
    unsupported = {
        language: count for language, count in votes.items() if language not in SUPPORTED
    }
    if unsupported and sum(unsupported.values()) > UNSUPPORTED_SHARE * sum(votes.values()):
        language = max(unsupported, key=lambda name: unsupported[name])
        return LanguageVerdict(language, supported=False)
    if votes["ar"] + votes["en"] == 0:
        return LanguageVerdict(_by_script(arabic_letters, latin_letters), supported=True)
    return LanguageVerdict(_by_script(votes["ar"], votes["en"]), supported=True)


def _script(letter: str) -> str:
    if "؀" <= letter <= "ۿ":
        return "arabic"
    if unicodedata.name(letter, "").startswith("LATIN"):
        return "latin"
    return OTHER_SCRIPT


def _latin_language(line: str, words: list[str]) -> str | None:
    counts = Counter(
        language
        for word in words
        for language, function_words in LATIN_WORDS.items()
        if word in function_words
    )
    ranked = counts.most_common(2)
    if ranked and ranked[0][1] >= MIN_VOTES:
        tied = len(ranked) == 2 and ranked[1][1] == ranked[0][1]
        return None if tied else ranked[0][0]
    accents = Counter(ACCENTS[char] for char in line.casefold() if char in ACCENTS)
    if accents:
        return accents.most_common(1)[0][0]
    # A Latin phrase no other language claims, such as a job title or an employer's name, is the
    # English side of a CV; a single word, such as a skill, says nothing.
    unclaimed = not ranked or ranked[0][0] == "en"
    return "en" if unclaimed and len(words) >= PHRASE_WORDS else None


def _by_script(arabic: int, english: int) -> str:
    """ar, en or mixed from the weight of Arabic and English. The weights are the lines that
    voted, so an Arabic CV listing its skills in Latin letters is still Arabic, and fall back to
    letters only when no line voted."""
    total = arabic + english
    if total == 0:
        return "en"
    share = arabic / total
    if share >= 1 - MIXED_SHARE:
        return "ar"
    if share <= MIXED_SHARE:
        return "en"
    return "mixed"

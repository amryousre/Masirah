"""Which language a CV is in, and whether version 1.0 supports it (T046, ADR 0005).

Arabic and English are supported. A CV in another language is flagged unsupported rather than
parsed, but never on the strength of a minority of its text: an English CV that quotes a few
French sentences is still English (SC-015).

Each line votes for the language its function words belong to (the, and, of; le, et, de; و، في،
من). Arabic-script lines are Arabic unless Persian or Urdu letters or words outweigh it. A Latin
phrase of a few words that no other language claims, such as a job title, is English. A name or a
single skill does not vote. So a CV is only flagged when most of the text that can be told apart
is in an unsupported language. Each vote weighs as many letters as its line has, and the same
votes decide whether a supported CV is Arabic, English or mixed: an Arabic CV listing its skills in
Latin letters is still Arabic.
"""

import re
from collections import Counter
from dataclasses import dataclass

SUPPORTED = frozenset({"ar", "en"})
# A CV is mixed when Arabic and English each hold at least this share of the lines that voted.
MIXED_SHARE = 0.2
# A CV is unsupported when this share of the letters in lines that voted is in other languages.
UNSUPPORTED_SHARE = 0.5
# A line votes only when its leading language has at least this many function words.
MIN_VOTES = 2
# A Latin line of at least this many words, with no function words of another language, is English.
PHRASE_WORDS = 3

FUNCTION_WORDS = {
    "en": "the and of in with for to at on an is my from as by our we i this that are or was",
    "fr": "le la les des du de et en pour avec dans une un au aux sur par est je qui que ou "
    "mon ma mes l d chez",
    "es": "el los las del y con para en una un por que es mi más al se",
    "de": "der die das und mit für von zu im ist ein eine den dem bei auf als",
    "it": "il lo gli di e con per in una un che è del della dei nel",
    "pt": "o os as do da dos das e com para em uma um que é no na",
    "ar": "في من على الى إلى عن مع التي الذي هذه هذا كان و ب ل",
    "fa": "است را این که كه برای با از به می های ها و",
}
# Letters that Persian or Urdu use and Arabic does not.
PERSIAN_LETTERS = frozenset("پچژگ")
URDU_LETTERS = frozenset("ٹڈڑںے")

WORDS = {language: frozenset(words.split()) for language, words in FUNCTION_WORDS.items()}
WORD = re.compile(r"[^\W\d_]+")


@dataclass(frozen=True)
class LanguageVerdict:
    """The CV's language: ar, en or mixed when supported, or the unsupported language found."""

    language: str
    supported: bool


def detect_language(text: str) -> LanguageVerdict:
    votes: Counter[str] = Counter()
    arabic_letters = latin_letters = 0
    for line in text.splitlines():
        letters = sum(char.isalpha() for char in line)
        arabic = sum("؀" <= char <= "ۿ" for char in line)
        arabic_letters += arabic
        latin_letters += letters - arabic
        if (language := _line_language(line, arabic > letters / 2)) is not None:
            votes[language] += letters
    unsupported = {
        language: count for language, count in votes.items() if language not in SUPPORTED
    }
    voted = sum(votes.values())
    if unsupported and sum(unsupported.values()) > UNSUPPORTED_SHARE * voted:
        language = max(unsupported, key=lambda name: unsupported[name])
        return LanguageVerdict(language, supported=False)
    if votes["ar"] + votes["en"] == 0:
        return LanguageVerdict(_by_script(arabic_letters, latin_letters), supported=True)
    return LanguageVerdict(_by_script(votes["ar"], votes["en"]), supported=True)


def _line_language(line: str, arabic_script: bool) -> str | None:
    words = [word.casefold() for word in WORD.findall(line)]
    if arabic_script:
        if any(char in URDU_LETTERS for char in line):
            return "ur"
        persian = sum(word in WORDS["fa"] for word in words) + sum(
            char in PERSIAN_LETTERS for char in line
        )
        arabic = sum(word in WORDS["ar"] for word in words)
        return "fa" if persian >= MIN_VOTES and persian > arabic else "ar"
    counts = Counter(
        language
        for word in words
        for language, function_words in WORDS.items()
        if language not in ("ar", "fa") and word in function_words
    )
    ranked = counts.most_common(2)
    if ranked and ranked[0][1] >= MIN_VOTES:
        tied = len(ranked) == 2 and ranked[1][1] == ranked[0][1]
        return None if tied else ranked[0][0]
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

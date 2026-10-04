"""Arabic name variants folded to one searchable form (T043, FR-007).

name_normalised gives the form candidate search compares, so that Mohamed, Mohammed, Muhammad and
محمد find each other. It is derived from the extracted name and never entered.

Spelling rules alone cannot do this. Folding names to their consonants would make Mohamed and
Mahmoud both mhmd, Hassan and Hussein both hsn, and Amr and Omar both mr: different names, and
among the commonest in Egypt. So the common names are listed, each with its Arabic spellings and
the Latin spellings Egyptian CVs use, and every spelling maps to the name's Arabic form. Compound
names built on Abd (Abdel Rahman, Abdallah) are generated from their attribute. A name not listed
keeps its own spelling, folded for case, marks and spacing: an unknown name matches itself
exactly, and is never merged with a different one.
"""

import re
import unicodedata
from collections.abc import Iterable

# Arabic spelling first (the form every spelling maps to), then the Latin spellings.
COMMON_NAMES = """
محمد | mohamed mohammed muhammad mohammad mohamad muhamed mouhamed mohmed
أحمد | ahmed ahmad
محمود | mahmoud mahmud mahmood mahmod
مصطفى | mostafa mustafa moustafa mostapha mustapha
خالد | khaled khalid
يوسف | youssef yousef yusuf youssif yousif yosef
حسن | hassan hasan
حسين | hussein hussain hosein hossein husein hussien
حسني | hosny hosni husny
عمرو | amr amro amrou
عمر | omar omer
علي | ali aly
إبراهيم | ibrahim ebrahim ibraheem
طارق | tarek tareq tarik
كريم | karim kareem
شريف | sherif shereef sharif
هاني | hany hani
هشام | hesham hisham
وليد | walid waleed
أيمن | ayman aymen
أشرف | ashraf
عصام | essam esam issam
عماد | emad imad
أسامة | osama ousama usama oussama
إسلام | islam eslam
حمدي | hamdy hamdi
حامد | hamed hamid
سامح | sameh
سامي | samy sami
سيد السيد | sayed sayyid sayyed elsayed alsayed elsayyed
سعيد | saeed said saied
سعد | saad
عادل | adel adil
مجدي | magdy magdi majdi
مدحت | medhat midhat
نبيل | nabil nabeel
نادر | nader nadir
رامي | ramy rami
رضا | reda rida
تامر | tamer
وائل | wael wail
ياسر | yasser yasir yaser
إيهاب | ehab ihab
فادي | fady fadi
جمال | gamal jamal
حازم | hazem hazim
حسام | hossam husam hosam hussam
كمال | kamal kamel
ماهر | maher
ممدوح | mamdouh mamdoh
محسن | mohsen mohsin
مراد | mourad morad murad
ناصر | nasser naser nasir
رجب | ragab rajab
سمير | samir
شادي | shady shadi
وجدي | wagdy wagdi
زكريا | zakaria zakariya zakareya
زياد | ziad ziyad
فتحي | fathy fathi
صلاح | salah
عاطف | atef
إسماعيل | ismail esmail
عثمان | osman othman
فاطمة | fatma fatima fatmah fatemah fatema
مريم | mariam maryam mariem meriam
نور | nour noor nur
آية | aya ayah
سارة | sara sarah
منى | mona muna
هبة | heba hiba hebah
رنا | rana
ياسمين | yasmin yasmine yasmeen
دينا | dina deena
نهى | noha nuha
أميرة | amira amirah ameera
سلمى | salma
هناء | hanaa hana
ريم | reem rim
ندى | nada
إسراء | esraa israa esra
دعاء | doaa duaa
أسماء | asmaa asma
شيماء | shaimaa shaima shymaa
إيمان | eman iman
مروة | marwa marwah
نسمة | nesma nesmah
رانيا | rania ranya
غادة | ghada
سمر | samar
نرمين | nermeen nermin
مي | mai may
زينب | zeinab zainab zaynab
هدى | hoda huda
ليلى | laila layla leila
نادية | nadia nadya
سميرة | samira
خديجة | khadiga khadija khadeeja
عائشة | aisha aysha
هند | hend hind
آلاء | alaa
ولاء | walaa
"""

# Names built on Abd: the attribute in Arabic, then its Latin spellings.
ABD_ATTRIBUTES = """
الرحمن | rahman rahmen rehman
الله | allah alla ullah ala
العزيز | aziz azeez
الحميد | hamid hameed
الحليم | halim haleem
الفتاح | fattah fatah
الرحيم | rahim raheem
المنعم | monem moneim menem monim
الغني | ghany ghani
الحكيم | hakim hakeem
العظيم | azim azeem
الكريم | karim kareem
الناصر | nasser naser
السلام | salam
اللطيف | latif lateef
الهادي | hady hadi
الجواد | gawad
التواب | tawab tawwab
المجيد | magid maged megid majid
الباسط | baset basset
الستار | sattar satar
الوهاب | wahab wahhab
الرازق | razek razik
الخالق | khalek khaliq
القادر | kader qader kadir
المحسن | mohsen mohsin
"""
ABD = "عبد"
# How Abd and its article are written in Latin: Abd, Abdel, Abdul, Abdur and the rest.
ABD_PREFIXES = (
    "abd",
    "abde",
    "abdel",
    "abdal",
    "abdul",
    "abdil",
    "abdu",
    "abdo",
    "abdou",
    "abdar",
    "abder",
    "abdur",
)
# The Latin article, written apart as in "El Sayed", is part of the name that follows it.
LATIN_ARTICLES = frozenset({"el", "al"})

ARABIC_MARKS = re.compile("[ؐ-ًؚ-ٰٟـ]")
ARABIC_LETTERS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ة": "ه", "ى": "ي"})
TOKEN = re.compile(r"[^\W\d_]+")


def name_normalised(name: str) -> str:
    """The name's searchable form: one form per part, separated by spaces."""
    return " ".join(_canonical(part) for part in _parts(name))


def _parts(name: str) -> list[str]:
    """The name's parts, folded, with Abd joined to the attribute that follows it."""
    # Marks go first: a short-vowel mark is not a letter, and would split its word in two.
    text = ARABIC_MARKS.sub("", unicodedata.normalize("NFKC", name))
    tokens = [_fold(token) for token in TOKEN.findall(text)]
    tokens = [token for token in tokens if token and token not in LATIN_ARTICLES]
    parts: list[str] = []
    for token in tokens:
        if parts and _is_abd(parts[-1]):
            parts[-1] = _fold(parts[-1] + token)
        else:
            parts.append(token)
    return parts


def _is_abd(part: str) -> bool:
    return part == ABD or part in ABD_PREFIXES


def _canonical(part: str) -> str:
    return CANONICAL.get(part, part)


def _fold(text: str) -> str:
    """Arabic without marks and with its letter variants as one; Latin lower-case and plain,
    with doubled letters single, since Egyptian spelling doubles them freely."""
    if any("؀" <= char <= "ۿ" for char in text):
        return ARABIC_MARKS.sub("", text).translate(ARABIC_LETTERS)
    plain = "".join(
        char for char in unicodedata.normalize("NFKD", text.casefold()) if char.isascii()
    )
    return re.sub(r"(.)\1+", r"\1", plain)


def _entries(table: str) -> Iterable[tuple[list[str], list[str]]]:
    for line in table.strip().splitlines():
        arabic, latin = line.split("|")
        yield arabic.split(), latin.split()


def _build() -> dict[str, str]:
    spellings: dict[str, str] = {}

    def add(spelling: str, canonical: str) -> None:
        folded = _fold(spelling)
        if spellings.get(folded, canonical) != canonical:
            raise ValueError(f"{spelling!r} would name both {spellings[folded]} and {canonical}")
        spellings[folded] = canonical

    for arabic, latin in _entries(COMMON_NAMES):
        canonical = _fold(arabic[0])
        for spelling in arabic + latin:
            add(spelling, canonical)
    for (attribute,), latin in _entries(ABD_ATTRIBUTES):
        canonical = _fold(ABD + attribute)
        add(canonical, canonical)
        for prefix in ABD_PREFIXES:
            for spelling in latin:
                add(prefix + spelling, canonical)
    return spellings


# Every listed spelling, folded, mapped to its name's Arabic form. Building it refuses any
# spelling that would map to two names, so the table cannot quietly merge names.
CANONICAL = _build()

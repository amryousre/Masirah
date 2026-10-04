"""Arabic name variants resolve to one searchable form (T037, FR-007).

A recruiter searching for Mohamed must find the candidate whose CV says Mohammed, Muhammad or
محمد. name_normalised is the form search compares: derived from the name, never entered.

It must not merge different names either. A consonant skeleton would turn Mohamed and Mahmoud
both into mhmd, and Hassan and Hussein both into hsn, which are among the commonest different
names in Egypt, so search would stop telling candidates apart.
"""

import pytest

from masirah_pipeline.domain.arabic import name_normalised


@pytest.mark.parametrize(
    "spellings",
    [
        ["Mohamed", "Mohammed", "Muhammad", "Mohammad", "Mohamad", "محمد", "مُحَمَّد"],
        ["Ahmed", "Ahmad", "أحمد", "احمد"],
        ["Mahmoud", "Mahmud", "محمود"],
        ["Mostafa", "Mustafa", "Moustafa", "مصطفى", "مصطفي"],
        ["Khaled", "Khalid", "خالد"],
        ["Youssef", "Yousef", "Yusuf", "Youssif", "يوسف"],
        ["Hassan", "Hasan", "حسن"],
        ["Hussein", "Hussain", "Hosein", "حسين"],
        ["Amr", "Amro", "عمرو"],
        ["Omar", "Omer", "عمر"],
        ["Gamal", "Jamal", "جمال"],
        ["Fatma", "Fatima", "Fatmah", "فاطمة", "فاطمه"],
        ["Sherif", "Shereef", "شريف"],
        ["Hossam", "Husam", "حسام"],
        ["Hesham", "Hisham", "هشام"],
        ["Mariam", "Maryam", "Mariem", "مريم"],
        [
            "Abdel Rahman",
            "Abdelrahman",
            "Abdulrahman",
            "Abd El-Rahman",
            "Abd Al Rahman",
            "Abdurrahman",
            "عبد الرحمن",
            "عبدالرحمن",
        ],
        ["Abdallah", "Abdullah", "Abdalla", "Abd Allah", "عبدالله", "عبد الله"],
        ["El Sayed", "Elsayed", "Al-Sayed", "Sayed", "Sayyid", "السيد", "سيد"],
    ],
    ids=lambda spellings: spellings[0],
)
def test_spellings_of_one_name_resolve_to_one_form(spellings: list[str]) -> None:
    forms = {name_normalised(spelling) for spelling in spellings}
    assert len(forms) == 1, forms


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ("Mohamed", "Mahmoud"),
        ("محمد", "محمود"),
        ("Hassan", "Hussein"),
        ("حسن", "حسين"),
        ("Amr", "Omar"),
        ("Ahmed", "Hamed"),
        ("Saad", "Sayed"),
        ("Saeed", "Sayed"),
        ("Hossam", "Hesham"),
        ("Khaled", "Walid"),
        ("Abdel Rahman", "Abdel Rahim"),
    ],
)
def test_different_names_stay_different(first: str, second: str) -> None:
    assert name_normalised(first) != name_normalised(second)


def test_a_full_name_is_the_same_in_either_script() -> None:
    latin = name_normalised("Mohamed Abdel Rahman El Sayed")
    assert latin == name_normalised("محمد عبد الرحمن السيد")
    assert latin.split() == [
        name_normalised("Mohamed"),
        name_normalised("Abdelrahman"),
        name_normalised("Elsayed"),
    ]


def test_a_name_outside_the_table_keeps_its_own_spelling() -> None:
    """Exact, not merged: an unknown name still matches itself, however it is cased or spaced."""
    assert name_normalised("Zorba") == name_normalised("  ZORBA ")
    assert name_normalised("Zorba") != name_normalised("Zarbi")
    assert name_normalised("زوربا") == name_normalised("زُوربا")


def test_case_spacing_and_punctuation_do_not_matter() -> None:
    assert name_normalised("  MOHAMED   ahmed ") == name_normalised("Mohamed-Ahmed")


def test_a_name_without_letters_has_an_empty_form() -> None:
    assert name_normalised(" - ") == ""

# Anonymised CV corpus (T028)

Real Egyptian CVs, anonymised, with the correct extraction of every FR-008 field written beside
each one. The accuracy suite (T029) measures extraction against these labels, and SC-002 and
SC-003 are gated on that measurement, so the labels matter as much as the documents.

## Where the documents come from

Real CVs collected by the project owner, who confirmed on 24 September 2026 that legal approval
covers using them. Synthetic CVs were rejected in research.md because they do not reproduce what
breaks parsers: skewed photographs, mixed-direction text and multi-column templates.

The originals and the anonymisation plan never enter this repository. Both name real people, so
they stay on the owner's machine, outside the working tree.

## How they were anonymised

`pipeline/tools/anonymise_cv.py`, driven by a plan kept beside the originals:

- **Replaced with invented values:** names, emails, phone numbers, street addresses, dates of
  birth (same year, so age stays realistic), social media handles, personal project URLs and
  certificate or verification codes. Invented emails use `example.com`, and invented mobile
  numbers start `01000000`.
- **Removed:** photographs (replaced with a blank of the same size, so the layout is unchanged),
  every link, all document metadata and any attachment.
- **Kept, because extraction and later tests need them:** employers, job titles, dates,
  education, cities, skills, nationality and marital status.

The tool re-reads every output before keeping it. The output fails, and is deleted, if any
original value survives in its text, metadata, links or raw objects, if an original photo's
pixels are still embedded, or if any line reads differently from what was intended.
`tests/unit/test_cv_corpus.py` then re-checks every committed file in CI. No metadata, links or
attachments are allowed, and every email and Egyptian mobile number must be an invented one.

## Labels

Each `name.pdf` has a `name.json` beside it:

```json
{
  "document": { "capture": "native", "language": "en", "layout": "two_column", "pages": 2 },
  "expected": "parsed",
  "profile": {
    "name": "…", "emails": ["…"], "phones": ["+201000000101"], "location": "Alexandria",
    "years_of_experience": null,
    "employment": [{ "employer": "…", "title": "…", "start": "2021-01", "end": "present" }],
    "education": [{ "institution": "…", "qualification": "…", "start": "2011", "end": "2015" }],
    "skills": ["…"],
    "languages": [{ "language": "Arabic", "level": "Mother tongue" }],
    "certifications": [{ "name": "…", "issuer": "…" }]
  },
  "protected": { "date_of_birth": "1995-03-07", "nationality": "Egyptian" }
}
```

| Field | Convention |
|---|---|
| `document.capture` | `native`, `scanned` or `photographed` (SC-002 or SC-003) |
| `document.language` | `en`, `ar`, `mixed` or `fr`. French is outside version 1.0 (ADR 0005) |
| `expected` | `parsed`, or `unsupported_language` for a CV the system must flag instead of extracting |
| Dates | `YYYY-MM`, or `YYYY` when the CV gives only a year. An `end` of `"present"` means current. `null` means the CV does not say |
| `phones` | E.164, so `01000000101` is labelled `+201000000101` |
| `location` | The city the candidate lives in, or `null` if the CV does not say |
| `years_of_experience` | Only when the CV states a figure. Never computed from the dates |
| `education` | Degrees and diplomas. Courses and online programmes go in `certifications`, even when the CV lists them under education |
| `employment` | Paid roles, including traineeships. Volunteering and projects are left out |
| `skills` | Technical skills the CV lists as skills. Soft skills are not labelled |
| `protected` | Attributes FR-017 redacts before scoring, when the CV shows them. Not extraction targets |

Values are written as the CV writes them, with obvious typos corrected ("Sofware" is labelled
"Software"). How strictly each field is compared, for example exact names but overlapping skill
sets, is T029's decision, not the labels'.

## Coverage

T028 asks for each of these. The corpus holds English native PDFs only so far.

| Kind | Have | Files |
|---|---|---|
| English, native PDF | 8 | `en-native-01` to `08` |
| Two-column layout | 3 | `en-native-03`, `05`, `06` |
| Photo on the CV | 1 | `en-native-06` |
| Arabic | 0 | |
| Mixed Arabic and English | 0 | `en-native-05` has one Arabic course title, which is not enough |
| Scanned | 0 | |
| Photographed | 0 | |
| Wholly French | 0 | |
| English with a few French lines | 0 | |

A scanned or photographed copy of a CV already here needs no new labels. Print the anonymised
PDF, scan or photograph it, and copy its JSON with `capture` changed. No new personal data is
involved.

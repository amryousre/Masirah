# CV corpus (T028)

Egyptian CVs with the correct extraction of every FR-008 field written beside each one. The
accuracy suite (T029) measures extraction against these labels, and SC-002 and SC-003 are gated
on that measurement, so the labels matter as much as the documents.

## Where the documents come from

Three kinds, told apart in each document's labels:

| Kind | Files | `origin` | `simulated` |
|---|---|---|---|
| Real CVs, anonymised | `en-native-*` | `real` | `false` |
| Synthetic CVs, invented from scratch | `syn-*-native-*` | `synthetic` | `false` |
| Scans and photographs simulated from a document above | `*-scanned-*`, `*-photographed-*` | its source's | `true` |

**Real CVs** were collected by the project owner, who confirmed on 24 September 2026 that legal
approval covers using them. The originals and the anonymisation plan never enter this repository.
Both name real people, so they stay on the owner's machine, outside the working tree.

**Synthetic CVs** fill the gaps that real ones have not reached yet: Arabic, mixed Arabic and
English, wholly French, and English with a few French lines. Every person, employer and contact
detail in them is invented. research.md chose real CVs because synthetic ones miss what breaks
parsers. These are used anyway, marked as synthetic, until real ones replace them.

**Simulated captures** are real or synthetic PDFs rasterised and degraded to look scanned or
photographed. Real scans and phone photos are still wanted.

Only real documents decide the gate. T029 reports accuracy for real documents on their own, and
Phase 1 does not exit on synthetic or simulated results.

## How the real CVs were anonymised

`pipeline/tools/anonymise_cv.py`, driven by a plan kept beside the originals:

- **Replaced with invented values:** names, emails, phone numbers, street addresses, dates of
  birth (same year, so age stays realistic), social media handles, personal project URLs and
  certificate or verification codes. Invented emails use `example.com`, and invented mobile
  numbers start `01000000`.
- **Removed:** photographs (replaced with a blank of the same size, so the layout is unchanged),
  every link, annotation (notes, text boxes, file attachments) and form field, all document
  metadata and any embedded file.
- **Kept, because extraction and later tests need them:** employers, job titles, dates,
  education, cities, skills, nationality and marital status.

The tool re-reads every output before keeping it. The output is deleted if any original value
survives in its text, metadata, links or raw objects, if an original photo's pixels are still
embedded, if an annotation or form field remains, if any line reads differently from what was
intended, or if a check cannot run at all.

## How the synthetic CVs and simulated captures were made

The sources are HTML files in `pipeline/tools/synthetic_cvs/`, each in a different template and
font, printed to PDF by Chromium the way a browser or an online CV builder saves one. From
`pipeline/`:

```
node tools/synthetic_cvs/render.mjs <raw folder>
uv run python -m tools.build_synthetic_cvs <raw folder> tests/fixtures/cvs
```

The build strips each PDF's metadata on the way in, then makes the copies listed in
`tools/build_synthetic_cvs.py` with `tools/simulate_capture.py`:

- A **scan** is every page tilted, greyed, grained, blurred slightly and stored as JPEG inside an
  image-only PDF.
- A **photograph** is one page laid on a desk in perspective, unevenly lit and saved as a
  phone-sized JPEG.

Neither has a text layer. A copy's labels are its source's labels with only the capture fields
changed. The sources use Windows fonts, so rendering elsewhere gives different PDFs.

Chromium stores right-to-left lines in visual order, so the Arabic CVs' text layers read backwards
and Arabic-Indic numbers come out reversed (`٢٠٢٢` reads `٢٢٠٢`). Real PDFs do the same, and
extraction has to put it right.

## The checks

`tests/unit/test_cv_corpus.py` re-checks every committed file in CI:

- No PDF carries metadata, links or attachments. No photograph carries EXIF, XMP or a comment.
- Every email is at `example.com`, `.net` or `.org`. Every Egyptian mobile number must be an
  invented one, however it is written: `01…`, `+20…`, `0020…`, letter-spaced, wrapped across
  lines, in Arabic-Indic digits, or stored reversed.
- Every copy carries exactly its source's labels, and a simulated copy has no text layer.

## Labels

Each document has a `.json` file of the same name beside it:

```json
{
  "document": {
    "capture": "native", "language": "en", "layout": "two_column", "pages": 2,
    "origin": "real", "copy_of": null, "simulated": false
  },
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
| `document.origin` | `real` for an anonymised real CV, `synthetic` for an invented one |
| `document.copy_of` | For a scan or photo of another corpus document, that document's name. Otherwise `null` |
| `document.simulated` | `true` when the scan or photo was made digitally rather than with a scanner or a phone |
| `expected` | `parsed`, or `unsupported_language` for a CV the system must flag instead of extracting |
| Dates | `YYYY-MM`, or `YYYY` when the CV gives only a year. An `end` of `"present"` means current. `null` means the CV does not say |
| `phones` | E.164 with ASCII digits, so `01000000101` and `٠١٠٠٠٠٠٠٢٠٢` are labelled `+201000000101` and `+201000000202` |
| `location` | The city the candidate lives in, or `null` if the CV does not say |
| `years_of_experience` | Only when the CV states a figure. Never computed from the dates |
| `education` | Degrees and diplomas. Courses and online programmes go in `certifications`, even when the CV lists them under education |
| `employment` | Paid roles, including traineeships. Volunteering and projects are left out |
| `skills` | Technical skills the CV lists as skills. Soft skills are not labelled |
| `protected` | Attributes FR-017 redacts before scoring, when the CV shows them. Not extraction targets |

Values are copied as the CV writes them, typos included ("Sofware Developer", "Markting"). That
way every label can be checked against its document: `test_cv_corpus.py` requires each Latin-script
value to appear in a native PDF's text, and each labelled year and phone number too. Arabic script
is checked by review instead, because a PDF text layer often stores it in visual order or as
presentation forms, which is exactly what extraction has to repair. How strictly extraction is
compared with a label is T029's decision, for example tolerating case and small spelling
differences, or scoring skills as an overlapping set.

## Coverage

| Kind | Real | Synthetic or simulated | Files |
|---|---|---|---|
| English, native PDF | 8 | 1 | `en-native-01` to `08`, `syn-en-native-01` |
| Two-column layout | 3 | 2 | `en-native-03`, `05`, `06`, `syn-ar-native-02`, `syn-mixed-native-02` |
| Photo on the CV | 1 | 1 | `en-native-06`, `syn-ar-native-03` |
| Arabic | 0 | 3 | `syn-ar-native-01` to `03` |
| Mixed Arabic and English | 0 | 2 | `syn-mixed-native-01`, `02` |
| Scanned | 0 | 2 | `en-scanned-01`, `syn-ar-scanned-01` |
| Photographed | 0 | 2 | `syn-ar-photographed-01`, `syn-en-photographed-01` |
| Wholly French | 0 | 1 | `syn-fr-native-01` |
| English with a few French lines | 0 | 1 | `syn-en-native-01` |

Every row still needs real documents before the gate can close on it. A scan or photo of a
corpus PDF needs no new labels: print the PDF, scan or photograph it, and copy its JSON with
`capture` and `copy_of` set and `simulated` false. No new personal data is involved.

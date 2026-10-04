// Names folded to one searchable form (T069, FR-007): the port of the pipeline's
// domain/arabic.py name_normalised, so a recruiter's search is folded as each candidate's name
// was. The table is the pipeline's, exported to name-spellings.json; the rules are below, and
// tests/unit/names.test.ts checks them against forms the pipeline computed.

import table from "./name-spellings.json";

const SPELLINGS: Readonly<Record<string, string>> = table.spellings;
const ABD = "عبد";
const ABD_PREFIXES = new Set(table.abdPrefixes);
const LATIN_ARTICLES = new Set(table.latinArticles);

/** Short-vowel and other marks, and the tatweel: none is a letter. */
const ARABIC_MARKS = /[\u0610-\u061A\u064B-\u065F\u0670\u0640]/gu;
const ARABIC_LETTERS: Readonly<Record<string, string>> = {
  أ: "ا",
  إ: "ا",
  آ: "ا",
  ٱ: "ا",
  ة: "ه",
  ى: "ي",
};
const ARABIC_VARIANTS = /[أإآٱةى]/gu;
const ARABIC = /[\u0600-\u06FF]/u;
const NOT_ASCII = /[^\u0000-\u007F]/gu;
const TOKEN = /\p{L}+/gu;

/** Arabic without marks and with its letter variants as one; Latin lower-case and plain. */
function fold(text: string): string {
  if (ARABIC.test(text)) {
    return text
      .replace(ARABIC_MARKS, "")
      .replace(ARABIC_VARIANTS, (letter) => ARABIC_LETTERS[letter] ?? letter);
  }
  // Decomposed, an accented letter is its plain letter and a mark; only the plain letter stays.
  return text.toLowerCase().normalize("NFKD").replace(NOT_ASCII, "");
}

const isAbd = (part: string) => part === ABD || ABD_PREFIXES.has(part);

/** The name's parts, folded, with Abd joined to the attribute that follows it. */
function parts(name: string): string[] {
  // Marks go first: a short-vowel mark is not a letter, and would split its word in two.
  const text = name.normalize("NFKC").replace(ARABIC_MARKS, "");
  const tokens = (text.match(TOKEN) ?? [])
    .map(fold)
    .filter((token) => token !== "" && !LATIN_ARTICLES.has(token));
  const joined: string[] = [];
  for (const token of tokens) {
    const last = joined.at(-1);
    if (last !== undefined && isAbd(last)) joined[joined.length - 1] = fold(last + token);
    else joined.push(token);
  }
  return joined;
}

/** The searchable form: each part's listed Arabic form, or its own folded spelling. */
export function nameNormalised(name: string): string {
  return namePartsNormalised(name).join(" ");
}

/** A name's folded parts with each listed spelling as its name's Arabic form. */
export function namePartsNormalised(name: string): string[] {
  return parts(name).map((part) => SPELLINGS[part] ?? part);
}

/** Folded parts as typed, for matching a search against free text. */
export function foldedParts(text: string): string[] {
  return parts(text);
}

/** Free text folded word by word, for a search to find a folded word inside it. */
export function searchForm(text: string): string {
  return (text.normalize("NFKC").replace(ARABIC_MARKS, "").match(TOKEN) ?? []).map(fold).join(" ");
}

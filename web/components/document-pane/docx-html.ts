import DOMPurify from "dompurify";
import mammoth from "mammoth";

/**
 * A Word CV as HTML that is safe to show (T067, FR-012). A CV is written by someone outside the
 * company, so the conversion is cleaned to an allowlist: text structure, tables and embedded
 * pictures only. A link keeps its words and loses where it leads, so a crafted CV cannot send a
 * recruiter anywhere. Every block takes dir="auto", since one CV often mixes Arabic and English.
 * The CV's headings move down two levels, below the page's own h1 and h2, so moving by heading
 * through the page does not run from the page's outline into the CV's.
 * Runs in the browser: DOMPurify needs a DOM.
 */

const BLOCKS = "p, h1, h2, h3, h4, h5, h6, li, td, th";

const ALLOWED_TAGS = [
  ...["p", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li", "br"],
  ...["strong", "em", "b", "i", "u", "s", "sub", "sup"],
  ...["table", "thead", "tbody", "tr", "th", "td"],
  "img",
];
const ALLOWED_ATTR = ["src", "alt", "colspan", "rowspan"];

const HEADINGS = "h1, h2, h3, h4, h5, h6";
const HEADING_SHIFT = 2;

// Pictures come embedded in the file, as data: URIs, and only in the formats every browser shows
// safely; anything else, an SVG or a link to elsewhere included, is dropped. DOMPurify lets any
// data: URI through on an image, so this is checked after cleaning.
const SHOWN_PICTURE = /^data:image\/(?:png|jpeg|gif);base64,/i;

export interface DocxOptions {
  /** Said of a picture the CV does not describe itself, often a headshot. */
  pictureAlt: string;
}

export async function docxToSafeHtml(file: ArrayBuffer, options: DocxOptions): Promise<string> {
  const { value } = await mammoth.convertToHtml({ arrayBuffer: file });
  const fragment = DOMPurify.sanitize(value, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    RETURN_DOM_FRAGMENT: true,
  });
  for (const picture of fragment.querySelectorAll("img")) {
    if (!SHOWN_PICTURE.test(picture.getAttribute("src") ?? "")) {
      picture.remove();
    } else if (!picture.getAttribute("alt")?.trim()) {
      picture.setAttribute("alt", options.pictureAlt);
    }
  }
  for (const heading of fragment.querySelectorAll(HEADINGS)) {
    const level = Math.min(6, Number(heading.tagName.slice(1)) + HEADING_SHIFT);
    const lower = document.createElement(`h${String(level)}`);
    lower.append(...heading.childNodes);
    heading.replaceWith(lower);
  }
  for (const block of fragment.querySelectorAll(BLOCKS)) block.setAttribute("dir", "auto");
  const host = document.createElement("div");
  host.append(fragment);
  return host.innerHTML;
}

import DOMPurify from "dompurify";
import mammoth from "mammoth";

/**
 * A Word CV as HTML that is safe to show (T067, FR-012). A CV is written by someone outside the
 * company, so the conversion is cleaned to an allowlist: text structure, tables and embedded
 * pictures only. A link keeps its words and loses where it leads, so a crafted CV cannot send a
 * recruiter anywhere. Every block takes dir="auto", since one CV often mixes Arabic and English.
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

export async function docxToSafeHtml(file: ArrayBuffer): Promise<string> {
  const { value } = await mammoth.convertToHtml({ arrayBuffer: file });
  const fragment = DOMPurify.sanitize(value, {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    // Pictures come embedded in the file, as data: URIs; nothing is fetched from elsewhere.
    ALLOWED_URI_REGEXP: /^data:image\/(?:png|jpe?g|gif);base64,/i,
    RETURN_DOM_FRAGMENT: true,
  });
  for (const block of fragment.querySelectorAll(BLOCKS)) block.setAttribute("dir", "auto");
  const host = document.createElement("div");
  host.append(fragment);
  return host.innerHTML;
}

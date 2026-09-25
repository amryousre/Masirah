# Interface foundations: one token file, one component library, next-intl

Every screen is built from the same design tokens and the same components, so the design reaches
the whole product rather than being restyled page by page. DESIGN.md section 2 states the rule; this
records how the code carries it out and why these tools were chosen.

- **Tokens** are CSS custom properties in `web/app/globals.css`, the Claude Design handoff's values
  one for one. It is the only file allowed to write a color.
- **Components** live in `web/components/`, one folder each with its CSS module, built from the
  Components sheet with its states. Screens compose them and never restyle them.
- **Styling** is CSS Modules. Next.js supports them with no extra dependency, they keep each
  component's styles beside it, and they are plain CSS, so logical properties and the tokens need
  no translation layer.
- **Translation** uses next-intl. Messages are ICU, which covers Arabic's six plural forms
  ("ملف واحد", "ملفان", "3 ملفات", "11 ملفًا") that a hand-written lookup would get wrong. Its
  proxy does locale detection, and it reads the locale from the `[lang]` segment through
  `next/root-params`, as research.md planned.
- **Icons** are the sheet's own set, drawn in `components/icon`, not an icon library.
- **Lint enforces it.** `@eslint/css` rejects physical left and right, pixel font sizes and features
  that are not widely available; a local rule rejects color values outside the token file. In
  components and screens, text written into the markup, hard-coded accessible names, color strings
  and inline styles other than custom properties all fail the build.

## Considered and rejected

**Tailwind.** Its logical utilities (`ms-`, `pe-`) would satisfy the right-to-left rule. But the
tokens would then live in a second vocabulary of class names beside the CSS, and arbitrary values
such as `bg-[#fff]` would need their own guard. CSS Modules keep one vocabulary, the custom
properties, which the lint rules can check directly.

**A component library such as Radix or shadcn.** The design asks for native controls: native
selects, a native `<dialog>` that traps focus and restores it. So far there is nothing a
headless library would add that the platform does not already do. This is worth revisiting for the
first complex widget, such as a combobox with search.

**A custom translation lookup.** Fewer dependencies, but Arabic plurals, ICU arguments and locale
detection would each be rebuilt by hand, and none of them is where this product's value lies.

## Consequences

A new screen should need little CSS of its own: layout, and nothing a component already does.
A visual change is made once, in a token or a component, and every screen gets it.

The design page at `/ar/design` and `/en/design` shows every shared component in both languages.
It needs no sign-in, and the end-to-end suite runs the WCAG 2.1 AA checks against it. Since T024
the start of the app is the jobs list, behind sign-in.

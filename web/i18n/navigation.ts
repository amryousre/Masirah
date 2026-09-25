import { createNavigation } from "next-intl/navigation";

import { routing } from "./routing";

// Locale-aware replacements for next/link and next/navigation: links keep the current locale
// unless told otherwise, which is how the language switch changes it.
export const { Link, redirect, usePathname, useRouter, getPathname } = createNavigation(routing);

import type { ComponentProps, ReactNode } from "react";

import { Link } from "@/i18n/navigation";

import { cx } from "../cx";
import type { ButtonVariant } from "./button";
import styles from "./button.module.css";

interface ButtonLinkProps extends Omit<ComponentProps<typeof Link>, "children" | "className"> {
  /** Verb plus object, like a button: "Create job". */
  children: ReactNode;
  variant?: Exclude<ButtonVariant, "destructive" | "destructiveConfirm">;
}

/**
 * Navigation that looks like a button: the same 36px, radius and variants, but a link, so it
 * opens in a new tab and reads as a link to a screen reader. Destructive variants are left out:
 * nothing destructive happens by following a link.
 */
export function ButtonLink({ children, variant = "secondary", ...rest }: ButtonLinkProps) {
  return (
    <Link className={cx(styles.button, styles[variant])} {...rest}>
      <span className={styles.label}>{children}</span>
    </Link>
  );
}

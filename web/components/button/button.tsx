"use client";

import { type ButtonHTMLAttributes, type MouseEvent, type ReactNode, useId } from "react";
import { useFormStatus } from "react-dom";

import { cx } from "../cx";
import { Icon, type IconName } from "../icon/icon";
import styles from "./button.module.css";

export type ButtonVariant =
  | "primary"
  | "secondary"
  | "ghost"
  /** Outlined red at rest. Its label ends with an ellipsis because a confirmation follows. */
  | "destructive"
  /** The only filled red in the product: the confirm button inside a rejection dialog. */
  | "destructiveConfirm";

interface ButtonProps extends Omit<ButtonHTMLAttributes<HTMLButtonElement>, "children"> {
  /** Verb plus object: "Save job", "Reject candidate…". */
  children: ReactNode;
  variant?: ButtonVariant;
  icon?: IconName;
  loading?: boolean;
  /** The progress verb shown while loading: "Saving…". Kept in the button so its width holds. */
  loadingLabel?: string;
  /** What went wrong and what to do, shown beside the button. */
  error?: string | undefined;
}

export function Button({
  children,
  variant = "secondary",
  icon,
  loading = false,
  loadingLabel,
  error,
  type = "button",
  className,
  onClick,
  ...rest
}: ButtonProps) {
  const errorId = useId();

  // A loading button stays focusable, so keyboard users keep their place, but does nothing.
  const handleClick = (event: MouseEvent<HTMLButtonElement>) => {
    if (loading) {
      event.preventDefault();
      return;
    }
    onClick?.(event);
  };

  const button = (
    <button
      type={type}
      className={cx(styles.button, styles[variant], className)}
      aria-busy={loading || undefined}
      aria-disabled={loading || undefined}
      aria-describedby={error ? errorId : undefined}
      data-loading={loading || undefined}
      onClick={handleClick}
      {...rest}
    >
      <span className={styles.label} aria-hidden={loading || undefined}>
        {icon && <Icon name={icon} />}
        {children}
      </span>
      {loadingLabel !== undefined && (
        <span className={styles.progress} aria-hidden={!loading || undefined}>
          <Icon name="spinner" size={14} strokeWidth={2.5} />
          {loadingLabel}
        </span>
      )}
    </button>
  );

  if (!error) return button;
  return (
    <span className={styles.withError}>
      {button}
      <span id={errorId} role="alert" className={styles.error}>
        <Icon name="alert" size={12} strokeWidth={2.25} />
        {error}
      </span>
    </span>
  );
}

/**
 * The submit button of a form whose action runs on the server. It shows its progress verb from
 * the moment the form is sent until the action answers, so a slow network never looks idle and
 * a second press does nothing.
 */
export function SubmitButton(props: Omit<ButtonProps, "type" | "loading">) {
  const { pending } = useFormStatus();
  return <Button {...props} type="submit" loading={pending} />;
}

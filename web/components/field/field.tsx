"use client";

import { useTranslations } from "next-intl";
import {
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  useId,
  useState,
} from "react";

import { cx } from "../cx";
import { Icon } from "../icon/icon";
import styles from "./field.module.css";

interface FieldProps {
  label: string;
  /** Helper text below the control. An error or a loading message takes its place. */
  help?: string | undefined;
  /** What is wrong and what to do about it. Marks the control invalid. */
  error?: string | undefined;
  /** What the field is doing while it waits: "Checking for a job with the same name…". */
  loading?: string | undefined;
  /** A value the system proposed, marked until someone saves it. */
  suggested?: boolean;
}

interface FrameProps extends FieldProps {
  id: string;
  children: ReactNode;
}

// The "Suggested" tag sits beside the label rather than inside it, so it is read as a description
// after the field's name instead of being run into the name as one word.
const tagIdOf = (id: string) => `${id}-suggested`;
const messageIdOf = (id: string) => `${id}-message`;

function FieldFrame({ id, label, help, error, loading, suggested, children }: FrameProps) {
  const t = useTranslations("field");
  const message = error ?? loading ?? help;
  return (
    <div className={styles.field}>
      <div className={styles.labelRow}>
        <label htmlFor={id} className={styles.label}>
          {label}
        </label>
        {suggested && (
          <span id={tagIdOf(id)} className={styles.tag}>
            {t("suggested")}
          </span>
        )}
      </div>
      <div className={styles.control}>{children}</div>
      {message !== undefined && (
        <p id={messageIdOf(id)} className={cx(styles.message, error !== undefined && styles.error)}>
          {error !== undefined && <Icon name="alert" size={12} strokeWidth={2.25} />}
          {message}
        </p>
      )}
    </div>
  );
}

function controlProps(props: FieldProps, id: string) {
  const { help, error, loading, suggested } = props;
  const hasMessage = error !== undefined || loading !== undefined || help !== undefined;
  const describedBy = [suggested && tagIdOf(id), hasMessage && messageIdOf(id)].filter(Boolean);
  return {
    id,
    "aria-invalid": error !== undefined || undefined,
    "aria-busy": loading !== undefined || undefined,
    "aria-describedby": describedBy.length > 0 ? describedBy.join(" ") : undefined,
    "data-suggested": suggested || undefined,
  };
}

type TextFieldProps = FieldProps & Omit<InputHTMLAttributes<HTMLInputElement>, "id">;

export function TextField({
  label,
  help,
  error,
  loading,
  suggested,
  className,
  ...input
}: TextFieldProps) {
  const id = useId();
  const field = { label, help, error, loading, suggested: suggested ?? false };
  return (
    <FieldFrame id={id} {...field}>
      <input className={cx(styles.input, className)} {...controlProps(field, id)} {...input} />
      {loading !== undefined && <Icon name="spinner" size={14} className={styles.adornment} />}
    </FieldFrame>
  );
}

export interface SelectOption {
  value: string;
  label: string;
}

type SelectFieldProps = FieldProps &
  Omit<SelectHTMLAttributes<HTMLSelectElement>, "id" | "children"> & {
    options: readonly SelectOption[];
    /** Shown until something is chosen. Defaults to "Choose…". */
    placeholder?: string;
  };

export function SelectField({
  label,
  help,
  error,
  loading,
  suggested,
  options,
  placeholder,
  className,
  ...select
}: SelectFieldProps) {
  const t = useTranslations("field");
  const id = useId();
  const field = { label, help, error, loading, suggested: suggested ?? false };
  return (
    <FieldFrame id={id} {...field}>
      <select
        className={cx(styles.input, styles.select, className)}
        {...controlProps(field, id)}
        {...select}
      >
        <option value="" disabled>
          {placeholder ?? t("choose")}
        </option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <Icon
        name={loading !== undefined ? "spinner" : "chevronDown"}
        size={16}
        strokeWidth={1.75}
        className={styles.adornment}
      />
    </FieldFrame>
  );
}

type PasswordFieldProps = FieldProps & Omit<InputHTMLAttributes<HTMLInputElement>, "id" | "type">;

/**
 * A password with a button that shows it, so a long password typed on a phone can be checked
 * before sending. The button keeps one name and reports its state through aria-pressed.
 */
export function PasswordField({
  label,
  help,
  error,
  loading,
  suggested,
  className,
  ...input
}: PasswordFieldProps) {
  const t = useTranslations("field");
  const id = useId();
  const [visible, setVisible] = useState(false);
  const field = { label, help, error, loading, suggested: suggested ?? false };
  return (
    <FieldFrame id={id} {...field}>
      <input
        type={visible ? "text" : "password"}
        className={cx(styles.input, styles.withToggle, className)}
        {...controlProps(field, id)}
        {...input}
      />
      <button
        type="button"
        className={styles.toggle}
        aria-label={t("showPassword")}
        aria-pressed={visible}
        aria-controls={id}
        onClick={() => {
          setVisible((shown) => !shown);
        }}
      >
        <Icon name={visible ? "eyeOff" : "eye"} size={16} strokeWidth={1.75} />
      </button>
    </FieldFrame>
  );
}

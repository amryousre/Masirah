"use client";

import { useTranslations } from "next-intl";
import { type KeyboardEvent, useId, useState } from "react";

import { Icon } from "../icon/icon";
import styles from "./skills-field.module.css";

interface SkillsFieldProps {
  label: string;
  /** Each skill is submitted as its own value under this name. */
  name: string;
  help?: string | undefined;
  error?: string | undefined;
  defaultValue?: readonly string[];
  /** Skills the system proposed, marked until someone saves them. */
  suggested?: boolean;
}

// Enter, a comma or an Arabic comma ends a skill.
const SEPARATORS = new Set(["Enter", ",", "،"]);

/**
 * A list of skills, one chip each. Enter or a comma adds what was typed; each chip has its own
 * remove button, so the list is editable by keyboard alone. The chips are submitted as repeated
 * form values, and the server decides what is kept (lib/domain/job-draft.ts).
 */
export function SkillsField({
  label,
  name,
  help,
  error,
  defaultValue = [],
  suggested = false,
}: SkillsFieldProps) {
  const t = useTranslations("field");
  const id = useId();
  const messageId = `${id}-message`;
  const [skills, setSkills] = useState<string[]>([...defaultValue]);
  const [typed, setTyped] = useState("");

  const add = () => {
    const skill = typed.trim();
    const known = skills.some((s) => s.toLocaleLowerCase() === skill.toLocaleLowerCase());
    if (skill !== "" && !known) setSkills([...skills, skill]);
    setTyped("");
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (SEPARATORS.has(event.key)) {
      event.preventDefault();
      add();
    } else if (event.key === "Backspace" && typed === "" && skills.length > 0) {
      setSkills(skills.slice(0, -1));
    }
  };

  const message = error ?? help;
  return (
    <div className={styles.field}>
      <div className={styles.labelRow}>
        <label htmlFor={id} className={styles.label}>
          {label}
        </label>
        {suggested && <span className={styles.tag}>{t("suggested")}</span>}
      </div>
      <div
        className={styles.box}
        data-suggested={suggested || undefined}
        data-invalid={error !== undefined || undefined}
      >
        {skills.length > 0 && (
          <ul className={styles.chips} aria-label={label}>
            {skills.map((skill) => (
              <li key={skill} className={styles.chip}>
                <bdi>{skill}</bdi>
                <input type="hidden" name={name} value={skill} />
                <button
                  type="button"
                  className={styles.remove}
                  aria-label={t("removeSkill", { skill })}
                  onClick={() => {
                    setSkills(skills.filter((s) => s !== skill));
                  }}
                >
                  <Icon name="close" size={12} strokeWidth={2} />
                </button>
              </li>
            ))}
          </ul>
        )}
        <input
          id={id}
          className={styles.input}
          value={typed}
          placeholder={t("addSkill")}
          aria-invalid={error !== undefined || undefined}
          aria-describedby={message !== undefined ? messageId : undefined}
          onChange={(event) => {
            setTyped(event.target.value);
          }}
          onKeyDown={onKeyDown}
          onBlur={add}
        />
      </div>
      {message !== undefined && (
        <p id={messageId} className={styles.message} data-error={error !== undefined || undefined}>
          {message}
        </p>
      )}
    </div>
  );
}

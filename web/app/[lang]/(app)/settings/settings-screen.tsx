"use client";

import { useLocale, useTranslations } from "next-intl";
import { type ReactNode, useEffect, useId, useRef, useState, useTransition } from "react";

import { Button } from "@/components/button/button";
import { DeleteCandidateData } from "@/components/delete-candidate-data/delete-candidate-data";
import { SelectField, TextField } from "@/components/field/field";
import { useRouter } from "@/i18n/navigation";
import { type Locale, routing } from "@/i18n/routing";
import type { CandidateMatch } from "@/lib/adapters/settings";
import { RETENTION_CHOICES } from "@/lib/domain/settings";

import { lookUpCandidates, saveRetention } from "./actions";
import styles from "./settings.module.css";

/** Waits for the typing to pause before looking candidates up. */
const LOOKUP_DELAY_MS = 300;

function Row({ title, help, children }: { title: string; help: string; children: ReactNode }) {
  const headingId = useId();
  return (
    <section className={styles.row} aria-labelledby={headingId}>
      <div className={styles.about}>
        <h2 id={headingId} className={styles.rowTitle}>
          {title}
        </h2>
        <p className={styles.help}>{help}</p>
      </div>
      <div className={styles.control}>{children}</div>
    </section>
  );
}

/** The three settings of the design: language, retention, and deleting a candidate's data. */
export function SettingsScreen({ retention }: { retention: number | null }) {
  const t = useTranslations("settings");
  return (
    <div className={styles.rows}>
      <Row title={t("language.title")} help={t("language.help")}>
        <LanguageChoice />
      </Row>
      <Row title={t("retention.title")} help={t("retention.help")}>
        <RetentionChoice saved={retention === null ? "never" : String(retention)} />
      </Row>
      <Row title={t("deletion.title")} help={t("deletion.help")}>
        <CandidateDeletion />
      </Row>
    </div>
  );
}

/** For the member's own account: the page opens again in the chosen language. */
function LanguageChoice() {
  const t = useTranslations("settings.language");
  const locale = useLocale();
  const router = useRouter();
  const name = useId();
  return (
    <fieldset className={styles.choices}>
      <legend className={styles.hidden}>{t("title")}</legend>
      {routing.locales.map((option: Locale) => (
        <label
          key={option}
          className={styles.choice}
          data-selected={option === locale || undefined}
        >
          <input
            type="radio"
            name={name}
            value={option}
            checked={option === locale}
            onChange={() => {
              router.replace("/settings", { locale: option });
            }}
          />
          <span lang={option}>{t(`names.${option}`)}</span>
        </label>
      ))}
    </fieldset>
  );
}

function RetentionChoice({ saved }: { saved: string }) {
  const t = useTranslations("settings.retention");
  const [choice, setChoice] = useState(saved);
  const [pending, startSaving] = useTransition();
  const [outcome, setOutcome] = useState<
    { kind: "saved"; months: number | null; affected: number } | { kind: "failed" } | null
  >(null);

  return (
    <form
      className={styles.stack}
      onSubmit={(event) => {
        event.preventDefault();
        startSaving(async () => {
          const result = await saveRetention(choice);
          setOutcome(result.ok ? { kind: "saved", ...result } : { kind: "failed" });
        });
      }}
    >
      <SelectField
        wide
        label={t("label")}
        value={choice}
        options={RETENTION_CHOICES.map((value) => ({
          value,
          label: value === "never" ? t("never") : t("months", { months: Number(value) }),
        }))}
        onChange={(event) => {
          setChoice(event.target.value);
          setOutcome(null);
        }}
      />
      <p className={styles.help}>
        {choice === "never" ? t("keptUntilDeleted") : t("rule", { months: Number(choice) })}
      </p>
      <div>
        <Button type="submit" variant="secondary" loading={pending} loadingLabel={t("saving")}>
          {t("save")}
        </Button>
      </div>
      <div role="status" className={styles.status}>
        {outcome?.kind === "saved" && (
          <>
            <p>{t("saved")}</p>
            {outcome.months !== null && outcome.affected > 0 && (
              <p>{t("dueSoon", { count: outcome.affected, months: outcome.months })}</p>
            )}
            <p>{t("nobodyNow")}</p>
          </>
        )}
      </div>
      {outcome?.kind === "failed" && (
        <p role="alert" className={styles.failed}>
          {t("failed")}
        </p>
      )}
    </form>
  );
}

function CandidateDeletion() {
  const t = useTranslations("settings.deletion");
  const locale = useLocale();
  const [query, setQuery] = useState("");
  const [matches, setMatches] = useState<CandidateMatch[]>([]);
  const [chosen, setChosen] = useState<CandidateMatch | null>(null);
  const [requested, setRequested] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const [, startLookup] = useTransition();
  // Each lookup is numbered; an older one that answers late is ignored, so the list always
  // matches what is in the box and nobody is picked from stale results.
  const latest = useRef(0);

  useEffect(() => {
    const timer = setTimeout(() => {
      const ticket = ++latest.current;
      startLookup(async () => {
        const found = await lookUpCandidates(query);
        if (ticket === latest.current) setMatches(found);
      });
    }, LOOKUP_DELAY_MS);
    return () => {
      clearTimeout(timer);
    };
  }, [query]);

  const day = new Intl.DateTimeFormat(locale, { dateStyle: "medium" });
  const nameOf = (match: CandidateMatch) =>
    match.name ?? match.email ?? match.phone ?? t("unnamed");

  const remove = async (match: CandidateMatch): Promise<boolean> => {
    setFailed(false);
    try {
      const response = await fetch(`/api/candidates/${match.id}`, { method: "DELETE" });
      if (!response.ok) {
        setFailed(true);
        return false;
      }
      setRequested(nameOf(match));
      setChosen(null);
      setMatches((current) => current.filter((candidate) => candidate.id !== match.id));
      return true;
    } catch {
      setFailed(true);
      return false;
    }
  };

  return (
    <div className={styles.stack}>
      <TextField
        wide
        label={t("search")}
        type="search"
        value={query}
        autoComplete="off"
        onChange={(event) => {
          setQuery(event.target.value);
          setChosen(null);
          setRequested(null);
        }}
      />
      {matches.length > 0 && chosen === null && (
        <ul className={styles.matches} aria-label={t("matches")}>
          {matches.map((match) => (
            <li key={match.id}>
              <button
                type="button"
                className={styles.match}
                onClick={() => {
                  setChosen(match);
                }}
              >
                <bdi className={styles.matchName}>{nameOf(match)}</bdi>
                <span className={styles.matchMeta}>
                  {t("meta", { jobs: match.jobs, when: day.format(new Date(match.lastActive)) })}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
      {query.trim().length >= 2 &&
        matches.length === 0 &&
        chosen === null &&
        requested === null && <p className={styles.help}>{t("noMatch")}</p>}
      {chosen !== null && (
        <>
          <div className={styles.chosen}>
            <bdi className={styles.matchName}>{nameOf(chosen)}</bdi>
            <span className={styles.matchMeta}>
              {t("meta", { jobs: chosen.jobs, when: day.format(new Date(chosen.lastActive)) })}
            </span>
          </div>
          <DeleteCandidateData
            candidate={nameOf(chosen)}
            onDelete={() => remove(chosen)}
            error={failed ? t("failed") : undefined}
          />
        </>
      )}
      <p role="status" className={styles.status}>
        {requested !== null && t("requested", { name: requested })}
      </p>
    </div>
  );
}

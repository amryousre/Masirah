"use client";

import { useTranslations } from "next-intl";
import { useId } from "react";

import { SelectField, TextField } from "../field/field";
import styles from "./candidate-filters.module.css";

export type DecisionFilter = "all" | "undecided" | "shortlisted" | "rejected";
export type SortChoice = "score" | "name" | "recent";

export interface FilterValues {
  query: string;
  decision: DecisionFilter;
  reviewOnly: boolean;
  sort: SortChoice;
}

interface CandidateFiltersProps {
  values: FilterValues;
  onChange: (values: FilterValues) => void;
  /** How many candidates the filters keep, and how many there are. */
  shown: number;
  total: number;
}

/**
 * Search, filter and sort above the ranked list (T069). Search reads names in either script and
 * the extracted fields; the count below says how many of the list are showing, and is announced
 * politely as it changes.
 */
export function CandidateFilters({ values, onChange, shown, total }: CandidateFiltersProps) {
  const t = useTranslations("filters");
  const reviewId = useId();
  const set = (changes: Partial<FilterValues>) => {
    onChange({ ...values, ...changes });
  };

  return (
    <search className={styles.filters} aria-label={t("label")}>
      <div className={styles.query}>
        <TextField
          label={t("search")}
          type="search"
          value={values.query}
          placeholder={t("searchHint")}
          autoComplete="off"
          onChange={(event) => {
            set({ query: event.target.value });
          }}
        />
      </div>
      <SelectField
        label={t("decision")}
        value={values.decision}
        options={(["all", "undecided", "shortlisted", "rejected"] as const).map((value) => ({
          value,
          label: t(`decisions.${value}`),
        }))}
        onChange={(event) => {
          set({ decision: event.target.value as DecisionFilter });
        }}
      />
      <SelectField
        label={t("sort")}
        value={values.sort}
        options={(["score", "name", "recent"] as const).map((value) => ({
          value,
          label: t(`sorts.${value}`),
        }))}
        onChange={(event) => {
          set({ sort: event.target.value as SortChoice });
        }}
      />
      <div className={styles.check}>
        <input
          id={reviewId}
          type="checkbox"
          checked={values.reviewOnly}
          onChange={(event) => {
            set({ reviewOnly: event.target.checked });
          }}
        />
        <label htmlFor={reviewId}>{t("reviewOnly")}</label>
      </div>
      <p role="status" className={styles.count}>
        {t("shown", { shown, total })}
      </p>
    </search>
  );
}

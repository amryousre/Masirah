"use client";

import { useLocale } from "next-intl";
import { type KeyboardEvent, type ReactNode, useId, useRef } from "react";

import { direction } from "@/i18n/routing";

import { Icon } from "../icon/icon";
import styles from "./tabs.module.css";

export interface TabItem {
  id: string;
  label: string;
  count?: number;
  disabled?: boolean;
  loading?: boolean;
  /** Why the tab's content could not load. */
  error?: string;
}

interface TabsProps {
  /** Names the set of tabs for assistive technology: "Job sections". */
  label: string;
  items: readonly TabItem[];
  selected: string;
  onSelect: (id: string) => void;
  /** The selected tab's content. */
  children: ReactNode;
}

/**
 * The selected tab is marked by weight and a 2px ink underline, never by amber, which stays free
 * for actions. Arrow keys follow the reading direction: in Arabic the left arrow moves forward.
 */
export function Tabs({ label, items, selected, onSelect, children }: TabsProps) {
  const rtl = direction(useLocale()) === "rtl";
  const baseId = useId();
  const tabs = useRef(new Map<string, HTMLButtonElement>());
  const tabId = (id: string) => `${baseId}-tab-${id}`;
  const panelId = `${baseId}-panel`;
  const enabled = items.filter((item) => !item.disabled);

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>, current: string) => {
    const index = enabled.findIndex((item) => item.id === current);
    const forward = rtl ? "ArrowLeft" : "ArrowRight";
    const backward = rtl ? "ArrowRight" : "ArrowLeft";
    const targets: Record<string, number> = {
      [forward]: (index + 1) % enabled.length,
      [backward]: (index - 1 + enabled.length) % enabled.length,
      Home: 0,
      End: enabled.length - 1,
    };
    const next = event.key in targets ? enabled[targets[event.key] ?? index] : undefined;
    if (!next) return;
    event.preventDefault();
    onSelect(next.id);
    tabs.current.get(next.id)?.focus();
  };

  return (
    <div className={styles.tabs}>
      <div role="tablist" aria-label={label} className={styles.list}>
        {items.map((item) => {
          const isSelected = item.id === selected;
          const errorId = `${tabId(item.id)}-error`;
          return (
            <button
              key={item.id}
              ref={(node) => {
                if (node) tabs.current.set(item.id, node);
                else tabs.current.delete(item.id);
              }}
              id={tabId(item.id)}
              type="button"
              role="tab"
              aria-selected={isSelected}
              aria-controls={isSelected ? panelId : undefined}
              aria-busy={item.loading || undefined}
              aria-describedby={item.error ? errorId : undefined}
              tabIndex={isSelected ? 0 : -1}
              disabled={item.disabled}
              className={styles.tab}
              onClick={() => {
                onSelect(item.id);
              }}
              onKeyDown={(event) => {
                onKeyDown(event, item.id);
              }}
            >
              <span className={styles.name}>{item.label}</span>
              {item.count !== undefined && <span className={styles.count}>{item.count}</span>}
              {item.loading && <Icon name="spinner" size={12} strokeWidth={2.5} />}
              {item.error && (
                <>
                  <Icon name="alert" size={13} strokeWidth={2.25} className={styles.error} />
                  <span id={errorId} hidden>
                    {item.error}
                  </span>
                </>
              )}
            </button>
          );
        })}
      </div>
      <div
        role="tabpanel"
        id={panelId}
        aria-labelledby={tabId(selected)}
        tabIndex={0}
        className={styles.panel}
      >
        {children}
      </div>
    </div>
  );
}

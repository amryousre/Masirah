import { cx } from "../cx";
import styles from "./icon.module.css";

// The icon set drawn in the Components sheet: a 24-unit grid, stroke only, round ends. Icons sit
// beside words and are hidden from assistive technology unless given a label of their own.
const circle = "M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z";
const globeLines = "M3 12h18M12 3c3 3.5 3 14.5 0 18M12 3c-3 3.5-3 14.5 0 18";
const eyeShape =
  "M2.5 12S6 5.5 12 5.5 21.5 12 21.5 12 18 18.5 12 18.5 2.5 12 2.5 12ZM12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z";

const paths = {
  alert: `${circle}M12 7.5v5M12 16v.01`,
  at: "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8ZM16 12v1.5a2.5 2.5 0 0 0 5 0V12a9 9 0 1 0-3.5 7.1",
  check: "M5 12.5l4.5 4.5L19 7.5",
  checkCircle: `${circle}M8 12.5l2.5 2.5L16 9.5`,
  chevronDown: "m6 9 6 6 6-6",
  // Drawn for left to right; a page mirrors them in Arabic.
  chevronLeft: "m15 18-6-6 6-6",
  chevronRight: "m9 18 6-6-6-6",
  chevronsUpDown: "m7 15 5 5 5-5M7 9l5-5 5 5",
  clock: `${circle}M12 7v5l3 2`,
  close: "M6 6l12 12M18 6 6 18",
  dot: "M12 9a3 3 0 1 0 0 6 3 3 0 0 0 0-6Z",
  eye: eyeShape,
  eyeOff: `${eyeShape}M4 4l16 16`,
  gauge: `${circle}M12 12l4-4`,
  globe: `${circle}${globeLines}`,
  globeOff: `${circle}${globeLines}M4 4l16 16`,
  layers: "M12 3 3 8l9 5 9-5-9-5ZM3 13l9 5 9-5",
  minusCircle: `${circle}M8 12h8`,
  pauseCircle: `${circle}M9 9v6M15 9v6`,
  queued: circle,
  sortDown: "M12 5v14M6 13l6 6 6-6",
  upload: "M12 15V4M7 9l5-5 5 5M4 15v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3",
  xCircle: `${circle}M9 9l6 6M15 9l-6 6`,
} as const;

export type IconName = keyof typeof paths | "spinner";

interface IconProps {
  name: IconName;
  /** Rendered size in pixels. The sheet uses 12 to 20. */
  size?: number;
  strokeWidth?: number;
  /** Only for an icon that stands alone; beside words, leave it out. */
  label?: string | undefined;
  className?: string | undefined;
}

export function Icon({ name, size = 16, strokeWidth = 2, label, className }: IconProps) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      fill="none"
      stroke="currentColor"
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      focusable="false"
      className={cx(styles.icon, name === "spinner" && styles.spinner, className)}
      role={label === undefined ? undefined : "img"}
      aria-label={label}
      aria-hidden={label === undefined ? true : undefined}
    >
      {name === "spinner" ? (
        <>
          <circle cx="12" cy="12" r="9" className={styles.track} />
          <path d="M21 12a9 9 0 0 0-9-9" />
        </>
      ) : (
        <path d={paths[name]} className={name === "queued" ? styles.dashed : undefined} />
      )}
    </svg>
  );
}

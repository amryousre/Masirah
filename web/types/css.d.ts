import "react";

// Inline styles may only set custom properties (DESIGN.md section 2, enforced by lint), such as
// the score bar's --fill. React's style type has no entry for them, so this adds one.
declare module "react" {
  interface CSSProperties {
    [property: `--${string}`]: string | number | undefined;
  }
}

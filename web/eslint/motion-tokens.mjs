// DESIGN.md motion and T108: every transition and animation takes 150 to 250 ms, and none at all
// for reduced motion. Both hold by construction when every motion takes a duration token from
// app/globals.css, which defines them in that range and sets them to zero under
// prefers-reduced-motion. This rule reports what would break that, on any selector, pseudo-elements
// included: a time written out, a delay (the stuff of staggered load sequences), and an animation
// that runs more than once. The spinner, which turns until the work is done, opts out with a
// disable comment that says so.

const MOTION = new Set([
  "transition", "transition-duration", "transition-delay",
  "animation", "animation-duration", "animation-delay", "animation-iteration-count",
]); // prettier-ignore

const TIME_UNITS = new Set(["s", "ms"]);

/** The value's top-level parts, split at its commas: one item per transition or animation. */
function items(value) {
  const groups = [[]];
  for (const part of value.children ?? []) {
    if (part.type === "Operator" && part.value === ",") groups.push([]);
    else groups.at(-1).push(part);
  }
  return groups;
}

const isDurationToken = (part) =>
  part.type === "Function" &&
  part.name === "var" &&
  part.children?.some(
    (child) => child.type === "Identifier" && child.name.startsWith("--duration-"),
  );

const isTime = (part) => part.type === "Dimension" && TIME_UNITS.has(part.unit.toLowerCase());

/** @type {import("eslint").Rule.RuleModule} */
const motionTokens = {
  meta: {
    type: "problem",
    docs: { description: "Motion takes the duration tokens, with no delays and no repeats" },
    messages: {
      raw: "Use a --duration-* token from app/globals.css instead of {{value}} (T108).",
      delay: "Motion starts at once: no delays, which stagger a sequence (T108).",
      repeat: "An animation runs once; only the spinner may turn until work is done (T108).",
    },
    schema: [],
  },
  create(context) {
    return {
      Declaration(node) {
        const property = node.property.toLowerCase();
        if (!MOTION.has(property) || node.value?.type !== "Value") return;
        const report = (messageId, data = {}) => context.report({ node, messageId, data });
        for (const item of items(node.value)) {
          for (const part of item) {
            if (isTime(part) && Number(part.value) !== 0) {
              report("raw", { value: `${part.value}${part.unit}` });
            }
          }
          const times = item.filter((part) => isTime(part) || isDurationToken(part));
          const delayed =
            property.endsWith("-delay")
              ? times.some((part) => !(isTime(part) && Number(part.value) === 0))
              : property === "transition" || property === "animation"
                ? times.length > 1
                : false;
          if (delayed) report("delay");
          const repeats =
            property === "animation-iteration-count" || property === "animation"
              ? item.some(
                  (part) =>
                    (part.type === "Identifier" && part.name.toLowerCase() === "infinite") ||
                    (part.type === "Number" && Number(part.value) !== 1),
                )
              : false;
          if (repeats) report("repeat");
        }
      },
    };
  },
};

export default motionTokens;

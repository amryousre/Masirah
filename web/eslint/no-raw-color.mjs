// DESIGN.md section 2: colors come from the tokens in app/globals.css and nowhere else. This rule
// runs on CSS files through @eslint/css and reports any color written out in full: a hex value, a
// color function such as oklch() or rgb(), or a named color. `transparent` and `currentColor` are
// not colors in this sense, and var(--token) is how every other file should say it.

const COLOR_FUNCTIONS = new Set([
  "rgb", "rgba", "hsl", "hsla", "hwb", "lab", "lch", "oklab", "oklch", "color",
]); // prettier-ignore

// CSS Color Module Level 4 named colors.
const NAMED_COLORS = new Set(
  (
    "aliceblue antiquewhite aqua aquamarine azure beige bisque black blanchedalmond blue " +
    "blueviolet brown burlywood cadetblue chartreuse chocolate coral cornflowerblue cornsilk " +
    "crimson cyan darkblue darkcyan darkgoldenrod darkgray darkgreen darkgrey darkkhaki " +
    "darkmagenta darkolivegreen darkorange darkorchid darkred darksalmon darkseagreen " +
    "darkslateblue darkslategray darkslategrey darkturquoise darkviolet deeppink deepskyblue " +
    "dimgray dimgrey dodgerblue firebrick floralwhite forestgreen fuchsia gainsboro ghostwhite " +
    "gold goldenrod gray green greenyellow grey honeydew hotpink indianred indigo ivory khaki " +
    "lavender lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan " +
    "lightgoldenrodyellow lightgray lightgreen lightgrey lightpink lightsalmon lightseagreen " +
    "lightskyblue lightslategray lightslategrey lightsteelblue lightyellow lime limegreen linen " +
    "magenta maroon mediumaquamarine mediumblue mediumorchid mediumpurple mediumseagreen " +
    "mediumslateblue mediumspringgreen mediumturquoise mediumvioletred midnightblue mintcream " +
    "mistyrose moccasin navajowhite navy oldlace olive olivedrab orange orangered orchid " +
    "palegoldenrod palegreen paleturquoise palevioletred papayawhip peachpuff peru pink plum " +
    "powderblue purple rebeccapurple red rosybrown royalblue saddlebrown salmon sandybrown " +
    "seagreen seashell sienna silver skyblue slateblue slategray slategrey snow springgreen " +
    "steelblue tan teal thistle tomato turquoise violet wheat white whitesmoke yellow " +
    "yellowgreen"
  ).split(" "),
);

/** @type {import("eslint").Rule.RuleModule} */
const noRawColor = {
  meta: {
    type: "problem",
    docs: { description: "Disallow color values outside the design token file" },
    messages: {
      raw: "Use a color token from app/globals.css instead of {{value}} (DESIGN.md section 2).",
    },
    schema: [],
  },
  create(context) {
    const report = (node, value) => {
      context.report({ node, messageId: "raw", data: { value } });
    };
    return {
      Hash(node) {
        report(node, `#${node.value}`);
      },
      Function(node) {
        if (COLOR_FUNCTIONS.has(node.name.toLowerCase())) report(node, `${node.name}()`);
      },
      Identifier(node) {
        if (NAMED_COLORS.has(node.name.toLowerCase())) report(node, node.name);
      },
    };
  },
};

const plugin = {
  meta: { name: "masirah" },
  rules: { "no-raw-color": noRawColor },
};

export default plugin;

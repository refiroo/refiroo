// Runs before the first paint (a blocking script, so the page never flashes the wrong theme). It is a file of
// its own, not an inline script, so the application's Content-Security-Policy needs no 'unsafe-inline' for
// scripts (0.17 RF4).
// Apply a saved light/dark choice before the first paint; see src/lib/theme.ts.
try {
  const theme = JSON.parse(localStorage.getItem("rdm:theme:v1") || '"system"');
  if (theme === "light" || theme === "dark") document.documentElement.dataset.theme = theme;
} catch {
  // Storage may be unavailable; the system theme applies.
}
// The theme likewise (Normal sets nothing; another sets data-scheme, and data-frame when its frame is not the top
// bar and sidebar); see src/lib/scheme.ts, whose tables these repeat.
try {
  const scheme = JSON.parse(localStorage.getItem("rdm:scheme:v1") || '"normal"');
  const themes = {
    purple: { light: "#fbf8f1", dark: "#0e1130" },
    hearth: { light: "#f6f2ec", dark: "#181613" },
    studio: { light: "#efeaf6", dark: "#100f16", frame: "sheet" },
    instrument: { light: "#fbfaf8", dark: "#111113", frame: "rail" },
  };
  const chosen = Object.prototype.hasOwnProperty.call(themes, scheme) ? themes[scheme] : null;
  if (chosen) {
    document.documentElement.dataset.scheme = scheme;
    if (chosen.frame) document.documentElement.dataset.frame = chosen.frame;
    for (const mode of ["light", "dark"])
      document
        .querySelector('meta[name="theme-color"][media="(prefers-color-scheme: ' + mode + ')"]')
        .setAttribute("content", chosen[mode]);
  }
} catch {
  // Storage may be unavailable; Normal applies.
}
// The type palette likewise; see src/lib/palette.ts. B, the default, needs no attribute.
try {
  if (JSON.parse(localStorage.getItem("rdm:palette:v1") || '"b"') === "a")
    document.documentElement.dataset.palette = "a";
} catch {
  // Storage may be unavailable; palette B applies.
}

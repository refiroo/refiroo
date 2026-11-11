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
// The colour theme likewise (Normal sets nothing; Website purple sets data-scheme); see src/lib/scheme.ts.
try {
  if (JSON.parse(localStorage.getItem("rdm:scheme:v1") || '"normal"') === "purple") {
    document.documentElement.dataset.scheme = "purple";
    const colours = { light: "#fbf8f1", dark: "#0e1130" };
    for (const mode in colours)
      document
        .querySelector('meta[name="theme-color"][media="(prefers-color-scheme: ' + mode + ')"]')
        .setAttribute("content", colours[mode]);
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

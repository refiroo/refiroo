// Switching a page to the dark theme and knowing it has taken effect (no fixed wait).

/** Animations and transitions that end (an infinite one is a spinner, which never finishes). */
export const settled = (page) =>
  page.evaluate(() =>
    Promise.all(
      document
        .getAnimations()
        .filter((animation) => animation.effect?.getComputedTiming().iterations !== Infinity)
        .map((animation) => animation.finished.catch(() => undefined)),
    ),
  );

/** Dark from the device and from the page's own switch; resolves once the page's background has changed and settled. */
export async function goDark(page) {
  const before = await page.evaluate(() => getComputedStyle(document.body).backgroundColor);
  await page.emulateMedia({ colorScheme: "dark" });
  await page.evaluate(() => (document.documentElement.dataset.theme = "dark"));
  await page.waitForFunction((light) => getComputedStyle(document.body).backgroundColor !== light, before);
  await settled(page);
}

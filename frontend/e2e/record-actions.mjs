// A visible, keyboard-accessible trigger for the same actions available on right-click.
export async function recordAction(page, label) {
  await page.getByRole("button", { name: "Record actions", exact: true }).click();
  await page.getByRole("menuitem", { name: label, exact: true }).click();
}

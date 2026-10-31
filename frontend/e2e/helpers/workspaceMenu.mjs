// The workspace ⋯ menu beside the workspace selector (0.16 WM1): Import…, Export… and Edit model.
export async function workspaceAction(page, name, { keyboard = false } = {}) {
  const trigger = page.getByRole("button", { name: "Workspace actions" });
  // On a phone it stands in the band's workspace choice.
  const choice = page.getByRole("button", { name: /^Workspace: / });
  if (await choice.isVisible().catch(() => false)) {
    if (!(await trigger.isVisible().catch(() => false))) await choice.click();
    await trigger.waitFor();
  }
  if (keyboard) {
    await trigger.focus();
    await page.keyboard.press("Enter");
    const item = page.getByRole("menuitem", { name });
    await item.waitFor();
    await item.focus();
    await page.keyboard.press("Enter");
    return;
  }
  await trigger.click();
  await page.getByRole("menuitem", { name }).click();
}

// Operations on the continuous lists of Base 0.8 S5 (ui/ScrollWindow, ui/ObjectLookup).

/** Jumps a list to a page number with its footer field; `scope` contains exactly one list. */
export async function goToPage(scope, number) {
  const field = scope.getByRole("spinbutton", { name: "Page", exact: true });
  await field.fill(String(number));
  await field.press("Enter");
}

/** Chooses an object in a picker by its ID; the option must be among the loaded results. */
export async function chooseObject(scope, objectId) {
  await scope.locator(`[role="option"][id$="-option-${objectId}"]`).click();
}

/** Scrolls `region` with the wheel until `target` is present, as a user scrolling on would. */
export async function scrollUntil(page, region, target, { step = 400, limit = 60 } = {}) {
  await region.scrollIntoViewIfNeeded();
  const box = await region.boundingBox();
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2);
  for (let attempt = 0; attempt < limit && (await target.count()) === 0; attempt++) {
    await page.mouse.wheel(0, step);
    await page.waitForTimeout(120);
  }
  await target.first().waitFor();
}

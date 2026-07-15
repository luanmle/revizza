import { expect, test } from "@playwright/test";

test("ordenação atualiza URL, request e reinicia cursor", async ({ page }) => {
  const requests: URL[] = [];
  await page.route("**/api/v1/decks/**", async (route) => {
    requests.push(new URL(route.request().url()));
    await route.fulfill({
      status: 200,
      json: { next: null, previous: null, results: [] },
    });
  });
  await page.goto("/decks?tag=Direito&sort=popular");

  const select = page.getByRole("combobox", { name: "Ordenar por" });
  await expect(select).toContainText("Mais populares");
  await select.click();
  for (const label of [
    "Recomendados",
    "Mais populares",
    "Atualizados recentemente",
    "Mais notas",
    "Recentes",
  ]) {
    await expect(page.getByRole("option", { name: label })).toBeVisible();
  }
  await page.getByRole("option", { name: "Mais notas" }).click();

  await expect(page).toHaveURL(/sort=notes/);
  await expect(page).toHaveURL(/tag=Direito/);
  await expect
    .poll(() =>
      requests.some((url) => url.searchParams.get("sort") === "notes"),
    )
    .toBeTruthy();
  const notesRequest = requests.find(
    (url) => url.searchParams.get("sort") === "notes",
  );
  expect(notesRequest?.searchParams.has("cursor")).toBeFalsy();
});

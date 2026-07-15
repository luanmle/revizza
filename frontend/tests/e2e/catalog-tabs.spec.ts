import { expect, type Page, test } from "@playwright/test";

const DECKS = {
  catalog: {
    id: "11111111-1111-4111-8111-111111111111",
    name: "Catálogo geral",
  },
  moderated: { id: "22222222-2222-4222-8222-222222222222", name: "Meu deck" },
};

async function mockCatalog(page: Page) {
  const requests: URL[] = [];
  await page.route("**/api/v1/decks/**", async (route) => {
    const url = new URL(route.request().url());
    requests.push(url);
    const deck = url.searchParams.has("moderated")
      ? DECKS.moderated
      : url.searchParams.has("subscribed")
        ? null
        : DECKS.catalog;
    const isNextPage = url.searchParams.has("cursor");
    await route.fulfill({
      status: 200,
      json: {
        next: isNextPage
          ? null
          : `${url.origin}/api/v1/decks/?cursor=next-page`,
        previous: null,
        results: deck
          ? [
              {
                ...deck,
                id: isNextPage
                  ? "33333333-3333-4333-8333-333333333333"
                  : deck.id,
                name: isNextPage ? "Outra página" : deck.name,
                description: "",
                subject_tags: ["Direito"],
                note_count: 10,
                subscriber_count: 2,
                creator: null,
                is_official: false,
                last_updated_at: "2026-07-15T12:00:00Z",
              },
            ]
          : [],
      },
    });
  });
  return requests;
}

test("abas preservam tag, refletem URL e reiniciam cursor", async ({
  page,
}) => {
  const requests = await mockCatalog(page);
  await page.goto("/decks?tag=Direito");

  await expect(
    page.getByRole("link", { name: DECKS.catalog.name }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Carregar mais" }).click();
  await expect
    .poll(() => requests.some((url) => url.searchParams.has("cursor")))
    .toBeTruthy();

  await page.getByRole("tab", { name: "Meus baralhos" }).click();
  await expect(page).toHaveURL(/tab=moderated/);
  await expect(page).toHaveURL(/tag=Direito/);
  await expect(
    page.getByRole("link", { name: DECKS.moderated.name }),
  ).toBeVisible();
  const moderatedRequest = requests.find((url) =>
    url.searchParams.has("moderated"),
  );
  expect(moderatedRequest?.searchParams.has("cursor")).toBeFalsy();

  await page.getByRole("tab", { name: "Inscritos" }).click();
  await expect(
    page.getByRole("heading", { name: "Nenhum deck inscrito" }),
  ).toBeVisible();
});

import { expect, test } from "@playwright/test";

const DECK_ID = "11111111-1111-4111-8111-111111111111";
const deck = {
  id: DECK_ID,
  name: "Direito Constitucional",
  description: "Deck comunitário.",
  subject_tags: ["Direito"],
  note_count: 120,
  subscriber_count: 45,
  creator: { id: "creator", name: "Ana Silva", avatar_url: null },
  is_official: true,
  last_updated_at: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
};

test.beforeEach(async ({ page }) => {
  await page.route("**/api/v1/decks/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    await route.fulfill({
      status: 200,
      json: path.endsWith(`/${DECK_ID}/`)
        ? {
            ...deck,
            moderator_count: 1,
            is_moderator: false,
            is_subscribed: false,
            sync_status: null,
            note_types: [],
            moderators: [
              {
                id: "relation",
                user_id: "moderator",
                name: "Bruno Costa",
                avatar_url: null,
              },
            ],
          }
        : { next: null, previous: null, results: [deck] },
    });
  });
});

test("card mostra autoria, selo e atualização", async ({ page }) => {
  await page.goto("/decks");

  await expect(page.getByText("Oficial")).toBeVisible();
  await expect(page.getByText("Ana Silva")).toBeVisible();
  await expect(page.getByText(/Atualizado há 1 hora/)).toBeVisible();
});

test("detalhe mostra criador e moderadores ativos", async ({ page }) => {
  await page.goto(`/decks/${DECK_ID}`);

  await expect(page.getByText("Oficial")).toBeVisible();
  await expect(page.getByText("Ana Silva")).toBeVisible();
  await expect(page.getByText("Bruno Costa")).toBeVisible();
  await expect(page.getByText(/Atualizado há 1 hora/)).toBeVisible();
});

test("catálogo e detalhe não transbordam em 360px e desktop", async ({
  page,
}) => {
  for (const viewport of [
    { name: "360", width: 360, height: 800 },
    { name: "desktop", width: 1280, height: 900 },
  ]) {
    await page.setViewportSize(viewport);
    for (const route of [
      { name: "decks", path: "/decks" },
      { name: "detail", path: `/decks/${DECK_ID}` },
    ]) {
      await page.goto(route.path);
      await expect(page.getByRole("main")).toBeVisible();
      await expect(
        route.name === "decks"
          ? page.getByRole("link", { name: deck.name })
          : page.getByRole("heading", { level: 1, name: deck.name }),
      ).toBeVisible();
      expect(
        await page.evaluate(
          () => document.documentElement.scrollWidth <= window.innerWidth,
        ),
      ).toBeTruthy();
      await page.screenshot({
        path: `test-results/catalog-${route.name}-${viewport.name}.png`,
        fullPage: true,
      });
    }
  }
});

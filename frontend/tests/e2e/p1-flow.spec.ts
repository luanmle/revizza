import { expect, type Page, test } from "@playwright/test";

const DECK_ID = "11111111-1111-4111-8111-111111111111";
const NOTE_ID = "22222222-2222-4222-8222-222222222222";
const SUGGESTION_ID = "33333333-3333-4333-8333-333333333333";
const DECK_NAME = "Direito Administrativo";

function recoveryToken() {
  const encode = (value: object) =>
    Buffer.from(JSON.stringify(value)).toString("base64url");
  const now = Math.floor(Date.now() / 1000);
  return `${encode({ alg: "HS256", typ: "JWT" })}.${encode({
    aud: "authenticated",
    email: "aluno@example.com",
    exp: now + 3600,
    iat: now,
    sub: "44444444-4444-4444-8444-444444444444",
  })}.test-signature`;
}

interface MockState {
  registered: boolean;
  subscribed: boolean;
  moderator: boolean;
  suggestion: null | {
    change_category: string;
    justification: string;
    proposed_field_values: Record<string, string>;
    tags: string[];
    status: "pending" | "accepted";
  };
}

async function mockApi(page: Page): Promise<MockState> {
  const state: MockState = {
    registered: false,
    subscribed: false,
    moderator: false,
    suggestion: null,
  };
  const headers = {
    "access-control-allow-origin": "http://localhost:3000",
    "access-control-allow-headers": "Accept, Authorization, Content-Type",
    "access-control-allow-methods": "DELETE, GET, OPTIONS, PATCH, POST, PUT",
  };

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const method = request.method();
    const path = new URL(request.url()).pathname.replace(/^\/api\/v1/, "");
    const json = (status: number, body: unknown) =>
      route.fulfill({ status, headers, json: body });

    if (method === "OPTIONS") {
      await route.fulfill({ status: 204, headers });
    } else if (method === "POST" && path === "/accounts/register/") {
      state.registered = true;
      await json(201, {});
    } else if (method === "GET" && path === "/accounts/me/") {
      await json(200, { id: "moderator-user" });
    } else if (method === "GET" && path === "/decks/") {
      await json(200, {
        next: null,
        previous: null,
        results: [
          {
            id: DECK_ID,
            name: DECK_NAME,
            subject_tags: ["Direito"],
            note_count: 1,
            subscriber_count: state.subscribed ? 1 : 0,
          },
        ],
      });
    } else if (method === "GET" && path === `/decks/${DECK_ID}/`) {
      await json(200, {
        id: DECK_ID,
        name: DECK_NAME,
        description: "Deck comunitário para concursos.",
        subject_tags: ["Direito"],
        note_count: 1,
        subscriber_count: state.subscribed ? 1 : 0,
        moderator_count: 1,
        is_moderator: state.moderator,
        is_subscribed: state.subscribed,
      });
    } else if (
      method === "POST" &&
      path === `/decks/${DECK_ID}/subscriptions/`
    ) {
      state.subscribed = true;
      await json(201, {});
    } else if (method === "GET" && path === `/decks/${DECK_ID}/notes/`) {
      await json(200, {
        next: null,
        previous: null,
        results: [
          {
            id: NOTE_ID,
            field_values: {
              Frente: "Qual é o prazo da licitação?",
              Verso: "15 dias",
            },
            tags: ["lei-14133"],
          },
        ],
      });
    } else if (method === "GET" && path === `/notes/${NOTE_ID}/`) {
      await json(200, {
        id: NOTE_ID,
        deck: DECK_ID,
        field_values: {
          Frente: "Qual é o prazo da licitação?",
          Verso: "15 dias",
        },
        tags: ["lei-14133"],
        note_type: {
          field_names: ["Frente", "Verso"],
          templates: [
            {
              name: "Card 1",
              qfmt: "{{Frente}}",
              afmt: "{{FrontSide}}<hr>{{Verso}}",
            },
          ],
          css: ".card { font-family: sans-serif; }",
        },
      });
    } else if (
      method === "POST" &&
      path === `/notes/${NOTE_ID}/suggestions/change/`
    ) {
      const body = request.postDataJSON() as Omit<
        NonNullable<MockState["suggestion"]>,
        "status"
      >;
      state.suggestion = { ...body, status: "pending" };
      state.moderator = true;
      await json(201, { id: SUGGESTION_ID });
    } else if (method === "GET" && path === `/decks/${DECK_ID}/suggestions/`) {
      await json(200, {
        next: null,
        previous: null,
        results: state.suggestion
          ? [
              {
                id: SUGGESTION_ID,
                deck: DECK_ID,
                type: "change",
                author: "student-user",
                author_name: "Estudante",
                likes_count: 0,
                dislikes_count: 0,
                rejection_reason: null,
                empty_fields: [],
                note_ids: [NOTE_ID],
                note_context: [
                  {
                    id: NOTE_ID,
                    field_values: {
                      Frente: "Qual é o prazo da licitação?",
                      Verso: "15 dias",
                    },
                    tags: ["lei-14133"],
                    open_suggestion_count: 1,
                  },
                ],
                created_at: "2026-07-13T12:00:00Z",
                ...state.suggestion,
              },
            ]
          : [],
      });
    } else if (
      method === "POST" &&
      path === `/suggestions/${SUGGESTION_ID}/accept/`
    ) {
      if (state.suggestion) state.suggestion.status = "accepted";
      await json(200, { status: "accepted" });
    } else {
      await json(404, { detail: `${method} ${path} não mockado` });
    }
  });

  return state;
}

test("T130 redefine a senha após abrir o link de recuperação", async ({
  page,
}) => {
  let updatedPassword = "";
  await page.route("**/auth/v1/**", async (route) => {
    const request = route.request();
    if (new URL(request.url()).pathname.endsWith("/user")) {
      if (request.method() === "PUT") {
        updatedPassword = request.postDataJSON().password;
      }
      await route.fulfill({
        status: 200,
        json: {
          id: "44444444-4444-4444-8444-444444444444",
          aud: "authenticated",
          role: "authenticated",
          email: "aluno@example.com",
          app_metadata: { provider: "email", providers: ["email"] },
          user_metadata: {},
          created_at: "2026-07-13T12:00:00Z",
          updated_at: "2026-07-13T12:00:00Z",
        },
      });
      return;
    }
    await route.abort();
  });

  const expiresAt = Math.floor(Date.now() / 1000) + 3600;
  await page.goto(
    `/password-reset/callback#access_token=${recoveryToken()}&expires_at=${expiresAt}&expires_in=3600&refresh_token=test-refresh&type=recovery&token_type=bearer`,
  );
  await page
    .getByLabel("Nova senha", { exact: true })
    .fill("nova-senha-segura");
  await page.getByLabel("Confirmar nova senha").fill("nova-senha-segura");
  await page.getByRole("button", { name: "Alterar senha" }).click();

  await expect(
    page.getByText("Senha alterada.", { exact: false }),
  ).toBeVisible();
  expect(updatedPassword).toBe("nova-senha-segura");
});

test("T122 mantém transição e preview abaixo de 500ms", async ({ page }) => {
  const state = await mockApi(page);
  state.subscribed = true;

  // Compila a rota antes de medir a carga típica, sem contar cold start do dev server.
  await page.goto(`/decks/${DECK_ID}`);
  await expect(
    page.getByRole("heading", { level: 1, name: DECK_NAME }),
  ).toBeVisible();
  await page.goto("/decks");
  await expect(page.getByRole("link", { name: DECK_NAME })).toBeVisible();

  let startedAt = performance.now();
  await page.getByRole("link", { name: DECK_NAME }).click();
  await expect(
    page.getByRole("heading", { level: 1, name: DECK_NAME }),
  ).toBeVisible({ timeout: 500 });
  const transitionMs = performance.now() - startedAt;

  await page.getByRole("button", { name: "Explorar notas" }).click();
  await expect(page.getByRole("button", { name: "Visualizar" })).toBeVisible();
  startedAt = performance.now();
  await page.getByRole("button", { name: "Visualizar" }).click();
  await expect(
    page
      .frameLocator('iframe[title="Preview do card Card 1"]')
      .getByText("15 dias"),
  ).toBeVisible({ timeout: 500 });
  const previewMs = performance.now() - startedAt;

  expect(
    transitionMs,
    `Transição levou ${transitionMs.toFixed(1)}ms`,
  ).toBeLessThan(500);
  expect(previewMs, `Preview levou ${previewMs.toFixed(1)}ms`).toBeLessThan(
    500,
  );
});

test("T123 cobre cadastro, assinatura, sugestão e moderação", async ({
  page,
}) => {
  const state = await mockApi(page);

  await page.goto("/register");
  await page.getByLabel("E-mail", { exact: true }).fill("aluno@example.com");
  await page.getByLabel("Senha", { exact: true }).fill("senha-segura");
  await page
    .getByRole("main")
    .getByRole("button", { name: "Criar conta" })
    .click();
  await expect(page.getByText("Conta criada!", { exact: true })).toBeVisible();

  await page.goto("/decks");
  await page.getByRole("link", { name: DECK_NAME }).click();
  await page.getByRole("button", { name: "Inscrever-se" }).click();
  await expect(
    page.getByRole("button", { name: "Cancelar inscrição" }),
  ).toBeVisible();

  await page.getByRole("button", { name: "Explorar notas" }).click();
  await page.getByRole("button", { name: "Sugerir mudança" }).click();
  await page.getByLabel("Tipo de mudança").click();
  await page.getByRole("option", { name: "Erro de conteúdo" }).click();
  await page
    .getByLabel("Justificativa")
    .fill("Atualizar a nota conforme a lei vigente.");
  await page
    .getByLabel("Adicionar tags (separadas por vírgula)")
    .fill("atualizada");
  await page.getByRole("button", { name: "Enviar sugestão" }).click();
  await expect(
    page.getByText("Sugestão enviada", { exact: true }),
  ).toBeVisible();

  await page.getByRole("link", { name: "Voltar ao deck" }).click();
  await page.getByRole("button", { name: "Ver sugestões" }).click();
  await expect(
    page.getByText("Atualizar a nota conforme a lei vigente."),
  ).toBeVisible();
  await page.getByRole("button", { name: "Aceitar" }).click();
  await expect(page.getByText("Aceita", { exact: true })).toBeVisible();

  expect(state).toMatchObject({
    registered: true,
    subscribed: true,
    moderator: true,
    suggestion: { status: "accepted", tags: ["atualizada"] },
  });
});

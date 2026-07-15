import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import SuggestionsPage from "@/app/decks/[id]/suggestions/page";

const NOTE_ID = "11111111-1111-1111-1111-111111111111";

const api = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
}));

vi.mock("@/lib/api-client", () => ({
  api,
  ApiError: class ApiError extends Error {
    status: number;
    body: unknown;
    constructor(status: number, body: unknown) {
      super("api error");
      this.status = status;
      this.body = body;
    }
  },
}));

// deep-link "Ver histórico" (US3): ?note_id= na URL
vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "deck-1" }),
  useSearchParams: () => new URLSearchParams(`note_id=${NOTE_ID}`),
}));

beforeEach(() => {
  vi.clearAllMocks();
  api.get.mockImplementation((path: string) => {
    if (path === "/accounts/me/") return Promise.resolve({ id: "user-1" });
    if (path === "/decks/deck-1/") return Promise.resolve({ id: "deck-1", name: "Deck", is_moderator: false });
    return Promise.resolve({ next: null, previous: null, results: [] });
  });
});

afterEach(cleanup);

function renderPage() {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <SuggestionsPage />
    </QueryClientProvider>,
  );
}

test("pré-filtra a lista pelo note_id da URL", async () => {
  renderPage();

  await waitFor(() =>
    expect(
      api.get.mock.calls.some(
        ([path]: [string]) =>
          path.startsWith("/decks/deck-1/suggestions/") &&
          path.includes(`note_id=${NOTE_ID}`),
      ),
    ).toBe(true),
  );

  // o campo do filtro reflete a nota pré-selecionada
  expect(
    (screen.getByLabelText("ID da nota") as HTMLInputElement).value,
  ).toBe(NOTE_ID);
});

test("nota sem sugestões mostra estado vazio, não erro", async () => {
  renderPage();

  expect(await screen.findByText("Nenhuma sugestão aqui")).toBeDefined();
});

import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import CommentThread from "@/components/CommentThread";

const api = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
}));

vi.mock("@/lib/api-client", () => ({ api }));

beforeEach(() => {
  vi.clearAllMocks();
  api.get.mockImplementation((path: string) =>
    Promise.resolve(
      path === "/accounts/me/"
        ? { id: "user-1" }
        : { next: null, previous: null, results: [] },
    ),
  );
  api.post.mockResolvedValue({ id: "comment-1" });
});

afterEach(cleanup);

test("mostra estado vazio e publica comentário na thread da nota", async () => {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <CommentThread noteId="note-1" />
    </QueryClientProvider>,
  );

  expect(await screen.findByText("Comece a conversa")).toBeDefined();

  fireEvent.change(screen.getByLabelText("Novo comentário"), {
    target: { value: "  Dúvida relevante.  " },
  });
  fireEvent.click(screen.getByRole("button", { name: "Comentar" }));

  await waitFor(() =>
    expect(api.post).toHaveBeenCalledWith("/notes/note-1/comments/", {
      body: "Dúvida relevante.",
    }),
  );
});

test("exibe o nome do autor em vez do prefixo do UUID", async () => {
  api.get.mockImplementation((path: string) =>
    Promise.resolve(
      path === "/accounts/me/"
        ? { id: "user-1" }
        : {
            next: null,
            previous: null,
            results: [
              {
                id: "comment-1",
                author: "user-2",
                author_name: "Ana Souza",
                body: "Comentário útil.",
                created_at: "2026-07-13T12:00:00Z",
                edited_at: null,
              },
            ],
          },
    ),
  );
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  render(
    <QueryClientProvider client={client}>
      <CommentThread noteId="note-1" />
    </QueryClientProvider>,
  );

  expect(await screen.findByText("Ana Souza")).toBeDefined();
  expect(screen.queryByText(/Usuário user-2/)).toBeNull();
});

test("mostra loading ao tentar carregar comentários novamente", async () => {
  let attempts = 0;
  let finishRetry!: (value: unknown) => void;
  const retry = new Promise((resolve) => {
    finishRetry = resolve;
  });
  api.get.mockImplementation((path: string) => {
    if (path === "/accounts/me/") return Promise.resolve({ id: "user-1" });
    attempts += 1;
    return attempts === 1 ? Promise.reject(new Error("offline")) : retry;
  });
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });

  render(
    <QueryClientProvider client={client}>
      <CommentThread noteId="note-1" />
    </QueryClientProvider>,
  );

  fireEvent.click(
    await screen.findByRole("button", { name: "Tentar novamente" }),
  );

  expect(await screen.findByLabelText("Carregando comentários")).toBeDefined();
  finishRetry({ next: null, previous: null, results: [] });
});

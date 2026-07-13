"use client";

import { useState } from "react";
import Link from "next/link";
import { useInfiniteQuery } from "@tanstack/react-query";
import { api, ApiError, Paginated } from "@/lib/api-client";

interface Deck {
  id: string;
  name: string;
  subject_tags: string[];
  note_count: number;
  subscriber_count: number;
}

export default function DecksPage() {
  const [tag, setTag] = useState("");
  const [tagInput, setTagInput] = useState("");

  const { data, error, fetchNextPage, hasNextPage, isFetching } = useInfiniteQuery({
    queryKey: ["decks", tag],
    queryFn: ({ pageParam }) =>
      api.get<Paginated<Deck>>(
        `/decks/${pageParam ?? (tag ? `?tag=${encodeURIComponent(tag)}` : "")}`,
      ),
    initialPageParam: undefined as string | undefined,
    // o cursor vem embutido na URL `next` (convenção AnkiHub)
    getNextPageParam: (last) => (last.next ? new URL(last.next).search : undefined),
    retry: false,
  });

  if (error instanceof ApiError && error.status === 401) {
    return (
      <main className="form-page">
        <p>
          <Link href="/login">Entre</Link> para explorar o catálogo de decks.
        </p>
      </main>
    );
  }

  const decks = data?.pages.flatMap((page) => page.results) ?? [];

  return (
    <main className="form-page">
      <h1>Catálogo de decks</h1>
      <form
        onSubmit={(e) => {
          e.preventDefault();
          setTag(tagInput.trim());
        }}
      >
        <label>
          Filtrar por matéria/tag
          <input
            type="search"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            placeholder="ex.: Direito"
          />
        </label>
        <button type="submit">Filtrar</button>
      </form>

      <ul className="deck-list">
        {decks.map((deck) => (
          <li key={deck.id}>
            <Link href={`/decks/${deck.id}`}>
              <strong>{deck.name}</strong>
            </Link>
            <p>{deck.subject_tags.join(", ")}</p>
            <p>
              {deck.note_count} notas · {deck.subscriber_count} assinantes
            </p>
          </li>
        ))}
      </ul>
      {decks.length === 0 && !isFetching && <p>Nenhum deck encontrado.</p>}
      {hasNextPage && (
        <button onClick={() => fetchNextPage()} disabled={isFetching}>
          Carregar mais
        </button>
      )}
    </main>
  );
}

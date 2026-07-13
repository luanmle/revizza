"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api-client";

interface DeckDetail {
  id: string;
  name: string;
  description: string;
  subject_tags: string[];
  note_count: number;
  subscriber_count: number;
  moderators: { id: string; email: string }[];
  is_subscribed: boolean;
}

export default function DeckDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const { data: deck, error } = useQuery<DeckDetail>({
    queryKey: ["deck", id],
    queryFn: () => api.get<DeckDetail>(`/decks/${id}/`),
    retry: false,
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["deck", id] });
  const subscribe = useMutation({
    mutationFn: () => api.post(`/decks/${id}/subscriptions/`),
    onSuccess: invalidate,
  });
  const unsubscribe = useMutation({
    mutationFn: () => api.delete(`/decks/${id}/subscriptions/me/`),
    onSuccess: invalidate,
  });

  if (error instanceof ApiError && error.status === 401) {
    return (
      <main className="form-page">
        <p>
          <Link href="/login">Entre</Link> para ver este deck.
        </p>
      </main>
    );
  }
  if (!deck) return <main className="form-page">Carregando…</main>;

  const busy = subscribe.isPending || unsubscribe.isPending;

  return (
    <main className="form-page">
      <p>
        <Link href="/decks">← Catálogo</Link>
      </p>
      <h1>{deck.name}</h1>
      {deck.description && <p>{deck.description}</p>}
      <p>{deck.subject_tags.join(", ")}</p>
      <p>
        {deck.note_count} notas · {deck.subscriber_count} assinantes
      </p>
      <p>Moderadores: {deck.moderators.map((m) => m.email).join(", ") || "—"}</p>

      {deck.is_subscribed ? (
        <>
          <button onClick={() => unsubscribe.mutate()} disabled={busy}>
            Cancelar inscrição
          </button>
          <p>
            <Link href={`/decks/${id}/suggest-new-note`}>Sugerir nota nova</Link>
          </p>
          <p>
            <Link href={`/decks/${id}/protection`}>Configurar proteção pessoal</Link>
          </p>
          <p>
            <Link href={`/decks/${id}/moderators`}>Ver moderadores</Link>
          </p>
        </>
      ) : (
        <button onClick={() => subscribe.mutate()} disabled={busy}>
          Inscrever-se
        </button>
      )}
    </main>
  );
}

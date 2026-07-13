"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useInfiniteQuery, useQuery } from "@tanstack/react-query";
import { MessageSquare, SearchX } from "lucide-react";
import { api, ApiError, type Paginated } from "@/lib/api-client";
import CommentThread from "@/components/CommentThread";
import NotePreview, { type NoteTypeInfo } from "@/components/NotePreview";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";

interface NoteListItem {
  id: string;
  field_values: Record<string, string>;
  tags: string[];
}

interface NoteDetail extends NoteListItem {
  note_type: NoteTypeInfo;
}

interface DeckDetail {
  id: string;
  name: string;
}

const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function nextPath(next: string | null): string | null {
  if (!next) return null;
  const marker = "/api/v1";
  return next.slice(next.indexOf(marker) + marker.length);
}

/** Trecho textual dos campos, sem HTML, para a lista de resultados. */
function snippet(fieldValues: Record<string, string>): string {
  const text = Object.values(fieldValues)
    .join(" · ")
    .replace(/<[^>]+>/g, " ")
    .replace(/\s+/g, " ")
    .trim();
  return text.length > 160 ? `${text.slice(0, 160)}…` : text;
}

function NoteResult({ note, deckId }: { note: NoteListItem; deckId: string }) {
  const [previewOpen, setPreviewOpen] = useState(false);
  const [discussionOpen, setDiscussionOpen] = useState(false);
  // detalhe (templates+css) só é buscado quando o preview abre
  const { data: detail, isPending } = useQuery<NoteDetail>({
    queryKey: ["note", note.id],
    queryFn: () => api.get<NoteDetail>(`/notes/${note.id}/`),
    enabled: previewOpen,
  });

  return (
    <Card>
      <CardContent className="flex flex-col gap-3">
        <p>{snippet(note.field_values) || "(nota sem conteúdo textual)"}</p>
        <p className="font-mono text-sm text-muted-foreground">{note.id}</p>
        {note.tags.length > 0 && (
          <p className="text-sm text-muted-foreground">{note.tags.join(", ")}</p>
        )}
        <div className="flex flex-wrap gap-2">
          <Button
            size="sm"
            variant="outline"
            onClick={() => setPreviewOpen((open) => !open)}
            aria-expanded={previewOpen}
          >
            {previewOpen ? "Ocultar preview" : "Visualizar"}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            nativeButton={false}
            render={<Link href={`/decks/${deckId}/notes/${note.id}/suggest`} />}
          >
            Sugerir mudança
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setDiscussionOpen((open) => !open)}
            aria-expanded={discussionOpen}
          >
            <MessageSquare aria-hidden /> Discussão
          </Button>
          <Button
            size="sm"
            variant="ghost"
            nativeButton={false}
            render={
              <Link
                href={`/decks/${deckId}/notes/${note.id}/suggest-deletion`}
              />
            }
          >
            Sugerir exclusão
          </Button>
        </div>
        {previewOpen && isPending && <Skeleton className="h-64 w-full" />}
        {previewOpen && detail && (
          <NotePreview noteType={detail.note_type} fieldValues={detail.field_values} />
        )}
        {discussionOpen && <CommentThread noteId={note.id} />}
      </CardContent>
    </Card>
  );
}

export default function NotesSearchPage() {
  const { id } = useParams<{ id: string }>();

  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");

  const { data: deck } = useQuery<DeckDetail>({
    queryKey: ["deck", id],
    queryFn: () => api.get<DeckDetail>(`/decks/${id}/`),
    retry: false,
  });

  // FR-010: termo textual ou ID exato — UUID válido vira busca por ID
  const params = new URLSearchParams();
  if (query) params.set(UUID_RE.test(query) ? "note_id" : "q", query);
  const firstPage = `/decks/${id}/notes/?${params}`;

  const notes = useInfiniteQuery({
    queryKey: ["notes", id, firstPage],
    queryFn: ({ pageParam }) => api.get<Paginated<NoteListItem>>(pageParam),
    initialPageParam: firstPage,
    getNextPageParam: (lastPage) => nextPath(lastPage.next),
    retry: false,
  });

  if (notes.error instanceof ApiError && notes.error.status === 401) {
    return (
      <main className="mx-auto max-w-3xl p-4 md:p-6">
        <p>
          <Link href="/login" className="text-primary underline">
            Entre
          </Link>{" "}
          para buscar notas.
        </p>
      </main>
    );
  }

  const results = notes.data?.pages.flatMap((page) => page.results) ?? [];

  return (
    <main className="mx-auto max-w-3xl p-4 md:p-6">
      <nav aria-label="Trilha de navegação" className="mb-4 text-sm text-muted-foreground">
        <Link href="/decks" className="hover:text-foreground">
          Catálogo
        </Link>{" "}
        /{" "}
        <Link href={`/decks/${id}`} className="hover:text-foreground">
          {deck?.name ?? "Deck"}
        </Link>{" "}
        / <span className="text-foreground">Notas</span>
      </nav>

      <h1 className="mb-6 text-2xl font-semibold tracking-tight">Notas do deck</h1>

      <form
        className="mb-6 flex flex-col gap-2 sm:flex-row sm:items-end"
        onSubmit={(e) => {
          e.preventDefault();
          setQuery(input.trim());
        }}
      >
        <div className="flex flex-1 flex-col gap-1">
          <Label htmlFor="note-search">Buscar por termo ou ID da nota</Label>
          <Input
            id="note-search"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ex.: prazo de licitação, ou um UUID exato"
          />
        </div>
        <Button type="submit">Buscar</Button>
      </form>

      {notes.isPending && (
        <div className="flex flex-col gap-4">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
        </div>
      )}

      {notes.isError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao buscar notas</AlertTitle>
          <AlertDescription>
            {(notes.error instanceof ApiError &&
              (notes.error.body as { detail?: string } | null)?.detail) ||
              "Não foi possível buscar as notas."}{" "}
            <button className="underline" onClick={() => notes.refetch()}>
              Tentar novamente
            </button>
          </AlertDescription>
        </Alert>
      )}

      {notes.isSuccess && results.length === 0 && (
        <div className="flex flex-col items-center gap-2 py-12 text-center">
          <SearchX aria-hidden className="size-8 text-muted-foreground" />
          <p className="text-lg font-medium">Nenhuma nota encontrada</p>
          <p className="text-sm text-muted-foreground">
            Tente outro termo ou confira o ID da nota.
          </p>
        </div>
      )}

      <div className="flex flex-col gap-4">
        {results.map((note) => (
          <NoteResult key={note.id} note={note} deckId={id} />
        ))}
      </div>

      {notes.hasNextPage && (
        <div className="mt-4 flex justify-center">
          <Button
            variant="outline"
            onClick={() => notes.fetchNextPage()}
            disabled={notes.isFetchingNextPage}
          >
            {notes.isFetchingNextPage ? "Carregando…" : "Carregar mais"}
          </Button>
        </div>
      )}
    </main>
  );
}

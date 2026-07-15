"use client";

/**
 * Página pública da nota (US1): aberta pelo botão "Ver no Revizza" do add-on,
 * sem exigir login. Leitura apenas — reusa NotePreview (FR-011). Ações de
 * contribuição (sugerir mudança/histórico) continuam atrás de auth nas suas telas.
 */

import Link from "next/link";
import { useParams } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api-client";
import NotePreview, { NoteTypeInfo } from "@/components/NotePreview";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

interface NoteDetail {
  id: string;
  field_values: Record<string, string>;
  tags: string[];
  note_type: NoteTypeInfo;
}

interface DeckDetail {
  id: string;
  name: string;
}

export default function NotePage() {
  const { id, noteId } = useParams<{ id: string; noteId: string }>();

  // deck opcional: rota pode exigir auth para visitantes anônimos — tolera falha
  const { data: deck } = useQuery<DeckDetail>({
    queryKey: ["deck", id],
    queryFn: () => api.get<DeckDetail>(`/decks/${id}/`),
    retry: false,
  });
  const {
    data: note,
    error,
    isPending,
  } = useQuery<NoteDetail>({
    queryKey: ["note", noteId],
    queryFn: () => api.get<NoteDetail>(`/notes/${noteId}/`),
    retry: false,
  });

  if (error instanceof ApiError && error.status === 404) {
    return (
      <main className="mx-auto max-w-3xl p-4 md:p-6">
        <Alert>
          <AlertTitle>Nota não encontrada</AlertTitle>
          <AlertDescription>
            Esta nota não existe mais no Revizza.{" "}
            <Link href="/decks" className="text-primary underline">
              Ver catálogo
            </Link>
          </AlertDescription>
        </Alert>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl p-4 md:p-6">
      <nav
        aria-label="Trilha de navegação"
        className="mb-4 text-sm text-muted-foreground"
      >
        <Link href="/decks" className="hover:text-foreground">
          Catálogo
        </Link>{" "}
        /{" "}
        <Link href={`/decks/${id}`} className="hover:text-foreground">
          {deck?.name ?? "Deck"}
        </Link>{" "}
        / <span className="text-foreground">Nota</span>
      </nav>

      <h1 className="mb-6 text-2xl font-semibold tracking-tight">Nota</h1>

      {isPending && <Skeleton className="h-64 w-full" />}

      {note && (
        <div className="flex flex-col gap-6">
          <NotePreview
            noteType={note.note_type}
            fieldValues={note.field_values}
          />

          {note.tags.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {note.tags.map((tag) => (
                <span
                  key={tag}
                  className="rounded-full bg-muted px-3 py-1 text-sm text-muted-foreground"
                >
                  {tag}
                </span>
              ))}
            </div>
          )}

          <div className="flex flex-wrap gap-3">
            <Button
              nativeButton={false}
              render={<Link href={`/decks/${id}/notes/${noteId}/suggest`} />}
            >
              Sugerir mudança
            </Button>
            <Button
              nativeButton={false}
              variant="outline"
              render={
                <Link href={`/decks/${id}/suggestions?note_id=${noteId}`} />
              }
            >
              Ver histórico
            </Button>
          </div>
        </div>
      )}
    </main>
  );
}

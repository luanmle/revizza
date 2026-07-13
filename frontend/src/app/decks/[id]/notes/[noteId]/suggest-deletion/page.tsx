"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { CircleAlert, Trash2 } from "lucide-react";
import { api, ApiError } from "@/lib/api-client";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";

interface DeckDetail {
  id: string;
  name: string;
}

interface NoteDetail {
  id: string;
  field_values: Record<string, string>;
  tags: string[];
}

function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return "Não foi possível enviar a sugestão.";
  if (error.status === 403) return "Assine o deck para sugerir a exclusão.";
  if (error.status === 429)
    return "Você enviou sugestões demais. Aguarde um pouco e tente novamente.";
  return "Não foi possível enviar a sugestão. Revise a justificativa.";
}

export default function SuggestDeletionPage() {
  const { id, noteId } = useParams<{ id: string; noteId: string }>();
  const [justification, setJustification] = useState("");
  const [confirmed, setConfirmed] = useState(false);
  const [formError, setFormError] = useState("");

  const deck = useQuery<DeckDetail>({
    queryKey: ["deck", id],
    queryFn: () => api.get(`/decks/${id}/`),
    retry: false,
  });
  const note = useQuery<NoteDetail>({
    queryKey: ["note", noteId],
    queryFn: () => api.get(`/notes/${noteId}/`),
    retry: false,
  });
  const submit = useMutation({
    mutationFn: () =>
      api.post(`/notes/${noteId}/suggestions/deletion/`, {
        justification: justification.trim(),
      }),
  });

  function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!justification.trim())
      return setFormError("A justificativa é obrigatória.");
    if (!confirmed)
      return setFormError("Confirme que entende o efeito da aprovação.");
    setFormError("");
    submit.mutate();
  }

  if (note.error instanceof ApiError && note.error.status === 401) {
    return (
      <main className="mx-auto max-w-3xl p-4 md:p-6">
        <p>
          <Link href="/login" className="text-primary underline">
            Entre
          </Link>{" "}
          para sugerir a exclusão.
        </p>
      </main>
    );
  }

  if (submit.isSuccess) {
    return (
      <main className="mx-auto max-w-3xl p-4 md:p-6">
        <Alert>
          <AlertTitle>Sugestão de exclusão enviada</AlertTitle>
          <AlertDescription>
            A nota continua disponível até a decisão de um moderador.{" "}
            <Link
              href={`/decks/${id}/suggestions`}
              className="text-primary underline"
            >
              Acompanhar sugestão
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
          {deck.data?.name ?? "Deck"}
        </Link>{" "}
        / <span className="text-foreground">Sugerir exclusão</span>
      </nav>

      <h1 className="mb-2 text-2xl font-semibold tracking-tight">
        Sugerir exclusão da nota
      </h1>
      <p className="mb-6 max-w-[70ch] text-sm text-muted-foreground">
        A exclusão só acontece após aprovação de um moderador e será propagada na
        próxima sincronização.
      </p>

      {note.isPending && <Skeleton className="mb-6 h-36 w-full" />}

      {note.data && (
        <section aria-labelledby="note-context" className="mb-6 border-y py-4">
          <h2 id="note-context" className="mb-3 font-semibold">
            Nota que será revisada
          </h2>
          <dl className="flex flex-col gap-3">
            {Object.entries(note.data.field_values).map(([field, html]) => (
              <div key={field}>
                <dt className="text-sm font-medium text-muted-foreground">{field}</dt>
                <dd
                  className="max-w-[70ch]"
                  // HTML sanitizado pelo backend antes de persistir.
                  dangerouslySetInnerHTML={{ __html: html }}
                />
              </div>
            ))}
          </dl>
        </section>
      )}

      <Alert className="mb-6">
        <CircleAlert aria-hidden />
        <AlertTitle>O conteúdo não será removido agora</AlertTitle>
        <AlertDescription>
          Moderadores verão sua justificativa e poderão aceitar ou rejeitar a proposta.
        </AlertDescription>
      </Alert>

      <form className="flex flex-col gap-5" onSubmit={onSubmit}>
        <div className="flex flex-col gap-2">
          <Label htmlFor="deletion-justification">Justificativa</Label>
          <Textarea
            id="deletion-justification"
            value={justification}
            onChange={(event) => setJustification(event.target.value)}
            placeholder="Explique por que esta nota deve ser removida"
            required
          />
        </div>

        <label className="flex min-h-11 cursor-pointer items-start gap-3 rounded-lg border p-3">
          <Checkbox
            checked={confirmed}
            onCheckedChange={(checked) => setConfirmed(checked === true)}
            aria-describedby="deletion-confirmation-help"
          />
          <span id="deletion-confirmation-help" className="text-sm leading-5">
            Entendo que, se aprovada, a remoção será enviada aos assinantes na próxima
            sincronização.
          </span>
        </label>

        {(formError || submit.isError) && (
          <p role="alert" className="text-sm text-destructive">
            {formError || errorMessage(submit.error)}
          </p>
        )}

        <div className="flex flex-wrap gap-2">
          <Button
            type="submit"
            variant="destructive"
            className="min-h-11"
            disabled={submit.isPending}
          >
            <Trash2 aria-hidden />
            {submit.isPending ? "Enviando…" : "Enviar para revisão"}
          </Button>
          <Button
            variant="outline"
            className="min-h-11"
            nativeButton={false}
            render={<Link href={`/decks/${id}/notes`} />}
          >
            Cancelar
          </Button>
        </div>
      </form>
    </main>
  );
}

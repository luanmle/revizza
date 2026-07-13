"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { CircleAlert } from "lucide-react";
import { api, ApiError } from "@/lib/api-client";
import RichTextEditor from "@/components/RichTextEditor";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";

interface DeckDetail {
  id: string;
  name: string;
  note_type: {
    name: string;
    field_names: string[];
  };
}

function hasVisibleText(html: string): boolean {
  return html
    .replace(/<[^>]*>/g, "")
    .replace(/&nbsp;|&#160;/g, " ")
    .trim().length > 0;
}

function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return "Não foi possível enviar a sugestão.";
  if (error.status === 403) return "Assine o deck para sugerir uma nota nova.";
  if (error.status === 429)
    return "Você enviou sugestões demais. Aguarde um pouco e tente novamente.";
  return "Revise os campos, a justificativa e as tags antes de tentar novamente.";
}

export default function SuggestNewNotePage() {
  const { id } = useParams<{ id: string }>();
  const [fields, setFields] = useState<Record<string, string>>({});
  const [justification, setJustification] = useState("");
  const [tagsInput, setTagsInput] = useState("");
  const [formError, setFormError] = useState("");

  const deck = useQuery<DeckDetail>({
    queryKey: ["deck", id],
    queryFn: () => api.get(`/decks/${id}/`),
    retry: false,
  });
  const fieldNames = deck.data?.note_type.field_names ?? [];
  const tags = tagsInput
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);
  const emptyFields = fieldNames.filter(
    (field) => !hasVisibleText(fields[field] ?? ""),
  );

  const submit = useMutation({
    mutationFn: () =>
      api.post(`/decks/${id}/suggestions/new-note/`, {
        justification: justification.trim(),
        proposed_field_values: Object.fromEntries(
          fieldNames.map((field) => [field, fields[field] ?? ""]),
        ),
        tags,
      }),
  });

  function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!justification.trim())
      return setFormError("A justificativa é obrigatória.");
    if (tags.length === 0) return setFormError("Informe pelo menos uma tag.");
    setFormError("");
    submit.mutate();
  }

  if (deck.error instanceof ApiError && deck.error.status === 401) {
    return (
      <main className="mx-auto max-w-3xl p-4 md:p-6">
        <p>
          <Link href="/login" className="text-primary underline">
            Entre
          </Link>{" "}
          para sugerir uma nota nova.
        </p>
      </main>
    );
  }

  if (submit.isSuccess) {
    return (
      <main className="mx-auto max-w-3xl p-4 md:p-6">
        <Alert>
          <AlertTitle>Nota nova sugerida</AlertTitle>
          <AlertDescription>
            A proposta está pendente de moderação e aparece na aba “Notas novas”.{" "}
            <Link
              href={`/decks/${id}/suggestions`}
              className="text-primary underline"
            >
              Ver sugestões
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
        / <span className="text-foreground">Sugerir nota nova</span>
      </nav>

      <h1 className="mb-2 text-2xl font-semibold tracking-tight">
        Sugerir nota nova
      </h1>
      <p className="mb-6 max-w-[70ch] text-sm text-muted-foreground">
        Preencha os campos do tipo de nota. Campos vazios são permitidos, mas ficam
        sinalizados para a moderação.
      </p>

      {deck.isPending && (
        <div className="flex flex-col gap-4">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
        </div>
      )}

      {deck.isError && !(deck.error instanceof ApiError && deck.error.status === 401) && (
        <Alert variant="destructive">
          <AlertTitle>Não foi possível carregar o deck</AlertTitle>
          <AlertDescription>
            Tente novamente para obter os campos do tipo de nota.
          </AlertDescription>
        </Alert>
      )}

      {deck.data && (
        <form className="flex flex-col gap-6" onSubmit={onSubmit}>
          <fieldset className="flex flex-col gap-5">
            <legend className="mb-1 font-medium">
              Campos · {deck.data.note_type.name}
            </legend>
            {fieldNames.map((field) => {
              const empty = !hasVisibleText(fields[field] ?? "");
              return (
                <div key={field} className="flex flex-col gap-2">
                  <div className="flex items-center justify-between gap-2">
                    <Label>{field}</Label>
                    {empty && (
                      <Badge variant="outline" className="rounded-full">
                        Vazio
                      </Badge>
                    )}
                  </div>
                  <RichTextEditor
                    value={fields[field] ?? ""}
                    onChange={(html) =>
                      setFields((current) => ({ ...current, [field]: html }))
                    }
                    ariaLabel={`Campo ${field}`}
                  />
                </div>
              );
            })}
          </fieldset>

          <div className="flex flex-col gap-2">
            <Label htmlFor="new-note-tags">Tags</Label>
            <Input
              id="new-note-tags"
              value={tagsInput}
              onChange={(event) => setTagsInput(event.target.value)}
              placeholder="Ex.: direito, licitação, revisão"
              required
            />
            <p className="text-sm text-muted-foreground">
              Separe as tags por vírgulas.
            </p>
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="new-note-justification">Justificativa</Label>
            <Textarea
              id="new-note-justification"
              value={justification}
              onChange={(event) => setJustification(event.target.value)}
              placeholder="Explique por que esta nota deve entrar no deck"
              required
            />
          </div>

          {emptyFields.length > 0 && (
            <div className="flex gap-2 rounded-lg bg-warning/10 p-3 text-sm">
              <CircleAlert aria-hidden className="mt-0.5 size-4 shrink-0 text-warning" />
              <p>
                Campos vazios sinalizados para revisão: {emptyFields.join(", ")}.
              </p>
            </div>
          )}

          {(formError || submit.isError) && (
            <p role="alert" className="text-sm text-destructive">
              {formError || errorMessage(submit.error)}
            </p>
          )}

          <div className="flex flex-wrap gap-2">
            <Button type="submit" className="min-h-11" disabled={submit.isPending}>
              {submit.isPending ? "Enviando…" : "Enviar sugestão"}
            </Button>
            <Button
              variant="outline"
              className="min-h-11"
              nativeButton={false}
              render={<Link href={`/decks/${id}`} />}
            >
              Cancelar
            </Button>
          </div>
        </form>
      )}
    </main>
  );
}

"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api-client";
import RichTextEditor from "@/components/RichTextEditor";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

// FR-013: categorias estruturadas de mudança
const CATEGORIES = [
  { value: "conteudo_atualizado", label: "Conteúdo atualizado" },
  { value: "ortografia_gramatica", label: "Ortografia/Gramática" },
  { value: "erro_conteudo", label: "Erro de conteúdo" },
  { value: "nova_tag", label: "Nova tag" },
  { value: "tag_atualizada", label: "Tag atualizada" },
  { value: "outro", label: "Outro" },
];

interface NoteDetail {
  id: string;
  field_values: Record<string, string>;
  tags: string[];
}

interface DeckDetail {
  id: string;
  name: string;
}

function HtmlPreview({ html, title }: { html: string; title: string }) {
  return (
    <iframe
      sandbox=""
      title={title}
      srcDoc={`<!doctype html><html><head><meta charset="utf-8"><style>body{margin:0;background:transparent;color:CanvasText;font:16px/1.5 system-ui,sans-serif}</style></head><body>${html}</body></html>`}
      className="h-24 w-full border-0 bg-transparent"
    />
  );
}

function FieldComparison({
  field,
  current,
  proposed,
  changed = true,
}: {
  field: string;
  current: string;
  proposed: string;
  changed?: boolean;
}) {
  return (
    <div className="flex flex-col gap-1">
      <p className="text-sm font-medium">{field}</p>
      <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
        <div
          className={`rounded-lg p-3 ${changed ? "bg-destructive/10" : "bg-muted/40"}`}
        >
          <p className="mb-1 text-sm font-medium text-muted-foreground">
            Atual
          </p>
          <HtmlPreview html={current} title={`${field}: valor atual`} />
        </div>
        <div
          className={`rounded-lg p-3 ${changed ? "bg-success/10" : "bg-muted/40"}`}
        >
          <p className="mb-1 text-sm font-medium text-muted-foreground">
            Sugerido
          </p>
          <HtmlPreview html={proposed} title={`${field}: valor sugerido`} />
        </div>
      </div>
    </div>
  );
}

function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError))
    return "Não foi possível enviar a sugestão.";
  if (error.status === 403) return "Assine o deck para sugerir mudanças.";
  if (error.status === 429)
    return "Você enviou sugestões demais em pouco tempo. Aguarde alguns segundos.";
  const body = error.body as { detail?: string } | null;
  return body?.detail ?? "Não foi possível enviar a sugestão.";
}

export default function SuggestChangePage() {
  const { id, noteId } = useParams<{ id: string; noteId: string }>();

  const { data: deck } = useQuery<DeckDetail>({
    queryKey: ["deck", id],
    queryFn: () => api.get<DeckDetail>(`/decks/${id}/`),
    retry: false,
  });
  const {
    data: note,
    error: noteError,
    isPending,
  } = useQuery<NoteDetail>({
    queryKey: ["note", noteId],
    queryFn: () => api.get<NoteDetail>(`/notes/${noteId}/`),
    retry: false,
  });

  const [category, setCategory] = useState<string | null>(null);
  const [justification, setJustification] = useState("");
  // overlay: só os campos que o usuário editou; o valor efetivo cai no atual da nota
  const [proposed, setProposed] = useState<Record<string, string>>({});
  const [tagsInput, setTagsInput] = useState("");
  const [formError, setFormError] = useState("");
  const [showUnchanged, setShowUnchanged] = useState(false);

  const changedFields = Object.keys(proposed).filter(
    (field) => note && proposed[field] !== note.field_values[field],
  );
  // FR-013 (Nova tag/Tag atualizada): só o que ainda não existe na nota
  const newTags = [
    ...new Set(
      tagsInput
        .split(",")
        .map((tag) => tag.trim())
        .filter(Boolean),
    ),
  ].filter((tag) => !note?.tags.includes(tag));
  const unchangedFields = Object.keys(note?.field_values ?? {}).filter(
    (field) => !changedFields.includes(field),
  );
  const unchangedCount =
    unchangedFields.length + (newTags.length === 0 ? 1 : 0);

  const submit = useMutation({
    mutationFn: () =>
      api.post(`/notes/${noteId}/suggestions/change/`, {
        change_category: category,
        justification,
        proposed_field_values: Object.fromEntries(
          changedFields.map((field) => [field, proposed[field]]),
        ),
        tags: newTags,
      }),
  });

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!category) return setFormError("Escolha o tipo de mudança.");
    if (!justification.trim())
      return setFormError("A justificativa é obrigatória.");
    if (changedFields.length === 0 && newTags.length === 0)
      return setFormError(
        "Altere pelo menos um campo ou adicione uma tag nova para sugerir uma mudança.",
      );
    setFormError("");
    submit.mutate();
  }

  if (noteError instanceof ApiError && noteError.status === 401) {
    return (
      <main className="mx-auto max-w-3xl p-4 md:p-6">
        <p>
          <Link href="/login" className="text-primary underline">
            Entre
          </Link>{" "}
          para sugerir mudanças.
        </p>
      </main>
    );
  }

  if (submit.isSuccess) {
    return (
      <main className="mx-auto max-w-3xl p-4 md:p-6">
        <Alert>
          <AlertTitle>Sugestão enviada</AlertTitle>
          <AlertDescription>
            Sua sugestão está pendente de moderação e já aparece para os
            assinantes do deck.{" "}
            <Link href={`/decks/${id}`} className="text-primary underline">
              Voltar ao deck
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
        / <span className="text-foreground">Sugerir mudança</span>
      </nav>

      <h1 className="mb-6 text-2xl font-semibold tracking-tight">
        Sugerir mudança
      </h1>

      {isPending && (
        <div className="flex flex-col gap-4">
          <Skeleton className="h-8 w-48" />
          <Skeleton className="h-24 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      )}

      {note && (
        <form onSubmit={onSubmit} className="flex flex-col gap-6">
          <div className="flex flex-col gap-2">
            <Label htmlFor="change-category">Tipo de mudança</Label>
            <Select
              value={category}
              onValueChange={setCategory}
              items={CATEGORIES}
            >
              <SelectTrigger id="change-category" className="w-full sm:w-64">
                <SelectValue placeholder="Escolha o tipo" />
              </SelectTrigger>
              <SelectContent>
                {CATEGORIES.map((c) => (
                  <SelectItem key={c.value} value={c.value}>
                    {c.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="flex flex-col gap-2">
            <Label htmlFor="justification">Justificativa</Label>
            <Textarea
              id="justification"
              required
              value={justification}
              onChange={(e) => setJustification(e.target.value)}
              placeholder="Explique por que essa mudança melhora a nota"
            />
          </div>

          {Object.keys(note.field_values).map((field) => (
            <div key={field} className="flex flex-col gap-2">
              <Label>{field}</Label>
              <RichTextEditor
                value={proposed[field] ?? note.field_values[field] ?? ""}
                onChange={(html) =>
                  setProposed((p) => ({ ...p, [field]: html }))
                }
                ariaLabel={`Campo ${field}`}
              />
            </div>
          ))}

          <div className="flex flex-col gap-2">
            <Label htmlFor="proposed-tags">
              Adicionar tags (separadas por vírgula)
            </Label>
            <Input
              id="proposed-tags"
              value={tagsInput}
              onChange={(e) => setTagsInput(e.target.value)}
              placeholder="lei-14133, licitação"
            />
            {note.tags.length > 0 && (
              <p className="text-sm text-muted-foreground">
                Tags atuais: {note.tags.join(", ")}
              </p>
            )}
          </div>

          {(changedFields.length > 0 || newTags.length > 0) && (
            <section
              aria-label="Comparação das mudanças"
              className="flex flex-col gap-4"
            >
              <h2 className="text-lg font-semibold">Comparação</h2>
              {changedFields.map((field) => (
                <FieldComparison
                  key={field}
                  field={field}
                  current={note.field_values[field]}
                  proposed={proposed[field]}
                />
              ))}
              {newTags.length > 0 && (
                <div className="flex flex-col gap-1">
                  <p className="text-sm font-medium">Tags</p>
                  <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                    <div className="rounded-lg bg-destructive/10 p-3">
                      <p className="mb-1 text-sm font-medium text-muted-foreground">
                        Atual
                      </p>
                      <p>{note.tags.join(", ") || "(sem tags)"}</p>
                    </div>
                    <div className="rounded-lg bg-success/10 p-3">
                      <p className="mb-1 text-sm font-medium text-muted-foreground">
                        Sugerido
                      </p>
                      <p>{[...note.tags, ...newTags].join(", ")}</p>
                    </div>
                  </div>
                </div>
              )}
              {unchangedCount > 0 && (
                <Button
                  type="button"
                  variant="outline"
                  className="self-start"
                  aria-expanded={showUnchanged}
                  aria-controls="unchanged-review"
                  onClick={() => setShowUnchanged((visible) => !visible)}
                >
                  {showUnchanged
                    ? "Ocultar itens sem alteração"
                    : `Mostrar itens sem alteração (${unchangedCount})`}
                </Button>
              )}
              {showUnchanged && (
                <div id="unchanged-review" className="flex flex-col gap-4">
                  {unchangedFields.map((field) => (
                    <FieldComparison
                      key={field}
                      field={field}
                      current={note.field_values[field]}
                      proposed={note.field_values[field]}
                      changed={false}
                    />
                  ))}
                  {newTags.length === 0 && (
                    <div className="flex flex-col gap-1">
                      <p className="text-sm font-medium">Tags</p>
                      <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                        {["Atual", "Sugerido"].map((label) => (
                          <div
                            key={label}
                            className="rounded-lg bg-muted/40 p-3"
                          >
                            <p className="mb-1 text-sm font-medium text-muted-foreground">
                              {label}
                            </p>
                            <p>{note.tags.join(", ") || "(sem tags)"}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}
            </section>
          )}

          {(formError || submit.isError) && (
            <p role="alert" className="text-sm text-destructive">
              {formError || errorMessage(submit.error)}
            </p>
          )}

          <div className="flex gap-2">
            <Button type="submit" disabled={submit.isPending}>
              {submit.isPending ? "Enviando…" : "Enviar sugestão"}
            </Button>
            <Button
              variant="outline"
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

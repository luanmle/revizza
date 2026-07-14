"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useInfiniteQuery, useMutation, useQuery } from "@tanstack/react-query";
import { api, ApiError, Paginated } from "@/lib/api-client";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
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

const CATEGORIES = [
  { value: "conteudo_atualizado", label: "Conteúdo atualizado" },
  { value: "ortografia_gramatica", label: "Ortografia/Gramática" },
  { value: "erro_conteudo", label: "Erro de conteúdo" },
  { value: "nova_tag", label: "Nova tag" },
  { value: "tag_atualizada", label: "Tag atualizada" },
  { value: "outro", label: "Outro" },
];

interface NoteItem {
  id: string;
  field_values: Record<string, string>;
  tags: string[];
}

interface DeckDetail {
  id: string;
  name: string;
}

/** Primeiro campo da nota como texto puro, para listar sem renderizar HTML. */
function notePreview(note: NoteItem): string {
  const html = Object.values(note.field_values)[0] ?? "";
  const div = document.createElement("div");
  div.innerHTML = html;
  return div.textContent?.trim() || "(campo vazio)";
}

function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return "Não foi possível enviar a sugestão.";
  if (error.status === 403) return "Assine o deck para sugerir mudanças.";
  if (error.status === 429)
    return "Você enviou sugestões demais em pouco tempo. Aguarde alguns segundos.";
  const body = error.body as { detail?: string } | null;
  return body?.detail ?? "Não foi possível enviar a sugestão.";
}

export default function SuggestBulkPage() {
  const { id } = useParams<{ id: string }>();

  const { data: deck } = useQuery<DeckDetail>({
    queryKey: ["deck", id],
    queryFn: () => api.get<DeckDetail>(`/decks/${id}/`),
    retry: false,
  });

  const [q, setQ] = useState("");
  const [qInput, setQInput] = useState("");
  const notesQuery = useInfiniteQuery({
    queryKey: ["deck-notes", id, q],
    queryFn: ({ pageParam }) =>
      api.get<Paginated<NoteItem>>(
        `/decks/${id}/notes/${pageParam ?? (q ? `?q=${encodeURIComponent(q)}` : "")}`,
      ),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) => (last.next ? new URL(last.next).search : undefined),
    retry: false,
  });

  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [category, setCategory] = useState<string | null>(null);
  const [justification, setJustification] = useState("");
  const [tagsInput, setTagsInput] = useState("");
  const [formError, setFormError] = useState("");

  // FR-017/FR-013: a correção compartilhada do lote são as tags propostas
  // (edição compartilhada de campos fica com a T118)
  const proposedTags = [
    ...new Set(tagsInput.split(",").map((tag) => tag.trim()).filter(Boolean)),
  ];

  const notes = notesQuery.data?.pages.flatMap((p) => p.results) ?? [];

  function toggle(noteId: string, checked: boolean) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (checked) next.add(noteId);
      else next.delete(noteId);
      return next;
    });
  }

  const submit = useMutation({
    mutationFn: () =>
      api.post("/suggestions/bulk-change/", {
        note_ids: [...selected],
        change_category: category,
        justification,
        tags: proposedTags,
      }),
  });

  function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (selected.size === 0) return setFormError("Selecione pelo menos uma nota.");
    if (!category) return setFormError("Escolha o tipo de mudança.");
    if (!justification.trim()) return setFormError("A justificativa é obrigatória.");
    if (proposedTags.length === 0)
      return setFormError("Informe pelo menos uma tag para aplicar às notas.");
    setFormError("");
    submit.mutate();
  }

  if (notesQuery.error instanceof ApiError && notesQuery.error.status === 401) {
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
          <AlertTitle>Sugestão em lote enviada</AlertTitle>
          <AlertDescription>
            Uma única sugestão cobrindo {selected.size} nota(s) está pendente de
            moderação.{" "}
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
      <nav aria-label="Trilha de navegação" className="mb-4 text-sm text-muted-foreground">
        <Link href="/decks" className="hover:text-foreground">
          Catálogo
        </Link>{" "}
        /{" "}
        <Link href={`/decks/${id}`} className="hover:text-foreground">
          {deck?.name ?? "Deck"}
        </Link>{" "}
        / <span className="text-foreground">Sugestão em lote</span>
      </nav>

      <h1 className="mb-2 text-2xl font-semibold tracking-tight">Sugestão em lote</h1>
      <p className="mb-6 text-sm text-muted-foreground">
        O mesmo tipo de mudança, tags e justificativa serão aplicados a todas as
        notas selecionadas, em uma única sugestão.
      </p>

      <form onSubmit={onSubmit} className="flex flex-col gap-6">
        <div className="flex flex-col gap-2">
          <Label htmlFor="note-search">Buscar notas</Label>
          <div className="flex gap-2">
            <Input
              id="note-search"
              type="search"
              value={qInput}
              onChange={(e) => setQInput(e.target.value)}
              placeholder="Termo ou trecho da nota"
            />
            <Button
              type="button"
              variant="outline"
              onClick={() => setQ(qInput.trim())}
            >
              Buscar
            </Button>
          </div>
        </div>

        <fieldset className="flex flex-col gap-1">
          <legend className="mb-2 text-sm font-medium">
            Notas ({selected.size} selecionada{selected.size === 1 ? "" : "s"})
          </legend>
          {notesQuery.isPending && (
            <div className="flex flex-col gap-2">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          )}
          {notes.map((note) => (
            <label
              key={note.id}
              className="flex min-h-10 cursor-pointer items-center gap-3 rounded-lg border p-2 hover:bg-muted"
            >
              <Checkbox
                checked={selected.has(note.id)}
                onCheckedChange={(checked) => toggle(note.id, checked === true)}
              />
              <span className="line-clamp-1 text-sm">{notePreview(note)}</span>
            </label>
          ))}
          {!notesQuery.isPending && notes.length === 0 && (
            <p className="py-6 text-center text-sm text-muted-foreground">
              Nenhuma nota encontrada.
            </p>
          )}
          {notesQuery.hasNextPage && (
            <Button
              type="button"
              variant="outline"
              className="mt-2"
              disabled={notesQuery.isFetching}
              onClick={() => notesQuery.fetchNextPage()}
            >
              Carregar mais
            </Button>
          )}
        </fieldset>

        <div className="flex flex-col gap-2">
          <Label htmlFor="change-category">Tipo de mudança</Label>
          <Select value={category} onValueChange={setCategory} items={CATEGORIES}>
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
          <Label htmlFor="proposed-tags">
            Tags a aplicar (separadas por vírgula)
          </Label>
          <Input
            id="proposed-tags"
            value={tagsInput}
            onChange={(e) => setTagsInput(e.target.value)}
            placeholder="lei-14133, licitação"
          />
        </div>

        <div className="flex flex-col gap-2">
          <Label htmlFor="justification">Justificativa</Label>
          <Textarea
            id="justification"
            required
            value={justification}
            onChange={(e) => setJustification(e.target.value)}
            placeholder="Explique a mudança que se aplica a todas as notas selecionadas"
          />
        </div>

        {(formError || submit.isError) && (
          <p role="alert" className="text-sm text-destructive">
            {formError || errorMessage(submit.error)}
          </p>
        )}

        <div className="flex gap-2">
          <Button type="submit" disabled={submit.isPending}>
            {submit.isPending ? "Enviando…" : "Enviar sugestão em lote"}
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
    </main>
  );
}

"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api-client";
import RichTextEditor from "@/components/RichTextEditor";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";

interface DeckDetail {
  id: string;
  name: string;
  description: string;
  subject_tags: string[];
  is_moderator: boolean;
}

function errorMessage(error: unknown): string {
  if (!(error instanceof ApiError)) return "Não foi possível salvar as alterações.";
  if (error.status === 403)
    return "Apenas moderadores ativos podem editar este deck.";
  const detail = (error.body as { detail?: string } | null)?.detail;
  return detail ?? "Revise os campos antes de tentar novamente.";
}

export default function EditDeckPage() {
  const { id } = useParams<{ id: string }>();

  const deck = useQuery<DeckDetail>({
    queryKey: ["deck", id],
    queryFn: () => api.get(`/decks/${id}/`),
    retry: false,
  });

  if (deck.error instanceof ApiError && deck.error.status === 401) {
    return (
      <main className="mx-auto max-w-3xl p-4 md:p-6">
        <p>
          <Link href="/login" className="text-primary underline">
            Entre
          </Link>{" "}
          para editar este deck.
        </p>
      </main>
    );
  }

  if (deck.data && !deck.data.is_moderator) {
    return (
      <main className="mx-auto max-w-3xl p-4 md:p-6">
        <Alert variant="destructive">
          <AlertTitle>Sem permissão</AlertTitle>
          <AlertDescription>
            Apenas moderadores ativos podem editar este deck.
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
        / <span className="text-foreground">Editar deck</span>
      </nav>

      <h1 className="mb-6 text-2xl font-semibold tracking-tight">
        Editar deck
      </h1>

      {deck.isPending && (
        <div className="flex flex-col gap-4">
          <Skeleton className="h-11 w-full" />
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-11 w-full" />
        </div>
      )}

      {deck.isError &&
        !(deck.error instanceof ApiError && deck.error.status === 401) && (
          <Alert variant="destructive">
            <AlertTitle>Não foi possível carregar o deck</AlertTitle>
            <AlertDescription>Tente novamente em instantes.</AlertDescription>
          </Alert>
        )}

      {deck.data && deck.data.is_moderator && (
        <EditForm id={id} deck={deck.data} />
      )}
    </main>
  );
}

function EditForm({ id, deck }: { id: string; deck: DeckDetail }) {
  const router = useRouter();
  const [name, setName] = useState(deck.name);
  const [description, setDescription] = useState(deck.description);
  const [tagsInput, setTagsInput] = useState(deck.subject_tags.join(", "));

  const submit = useMutation({
    mutationFn: () =>
      api.patch(`/decks/${id}/`, {
        name,
        description,
        subject_tags: tagsInput
          .split(",")
          .map((tag) => tag.trim())
          .filter(Boolean),
      }),
    onSuccess: () => router.push(`/decks/${id}`),
  });

  function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    submit.mutate();
  }

  return (
    <form className="flex flex-col gap-6" onSubmit={onSubmit}>
      <div className="flex flex-col gap-2">
        <Label htmlFor="deck-name">Título</Label>
        <Input
          id="deck-name"
          value={name}
          onChange={(event) => setName(event.target.value)}
          required
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label>Descrição</Label>
        <RichTextEditor
          value={description}
          onChange={setDescription}
          ariaLabel="Descrição do deck"
        />
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="deck-tags">Tags</Label>
        <Input
          id="deck-tags"
          value={tagsInput}
          onChange={(event) => setTagsInput(event.target.value)}
          placeholder="Ex.: direito, licitação, revisão"
        />
        <p className="text-sm text-muted-foreground">
          Separe as tags por vírgulas.
        </p>
      </div>

      {submit.isError && (
        <p role="alert" className="text-sm text-destructive">
          {errorMessage(submit.error)}
        </p>
      )}

      <div className="flex flex-wrap gap-2">
        <Button type="submit" className="min-h-11" disabled={submit.isPending}>
          {submit.isPending ? "Salvando…" : "Salvar alterações"}
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
  );
}

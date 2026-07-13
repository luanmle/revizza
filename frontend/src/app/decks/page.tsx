"use client";

import { useState } from "react";
import Link from "next/link";
import { useInfiniteQuery } from "@tanstack/react-query";
import { Layers3, Search } from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
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

  const {
    data,
    error,
    fetchNextPage,
    hasNextPage,
    isFetching,
    isPending,
    refetch,
  } = useInfiniteQuery({
    queryKey: ["decks", tag],
    queryFn: ({ pageParam }) =>
      api.get<Paginated<Deck>>(
        `/decks/${pageParam ?? (tag ? `?tag=${encodeURIComponent(tag)}` : "")}`,
      ),
    initialPageParam: undefined as string | undefined,
    // o cursor vem embutido na URL `next` (convenção AnkiHub)
    getNextPageParam: (last) =>
      last.next ? new URL(last.next).search : undefined,
    retry: false,
  });

  if (error instanceof ApiError && error.status === 401) {
    return (
      <main className="mx-auto w-full max-w-3xl p-4 md:p-6">
        <Alert>
          <AlertDescription>
            <Link href="/login">Entre</Link> para explorar o catálogo de decks.
          </AlertDescription>
        </Alert>
      </main>
    );
  }

  const decks = data?.pages.flatMap((page) => page.results) ?? [];

  return (
    <main className="mx-auto w-full max-w-3xl p-4 md:p-6">
      <h1 className="mb-2 text-2xl font-semibold tracking-tight">
        Catálogo de decks
      </h1>
      <p className="mb-6 max-w-[70ch] text-sm text-muted-foreground">
        Encontre conteúdo por matéria ou tag e acompanhe atualizações da
        comunidade.
      </p>
      <form
        className="mb-6 flex flex-col gap-3 rounded-lg border bg-card p-4 sm:flex-row sm:items-end"
        onSubmit={(e) => {
          e.preventDefault();
          setTag(tagInput.trim());
        }}
      >
        <div className="grid flex-1 gap-2">
          <Label htmlFor="deck-tag">Filtrar por matéria ou tag</Label>
          <Input
            id="deck-tag"
            type="search"
            value={tagInput}
            onChange={(e) => setTagInput(e.target.value)}
            placeholder="Ex.: Direito Constitucional"
          />
        </div>
        <Button type="submit" variant="outline" size="lg">
          <Search aria-hidden />
          Filtrar
        </Button>
      </form>

      {error && !(error instanceof ApiError && error.status === 401) && (
        <Alert variant="destructive" className="mb-6">
          <AlertTitle>Não foi possível carregar os decks</AlertTitle>
          <AlertDescription>
            Tente novamente em instantes.
            <Button
              variant="outline"
              className="mt-4"
              onClick={() => refetch()}
            >
              Tentar novamente
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {isPending && (
        <div
          className="grid gap-4 sm:grid-cols-2"
          aria-label="Carregando decks"
        >
          {[0, 1, 2, 3].map((item) => (
            <Skeleton key={item} className="h-40 w-full" />
          ))}
        </div>
      )}

      <ul className="grid gap-4 sm:grid-cols-2">
        {decks.map((deck) => (
          <li key={deck.id}>
            <Card className="relative h-full transition-colors hover:bg-muted/30">
              <CardHeader>
                <CardTitle>
                  <Link
                    href={`/decks/${deck.id}`}
                    className="after:absolute after:inset-0"
                  >
                    {deck.name}
                  </Link>
                </CardTitle>
                <CardDescription>
                  {deck.note_count} {deck.note_count === 1 ? "nota" : "notas"} ·{" "}
                  {deck.subscriber_count}{" "}
                  {deck.subscriber_count === 1 ? "assinante" : "assinantes"}
                </CardDescription>
              </CardHeader>
              {deck.subject_tags.length > 0 && (
                <CardContent className="flex flex-wrap gap-2">
                  {deck.subject_tags.map((subjectTag) => (
                    <Badge key={subjectTag} variant="secondary">
                      {subjectTag}
                    </Badge>
                  ))}
                </CardContent>
              )}
            </Card>
          </li>
        ))}
      </ul>
      {decks.length === 0 && !isFetching && !error && (
        <div className="rounded-lg border border-dashed p-8 text-center">
          <Layers3
            className="mx-auto mb-3 size-8 text-muted-foreground"
            aria-hidden
          />
          <h2 className="text-lg font-medium">Nenhum deck encontrado</h2>
          <p className="mt-1 text-sm text-muted-foreground">
            Tente uma matéria ou tag diferente.
          </p>
        </div>
      )}
      {hasNextPage && (
        <div className="mt-6 text-center">
          <Button
            variant="outline"
            onClick={() => fetchNextPage()}
            disabled={isFetching}
          >
            {isFetching ? "Carregando…" : "Carregar mais"}
          </Button>
        </div>
      )}
    </main>
  );
}

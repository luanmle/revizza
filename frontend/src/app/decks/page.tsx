"use client";

import { Suspense, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useInfiniteQuery } from "@tanstack/react-query";
import { BadgeCheck, Clock3, Layers3, Search } from "lucide-react";
import { UserAvatar } from "@/components/user-avatar";
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
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { api, ApiError, Paginated } from "@/lib/api-client";
import { formatRelativeDate } from "@/lib/format-relative-date";

type CatalogTab = "catalog" | "moderated" | "subscribed";
type CatalogSort = "recommended" | "popular" | "updated" | "notes" | "recent";

interface UserSummary {
  id: string;
  name: string;
  avatar_url: string | null;
}

interface Deck {
  id: string;
  name: string;
  description: string;
  subject_tags: string[];
  note_count: number;
  subscriber_count: number;
  creator: UserSummary | null;
  is_official: boolean;
  last_updated_at: string;
}

const tabs: { value: CatalogTab; label: string }[] = [
  { value: "catalog", label: "Catálogo" },
  { value: "moderated", label: "Meus baralhos" },
  { value: "subscribed", label: "Inscritos" },
];
const sorts: { value: CatalogSort; label: string }[] = [
  { value: "recommended", label: "Recomendados" },
  { value: "popular", label: "Mais populares" },
  { value: "updated", label: "Atualizados recentemente" },
  { value: "notes", label: "Mais notas" },
  { value: "recent", label: "Recentes" },
];

function CatalogSkeleton() {
  return (
    <div
      role="status"
      className="grid gap-4 sm:grid-cols-2"
      aria-label="Carregando decks"
    >
      {[0, 1, 2, 3].map((item) => (
        <Skeleton key={item} className="h-52 w-full" />
      ))}
    </div>
  );
}

function DeckCatalog() {
  const searchParams = useSearchParams();
  const tabParam = searchParams.get("tab");
  const sortParam = searchParams.get("sort");
  const tab = tabs.some((item) => item.value === tabParam)
    ? (tabParam as CatalogTab)
    : "catalog";
  const sort = sorts.some((item) => item.value === sortParam)
    ? (sortParam as CatalogSort)
    : "recommended";
  const tag = searchParams.get("tag") ?? "";
  const [tagInput, setTagInput] = useState(tag);

  function updateUrl(values: Partial<Record<"tab" | "tag" | "sort", string>>) {
    const params = new URLSearchParams(searchParams.toString());
    for (const [key, value] of Object.entries(values)) {
      if (
        !value ||
        (key === "tab" && value === "catalog") ||
        (key === "sort" && value === "recommended")
      ) {
        params.delete(key);
      } else {
        params.set(key, value);
      }
    }
    window.history.pushState(null, "", params.size ? `?${params}` : "/decks");
  }

  const query = useInfiniteQuery({
    queryKey: ["decks", { tab, tag, sort }],
    queryFn: ({ pageParam }) => {
      const params = new URLSearchParams();
      if (tab !== "catalog") params.set(tab, "1");
      if (tag) params.set("tag", tag);
      if (sort !== "recommended") params.set("sort", sort);
      return api.get<Paginated<Deck>>(
        `/decks/${pageParam ?? (params.size ? `?${params}` : "")}`,
      );
    },
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (last) =>
      last.next ? new URL(last.next).search : undefined,
    retry: false,
  });
  const decks = query.data?.pages.flatMap((page) => page.results) ?? [];
  const unauthorized =
    query.error instanceof ApiError && query.error.status === 401;
  const empty = {
    catalog: ["Nenhum deck encontrado", "Tente uma matéria ou tag diferente."],
    moderated: [
      "Nenhum deck moderado",
      "Decks que você modera aparecerão aqui.",
    ],
    subscribed: [
      "Nenhum deck inscrito",
      "Assine um deck do catálogo para encontrá-lo aqui.",
    ],
  }[tab];

  return (
    <main className="mx-auto w-full max-w-3xl p-4 md:p-6">
      <h1 className="mb-2 text-2xl font-semibold tracking-tight">
        Catálogo de decks
      </h1>
      <p className="mb-5 max-w-[70ch] text-sm text-muted-foreground">
        Encontre conteúdo por matéria ou tag e acompanhe atualizações da
        comunidade.
      </p>

      <Tabs
        value={tab}
        onValueChange={(value) => updateUrl({ tab: String(value) })}
        className="mb-5"
      >
        <TabsList className="h-10 w-full">
          {tabs.map((item) => (
            <TabsTrigger
              key={item.value}
              value={item.value}
              className="min-w-0 px-2"
            >
              {item.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <div className="mb-6 flex flex-col gap-3 border-b pb-6 sm:flex-row sm:items-end">
        <form
          className="flex min-w-0 flex-1 flex-col gap-2 sm:flex-row sm:items-end"
          onSubmit={(event) => {
            event.preventDefault();
            updateUrl({ tag: tagInput.trim() });
          }}
        >
          <div className="grid min-w-0 flex-1 gap-2">
            <Label htmlFor="deck-tag">Filtrar por matéria ou tag</Label>
            <Input
              id="deck-tag"
              type="search"
              value={tagInput}
              onChange={(event) => setTagInput(event.target.value)}
              placeholder="Ex.: Direito Constitucional"
            />
          </div>
          <Button type="submit" variant="outline" className="h-10">
            <Search aria-hidden /> Filtrar
          </Button>
        </form>
        <div className="grid gap-2 sm:w-56">
          <Label htmlFor="catalog-sort">Ordenar por</Label>
          <Select
            value={sort}
            onValueChange={(value) => updateUrl({ sort: String(value) })}
            items={sorts}
          >
            <SelectTrigger
              id="catalog-sort"
              className="h-10 w-full"
              aria-label="Ordenar por"
            >
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {sorts.map((item) => (
                <SelectItem key={item.value} value={item.value}>
                  {item.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {unauthorized && (
        <Alert className="mb-6">
          <AlertTitle>Entre para acessar esta aba</AlertTitle>
          <AlertDescription>
            <Link
              href="/login"
              className="font-medium text-primary underline-offset-4 hover:underline"
            >
              Entrar
            </Link>{" "}
            para ver seus decks pessoais.
          </AlertDescription>
        </Alert>
      )}
      {query.error && !unauthorized && (
        <Alert variant="destructive" className="mb-6">
          <AlertTitle>Não foi possível carregar os decks</AlertTitle>
          <AlertDescription>
            Tente novamente em instantes.
            <Button
              variant="outline"
              className="mt-4"
              onClick={() => query.refetch()}
            >
              Tentar novamente
            </Button>
          </AlertDescription>
        </Alert>
      )}
      {query.isPending && <CatalogSkeleton />}

      <ul className="grid gap-4 sm:grid-cols-2">
        {decks.map((deck) => (
          <li key={deck.id}>
            <Card className="relative h-full transition-colors duration-150 hover:bg-muted/30">
              <CardHeader className="gap-3">
                <div className="flex items-start justify-between gap-2">
                  <CardTitle className="min-w-0 break-words">
                    <Link
                      href={`/decks/${deck.id}`}
                      className="after:absolute after:inset-0"
                    >
                      {deck.name}
                    </Link>
                  </CardTitle>
                  {deck.is_official && (
                    <Badge className="shrink-0">
                      <BadgeCheck aria-hidden /> Oficial
                    </Badge>
                  )}
                </div>
                <CardDescription>
                  {deck.note_count} {deck.note_count === 1 ? "nota" : "notas"} ·{" "}
                  {deck.subscriber_count}{" "}
                  {deck.subscriber_count === 1 ? "assinante" : "assinantes"}
                </CardDescription>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <UserAvatar
                    avatarUrl={deck.creator?.avatar_url}
                    name={deck.creator?.name}
                  />
                  <span className="min-w-0 truncate">
                    {deck.creator?.name || "Autoria indisponível"}
                  </span>
                </div>
                <p className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Clock3 aria-hidden className="size-4" /> Atualizado{" "}
                  {formatRelativeDate(deck.last_updated_at)}
                </p>
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

      {decks.length === 0 && !query.isFetching && !query.error && (
        <div className="py-10 text-center">
          <Layers3
            className="mx-auto mb-3 size-8 text-muted-foreground"
            aria-hidden
          />
          <h2 className="text-lg font-medium">{empty[0]}</h2>
          <p className="mt-1 text-sm text-muted-foreground">{empty[1]}</p>
        </div>
      )}
      {query.hasNextPage && (
        <div className="mt-6 text-center">
          <Button
            variant="outline"
            onClick={() => query.fetchNextPage()}
            disabled={query.isFetching}
          >
            {query.isFetching ? "Carregando…" : "Carregar mais"}
          </Button>
        </div>
      )}
    </main>
  );
}

export default function DecksPage() {
  return (
    <Suspense
      fallback={
        <main className="mx-auto w-full max-w-3xl p-4 md:p-6">
          <CatalogSkeleton />
        </main>
      }
    >
      <DeckCatalog />
    </Suspense>
  );
}

"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { UserPlus, UserRoundCheck, UserRoundX } from "lucide-react";
import { api, ApiError, type Paginated } from "@/lib/api-client";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";

interface DeckDetail {
  id: string;
  name: string;
}

interface Moderator {
  id: string;
  user_id: string;
  email: string;
  status: "active" | "pending";
  created_at: string;
}

function nextPath(next: string | null): string | null {
  if (!next) return null;
  const marker = "/api/v1";
  return next.slice(next.indexOf(marker) + marker.length);
}

function mutationError(error: unknown): string {
  if (error instanceof ApiError) {
    const body = error.body as { detail?: string } | null;
    if (body?.detail) return body.detail;
  }
  return "Não foi possível concluir a ação. Tente novamente.";
}

export default function ModeratorsPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();
  const [email, setEmail] = useState("");

  const me = useQuery<{ id: string }>({
    queryKey: ["me"],
    queryFn: () => api.get("/accounts/me/"),
    retry: false,
  });
  const deck = useQuery<DeckDetail>({
    queryKey: ["deck", id],
    queryFn: () => api.get(`/decks/${id}/`),
    retry: false,
  });
  const moderators = useInfiniteQuery({
    queryKey: ["moderators", id],
    queryFn: ({ pageParam }) => api.get<Paginated<Moderator>>(pageParam),
    initialPageParam: `/decks/${id}/moderators/`,
    getNextPageParam: (lastPage) => nextPath(lastPage.next),
    retry: false,
  });
  const refresh = () =>
    queryClient.invalidateQueries({ queryKey: ["moderators", id] });

  const invite = useMutation({
    mutationFn: () =>
      api.post(`/decks/${id}/moderators/`, { email: email.trim() }),
    onSuccess: () => {
      setEmail("");
      refresh();
    },
  });
  const accept = useMutation({
    mutationFn: (inviteId: string) =>
      api.post(`/deck-moderator-invites/${inviteId}/accept/`),
    onSuccess: refresh,
  });
  const remove = useMutation({
    mutationFn: (userId: string) =>
      api.delete(`/decks/${id}/moderators/${userId}/`),
    onSuccess: refresh,
  });

  const results = moderators.data?.pages.flatMap((page) => page.results) ?? [];
  const isModerator = results.some(
    (moderator) =>
      moderator.user_id === me.data?.id && moderator.status === "active",
  );
  const error = deck.error || moderators.error;

  if (error instanceof ApiError && error.status === 401) {
    return (
      <main className="mx-auto max-w-3xl p-4 md:p-6">
        <p>
          <Link href="/login" className="text-primary underline">
            Entre
          </Link>{" "}
          para ver os moderadores.
        </p>
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
        / <span className="text-foreground">Moderadores</span>
      </nav>

      <h1 className="mb-2 text-2xl font-semibold tracking-tight">Moderadores</h1>
      <p className="mb-6 max-w-[70ch] text-sm text-muted-foreground">
        Moderadores ativos têm o mesmo nível de permissão para revisar sugestões.
      </p>

      {isModerator && (
        <form
          className="mb-8 flex flex-col gap-2 border-b pb-8"
          onSubmit={(event) => {
            event.preventDefault();
            if (email.trim()) invite.mutate();
          }}
        >
          <Label htmlFor="moderator-email">Convidar por e-mail</Label>
          <div className="flex flex-col gap-2 sm:flex-row">
            <Input
              id="moderator-email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="pessoa@example.com"
              className="min-h-11"
              required
            />
            <Button
              type="submit"
              className="min-h-11"
              disabled={invite.isPending}
            >
              <UserPlus aria-hidden />
              {invite.isPending ? "Convidando…" : "Convidar"}
            </Button>
          </div>
          {invite.isError && (
            <p role="alert" className="text-sm text-destructive">
              {mutationError(invite.error)}
            </p>
          )}
        </form>
      )}

      <section aria-labelledby="moderator-list-title">
        <h2 id="moderator-list-title" className="mb-4 text-lg font-semibold">
          Equipe de curadoria
        </h2>

        {moderators.isPending && (
          <div className="flex flex-col gap-3">
            <Skeleton className="h-16 w-full" />
            <Skeleton className="h-16 w-full" />
          </div>
        )}

        {error && !(error instanceof ApiError && error.status === 401) && (
          <Alert variant="destructive">
            <AlertTitle>Não foi possível carregar os moderadores</AlertTitle>
            <AlertDescription>
              Confirme que você assina este deck e tente novamente.
            </AlertDescription>
          </Alert>
        )}

        <ul className="divide-y">
          {results.map((moderator) => {
            const own = moderator.user_id === me.data?.id;
            return (
              <li
                key={moderator.id}
                className="flex flex-col gap-3 py-4 first:pt-0 sm:flex-row sm:items-center"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate font-medium">
                    {own ? `${moderator.email} (você)` : moderator.email}
                  </p>
                  <Badge
                    variant={moderator.status === "active" ? "secondary" : "outline"}
                    className="mt-1 rounded-full"
                  >
                    {moderator.status === "active" ? "Ativo" : "Convite pendente"}
                  </Badge>
                </div>

                {own && moderator.status === "pending" && (
                  <Button
                    type="button"
                    className="min-h-11"
                    disabled={accept.isPending}
                    onClick={() => accept.mutate(moderator.id)}
                  >
                    <UserRoundCheck aria-hidden /> Aceitar convite
                  </Button>
                )}

                {isModerator && !(own && moderator.status === "pending") && (
                  <Button
                    type="button"
                    variant="destructive"
                    className="min-h-11"
                    disabled={remove.isPending}
                    onClick={() => {
                      if (window.confirm(`Remover ${moderator.email} da moderação?`)) {
                        remove.mutate(moderator.user_id);
                      }
                    }}
                  >
                    <UserRoundX aria-hidden /> Remover
                  </Button>
                )}
              </li>
            );
          })}
        </ul>

        {(accept.isError || remove.isError) && (
          <p role="alert" className="mt-3 text-sm text-destructive">
            {mutationError(accept.error || remove.error)}
          </p>
        )}

        {moderators.hasNextPage && (
          <Button
            variant="outline"
            className="mt-4 min-h-11"
            disabled={moderators.isFetchingNextPage}
            onClick={() => moderators.fetchNextPage()}
          >
            {moderators.isFetchingNextPage ? "Carregando…" : "Carregar mais"}
          </Button>
        )}
      </section>
    </main>
  );
}

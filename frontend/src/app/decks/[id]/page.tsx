"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  AlertTriangle,
  DownloadCloud,
  FilePlus2,
  FileText,
  ListChecks,
  MessageSquareText,
  Settings2,
  ShieldCheck,
  Users,
} from "lucide-react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api-client";

interface DeckDetail {
  id: string;
  name: string;
  description: string;
  subject_tags: string[];
  note_count: number;
  subscriber_count: number;
  moderator_count: number;
  is_moderator: boolean;
  is_subscribed: boolean;
  sync_status: "not_synced_yet" | "up_to_date" | "out_of_date" | null;
}

export default function DeckDetailPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const {
    data: deck,
    error,
    refetch,
  } = useQuery<DeckDetail>({
    queryKey: ["deck", id],
    queryFn: () => api.get<DeckDetail>(`/decks/${id}/`),
    retry: false,
  });

  const invalidate = () =>
    queryClient.invalidateQueries({ queryKey: ["deck", id] });
  const subscribe = useMutation({
    mutationFn: () => api.post(`/decks/${id}/subscriptions/`),
    onSuccess: invalidate,
  });
  const unsubscribe = useMutation({
    mutationFn: () => api.delete(`/decks/${id}/subscriptions/me/`),
    onSuccess: invalidate,
  });

  if (error instanceof ApiError && error.status === 401) {
    return (
      <main className="mx-auto w-full max-w-3xl p-4 md:p-6">
        <Alert>
          <AlertDescription>
            <Link href="/login">Entre</Link> para ver este deck.
          </AlertDescription>
        </Alert>
      </main>
    );
  }
  if (error) {
    return (
      <main className="mx-auto w-full max-w-3xl p-4 md:p-6">
        <Alert variant="destructive">
          <AlertTitle>Não foi possível carregar o deck</AlertTitle>
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
      </main>
    );
  }
  if (!deck) {
    return (
      <main className="mx-auto w-full max-w-3xl p-4 md:p-6">
        <span className="sr-only">Carregando deck…</span>
        <Skeleton className="mb-4 h-5 w-40" />
        <Skeleton className="mb-4 h-10 w-2/3" />
        <Skeleton className="h-72 w-full" />
      </main>
    );
  }

  const busy = subscribe.isPending || unsubscribe.isPending;

  return (
    <main className="mx-auto w-full max-w-3xl p-4 md:p-6">
      <nav
        aria-label="Trilha de navegação"
        className="mb-4 text-sm text-muted-foreground"
      >
        <Link href="/decks" className="hover:text-foreground">
          Catálogo
        </Link>{" "}
        / <span className="text-foreground">{deck.name}</span>
      </nav>

      <div className="mb-6 flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight">{deck.name}</h1>
          {deck.description && (
            <p className="mt-2 max-w-[70ch] text-muted-foreground">
              {deck.description}
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          {deck.is_moderator && (
            <Button
              variant="outline"
              size="lg"
              nativeButton={false}
              render={<Link href={`/decks/${id}/edit`} />}
            >
              Editar deck
            </Button>
          )}
          {deck.is_subscribed ? (
            <Button
              variant="outline"
              size="lg"
              onClick={() => unsubscribe.mutate()}
              disabled={busy}
            >
              {unsubscribe.isPending ? "Cancelando…" : "Cancelar inscrição"}
            </Button>
          ) : (
            <Button size="lg" onClick={() => subscribe.mutate()} disabled={busy}>
              {subscribe.isPending ? "Inscrevendo…" : "Inscrever-se"}
            </Button>
          )}
        </div>
      </div>

      <div className="mb-6 flex flex-wrap gap-2">
        {deck.subject_tags.map((subjectTag) => (
          <Badge key={subjectTag} variant="secondary">
            {subjectTag}
          </Badge>
        ))}
      </div>

      <Card className="mb-6">
        <CardContent className="flex flex-wrap gap-x-6 gap-y-3 pt-1 text-sm text-muted-foreground">
          <span className="inline-flex items-center gap-2">
            <FileText aria-hidden />
            {deck.note_count} {deck.note_count === 1 ? "nota" : "notas"}
          </span>
          <span className="inline-flex items-center gap-2">
            <Users aria-hidden />
            {deck.subscriber_count}{" "}
            {deck.subscriber_count === 1 ? "assinante" : "assinantes"}
          </span>
          <span className="inline-flex items-center gap-2">
            <ShieldCheck aria-hidden />
            {deck.moderator_count}{" "}
            {deck.moderator_count === 1 ? "moderador" : "moderadores"}
          </span>
        </CardContent>
      </Card>

      {deck.sync_status === "not_synced_yet" && (
        <Alert className="mb-6">
          <DownloadCloud aria-hidden />
          <AlertTitle>Ainda não sincronizado</AlertTitle>
          <AlertDescription>
            Instale e configure o add-on do AnkiHub Brasil no seu Anki, entre com sua
            conta e sincronize para trazer este deck para o seu computador.
          </AlertDescription>
        </Alert>
      )}

      {deck.sync_status === "out_of_date" && (
        <Alert className="mb-6 border-warning/40 bg-warning/10">
          <AlertTriangle aria-hidden className="text-warning" />
          <AlertTitle>Desatualizado</AlertTitle>
          <AlertDescription>
            Este deck tem mudanças novas desde sua última sincronização. Sincronize pelo
            add-on para trazê-las ao seu Anki.
          </AlertDescription>
        </Alert>
      )}

      {(subscribe.isError || unsubscribe.isError) && (
        <p role="alert" className="mb-4 text-sm text-destructive">
          Não foi possível alterar sua inscrição. Tente novamente.
        </p>
      )}

      <section aria-labelledby="deck-actions-title">
        <h2 id="deck-actions-title" className="mb-3 text-lg font-semibold">
          Conteúdo e comunidade
        </h2>
        <div className="grid gap-3 sm:grid-cols-2">
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <FileText aria-hidden /> Notas
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Button
                variant="outline"
                className="w-full"
                nativeButton={false}
                render={<Link href={`/decks/${id}/notes`} />}
              >
                Explorar notas
              </Button>
            </CardContent>
          </Card>
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <MessageSquareText aria-hidden /> Sugestões
              </CardTitle>
            </CardHeader>
            <CardContent>
              <Button
                variant="outline"
                className="w-full"
                nativeButton={false}
                render={<Link href={`/decks/${id}/suggestions`} />}
              >
                Ver sugestões
              </Button>
            </CardContent>
          </Card>
        </div>
      </section>

      {deck.is_subscribed && (
        <section aria-labelledby="subscriber-actions-title" className="mt-8">
          <h2
            id="subscriber-actions-title"
            className="mb-3 text-lg font-semibold"
          >
            Ações de assinante
          </h2>
          <div className="grid gap-2 sm:grid-cols-2">
            <Button
              variant="outline"
              nativeButton={false}
              render={<Link href={`/decks/${id}/suggest-new-note`} />}
            >
              <FilePlus2 aria-hidden /> Sugerir nota nova
            </Button>
            <Button
              variant="outline"
              nativeButton={false}
              render={<Link href={`/decks/${id}/suggest-bulk`} />}
            >
              <ListChecks aria-hidden /> Sugerir alteração em lote
            </Button>
            <Button
              variant="outline"
              nativeButton={false}
              render={<Link href={`/decks/${id}/protection`} />}
            >
              <Settings2 aria-hidden /> Proteção pessoal
            </Button>
            <Button
              variant="outline"
              nativeButton={false}
              render={<Link href={`/decks/${id}/moderators`} />}
            >
              <Users aria-hidden /> Ver moderadores
            </Button>
          </div>
        </section>
      )}
    </main>
  );
}

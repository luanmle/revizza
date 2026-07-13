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
import { Inbox, MessageSquare, ThumbsDown, ThumbsUp } from "lucide-react";
import { api, ApiError, type Paginated } from "@/lib/api-client";
import SuggestionModerationControls from "@/components/SuggestionModerationControls";
import ReportButton from "@/components/ReportButton";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface Suggestion {
  id: string;
  type: "change" | "new_note" | "deletion";
  status: "pending" | "accepted" | "rejected";
  author: string | null;
  change_category: string | null;
  justification: string;
  proposed_field_values: Record<string, string> | null;
  tags: string[];
  empty_fields: string[];
  note_ids: string[];
  likes_count: number;
  dislikes_count: number;
  rejection_reason: string | null;
  created_at: string;
}

interface Comment {
  id: string;
  author: string | null;
  body: string;
  created_at: string;
}

interface DeckDetail {
  id: string;
  name: string;
  moderators: { id: string; email: string }[];
}

// FR-021: três abas — mudanças, notas novas e exclusões
const TABS = [
  { value: "change", label: "Mudanças" },
  { value: "new_note", label: "Notas novas" },
  { value: "deletion", label: "Exclusões" },
];

const STATUSES = [
  { value: "all", label: "Todos os status" },
  { value: "pending", label: "Pendentes" },
  { value: "accepted", label: "Aceitas" },
  { value: "rejected", label: "Rejeitadas" },
];

const SUBMISSIONS = [
  { value: "all", label: "Individual e lote" },
  { value: "individual", label: "Individual" },
  { value: "bulk", label: "Em lote" },
];

const STATUS_BADGE: Record<
  Suggestion["status"],
  { className: string; label: string }
> = {
  pending: { className: "bg-warning/15 text-warning", label: "Pendente" },
  accepted: { className: "bg-success/15 text-success", label: "Aceita" },
  rejected: {
    className: "bg-destructive/15 text-destructive",
    label: "Rejeitada",
  },
};

const CATEGORY_LABELS: Record<string, string> = {
  conteudo_atualizado: "Conteúdo atualizado",
  ortografia_gramatica: "Ortografia/Gramática",
  erro_conteudo: "Erro de conteúdo",
  nova_tag: "Nova tag",
  tag_atualizada: "Tag atualizada",
  outro: "Outro",
};

/** `next` da API é URL absoluta; o api-client espera caminho relativo a /api/v1. */
function nextPath(next: string | null): string | null {
  if (!next) return null;
  const marker = "/api/v1";
  return next.slice(next.indexOf(marker) + marker.length);
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("pt-BR");
}

function CommentsThread({ suggestionId }: { suggestionId: string }) {
  const queryClient = useQueryClient();
  const queryKey = ["suggestion-comments", suggestionId];
  // ponytail: só a primeira página da thread; paginar quando threads longas existirem
  const { data, isPending } = useQuery({
    queryKey,
    queryFn: () =>
      api.get<Paginated<Comment>>(`/suggestions/${suggestionId}/comments/`),
  });

  const [body, setBody] = useState("");
  const post = useMutation({
    mutationFn: () =>
      api.post(`/suggestions/${suggestionId}/comments/`, { body }),
    onSuccess: () => {
      setBody("");
      queryClient.invalidateQueries({ queryKey });
    },
  });

  return (
    <div className="flex flex-col gap-3 border-t pt-3">
      {isPending && <Skeleton className="h-12 w-full" />}
      {data?.results.length === 0 && (
        <p className="text-sm text-muted-foreground">
          Nenhum comentário ainda.
        </p>
      )}
      {data?.results.map((comment) => (
        <div key={comment.id} className="text-sm">
          <p className="text-muted-foreground">
            <span className="font-mono">
              {comment.author?.slice(0, 8) ?? "removido"}
            </span>{" "}
            · {formatDate(comment.created_at)}
          </p>
          <p>{comment.body}</p>
          <ReportButton commentId={comment.id} suggestionThread />
        </div>
      ))}
      <form
        className="flex flex-col gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (body.trim()) post.mutate();
        }}
      >
        <Label htmlFor={`comment-${suggestionId}`} className="sr-only">
          Novo comentário
        </Label>
        <Textarea
          id={`comment-${suggestionId}`}
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Participe da discussão desta sugestão"
        />
        {post.isError && (
          <p role="alert" className="text-sm text-destructive">
            Não foi possível enviar o comentário.
          </p>
        )}
        <Button
          type="submit"
          size="sm"
          className="self-start"
          disabled={post.isPending}
        >
          {post.isPending ? "Enviando…" : "Comentar"}
        </Button>
      </form>
    </div>
  );
}

function SuggestionCard({
  suggestion,
  isModerator,
  onChanged,
}: {
  suggestion: Suggestion;
  isModerator: boolean;
  onChanged: () => void;
}) {
  const [threadOpen, setThreadOpen] = useState(false);
  const status = STATUS_BADGE[suggestion.status];

  const vote = useMutation({
    mutationFn: (value: "like" | "dislike") =>
      api.post(`/suggestions/${suggestion.id}/votes/`, { value }),
    onSuccess: onChanged,
  });

  const proposedFields = Object.entries(suggestion.proposed_field_values ?? {});

  return (
    <Card>
      <CardContent className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <Badge className={`rounded-full ${status.className}`}>
            {status.label}
          </Badge>
          {suggestion.change_category && (
            <Badge variant="secondary" className="rounded-full">
              {CATEGORY_LABELS[suggestion.change_category] ??
                suggestion.change_category}
            </Badge>
          )}
          {suggestion.note_ids.length > 1 && (
            <Badge variant="secondary" className="rounded-full">
              Lote · {suggestion.note_ids.length} notas
            </Badge>
          )}
          <span className="text-sm text-muted-foreground">
            <span className="font-mono">
              {suggestion.author?.slice(0, 8) ?? "removido"}
            </span>{" "}
            · {formatDate(suggestion.created_at)}
          </span>
        </div>

        <p>{suggestion.justification}</p>

        {proposedFields.length > 0 && (
          <details className="rounded-lg border bg-muted/30 p-3">
            <summary className="cursor-pointer text-sm font-medium">
              Campos propostos (
              {proposedFields.map(([field]) => field).join(", ")})
            </summary>
            <div className="mt-2 flex flex-col gap-2">
              {proposedFields.map(([field, html]) => (
                <div key={field}>
                  <p className="flex items-center gap-2 text-sm font-medium text-muted-foreground">
                    {field}
                    {suggestion.empty_fields.includes(field) && (
                      <Badge variant="outline" className="rounded-full">
                        Vazio
                      </Badge>
                    )}
                  </p>
                  <div
                    className="rounded-lg bg-success/10 p-2"
                    // HTML já sanitizado pelo backend (nh3)
                    dangerouslySetInnerHTML={{ __html: html }}
                  />
                </div>
              ))}
            </div>
          </details>
        )}

        {suggestion.tags.length > 0 && (
          <p className="text-sm text-muted-foreground">
            Tags propostas: {suggestion.tags.join(", ")}
          </p>
        )}

        {suggestion.status === "rejected" && suggestion.rejection_reason && (
          <p className="text-sm text-muted-foreground">
            Motivo da rejeição: {suggestion.rejection_reason}
          </p>
        )}

        <div className="flex flex-wrap items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            aria-label="Curtir sugestão"
            disabled={vote.isPending}
            onClick={() => vote.mutate("like")}
          >
            <ThumbsUp aria-hidden /> {suggestion.likes_count}
          </Button>
          <Button
            size="sm"
            variant="outline"
            aria-label="Descurtir sugestão"
            disabled={vote.isPending}
            onClick={() => vote.mutate("dislike")}
          >
            <ThumbsDown aria-hidden /> {suggestion.dislikes_count}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setThreadOpen((open) => !open)}
            aria-expanded={threadOpen}
          >
            <MessageSquare aria-hidden /> Discussão
          </Button>
          {isModerator && suggestion.status === "pending" && (
            <div className="ml-auto">
              <SuggestionModerationControls
                suggestionId={suggestion.id}
                onDecided={onChanged}
              />
            </div>
          )}
        </div>

        {threadOpen && <CommentsThread suggestionId={suggestion.id} />}
      </CardContent>
    </Card>
  );
}

export default function CommunitySuggestionsPage() {
  const { id } = useParams<{ id: string }>();
  const queryClient = useQueryClient();

  const [tab, setTab] = useState("change");
  const [status, setStatus] = useState("all");
  const [submission, setSubmission] = useState("all");
  const [createdAfter, setCreatedAfter] = useState("");
  const [createdBefore, setCreatedBefore] = useState("");
  // busca por autor/nota aplicada no submit do form (FR-022)
  const [authorInput, setAuthorInput] = useState("");
  const [noteIdInput, setNoteIdInput] = useState("");
  const [search, setSearch] = useState({ author: "", note_id: "" });

  const { data: me } = useQuery<{ id: string }>({
    queryKey: ["me"],
    queryFn: () => api.get<{ id: string }>("/accounts/me/"),
    retry: false,
  });
  const { data: deck } = useQuery<DeckDetail>({
    queryKey: ["deck", id],
    queryFn: () => api.get<DeckDetail>(`/decks/${id}/`),
    retry: false,
  });
  const isModerator = !!me && !!deck?.moderators.some((m) => m.id === me.id);

  const params = new URLSearchParams({ type: tab });
  if (status !== "all") params.set("status", status);
  if (submission !== "all") params.set("submission", submission);
  if (createdAfter) params.set("created_after", createdAfter);
  if (createdBefore) params.set("created_before", createdBefore);
  if (search.author) params.set("author", search.author);
  if (search.note_id) params.set("note_id", search.note_id);
  const firstPage = `/decks/${id}/suggestions/?${params}`;

  const suggestions = useInfiniteQuery({
    queryKey: ["suggestions", id, firstPage],
    queryFn: ({ pageParam }) => api.get<Paginated<Suggestion>>(pageParam),
    initialPageParam: firstPage,
    getNextPageParam: (lastPage) => nextPath(lastPage.next),
    retry: false,
  });
  const refetchSuggestions = () =>
    queryClient.invalidateQueries({ queryKey: ["suggestions", id] });

  if (
    suggestions.error instanceof ApiError &&
    suggestions.error.status === 401
  ) {
    return (
      <main className="mx-auto max-w-3xl p-4 md:p-6">
        <p>
          <Link href="/login" className="text-primary underline">
            Entre
          </Link>{" "}
          para ver as sugestões da comunidade.
        </p>
      </main>
    );
  }

  const results = suggestions.data?.pages.flatMap((page) => page.results) ?? [];

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
        / <span className="text-foreground">Sugestões</span>
      </nav>

      <h1 className="mb-6 text-2xl font-semibold tracking-tight">
        Sugestões da comunidade
      </h1>

      <Tabs value={tab} onValueChange={(value) => setTab(String(value))}>
        <TabsList className="w-full sm:w-fit">
          {TABS.map((t) => (
            <TabsTrigger key={t.value} value={t.value}>
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>
      </Tabs>

      <form
        className="my-4 grid grid-cols-1 gap-3 sm:grid-cols-2"
        onSubmit={(e) => {
          e.preventDefault();
          setSearch({
            author: authorInput.trim(),
            note_id: noteIdInput.trim(),
          });
        }}
      >
        <div className="flex flex-col gap-1">
          <Label htmlFor="filter-status">Status</Label>
          <Select
            value={status}
            onValueChange={(value) => setStatus(value ?? "all")}
            items={STATUSES}
          >
            <SelectTrigger id="filter-status" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {STATUSES.map((s) => (
                <SelectItem key={s.value} value={s.value}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="filter-submission">Tipo de envio</Label>
          <Select
            value={submission}
            onValueChange={(value) => setSubmission(value ?? "all")}
            items={SUBMISSIONS}
          >
            <SelectTrigger id="filter-submission" className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {SUBMISSIONS.map((s) => (
                <SelectItem key={s.value} value={s.value}>
                  {s.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="filter-after">Criadas a partir de</Label>
          <Input
            id="filter-after"
            type="date"
            value={createdAfter}
            onChange={(e) => setCreatedAfter(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="filter-before">Criadas até</Label>
          <Input
            id="filter-before"
            type="date"
            value={createdBefore}
            onChange={(e) => setCreatedBefore(e.target.value)}
          />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="filter-author">ID do autor</Label>
          <Input
            id="filter-author"
            value={authorInput}
            onChange={(e) => setAuthorInput(e.target.value)}
            placeholder="UUID do autor"
            className="font-mono"
          />
        </div>
        <div className="flex flex-col gap-1">
          <Label htmlFor="filter-note">ID da nota</Label>
          <Input
            id="filter-note"
            value={noteIdInput}
            onChange={(e) => setNoteIdInput(e.target.value)}
            placeholder="UUID da nota"
            className="font-mono"
          />
        </div>
        <div className="sm:col-span-2">
          <Button type="submit" variant="outline" size="sm">
            Buscar
          </Button>
        </div>
      </form>

      {suggestions.isPending && (
        <div className="flex flex-col gap-4">
          <Skeleton className="h-32 w-full" />
          <Skeleton className="h-32 w-full" />
        </div>
      )}

      {suggestions.isError && (
        <Alert variant="destructive">
          <AlertTitle>Erro ao carregar sugestões</AlertTitle>
          <AlertDescription>
            {(suggestions.error instanceof ApiError &&
              (suggestions.error.body as { detail?: string } | null)?.detail) ||
              "Não foi possível carregar as sugestões."}{" "}
            <button className="underline" onClick={() => suggestions.refetch()}>
              Tentar novamente
            </button>
          </AlertDescription>
        </Alert>
      )}

      {suggestions.isSuccess && results.length === 0 && (
        <div className="flex flex-col items-center gap-2 py-12 text-center">
          <Inbox aria-hidden className="size-8 text-muted-foreground" />
          <p className="text-lg font-medium">Nenhuma sugestão aqui</p>
          <p className="text-sm text-muted-foreground">
            Ajuste os filtros ou seja o primeiro a sugerir uma melhoria.
          </p>
        </div>
      )}

      <div className="flex flex-col gap-4">
        {results.map((suggestion) => (
          <SuggestionCard
            key={suggestion.id}
            suggestion={suggestion}
            isModerator={isModerator}
            onChanged={refetchSuggestions}
          />
        ))}
      </div>

      {suggestions.hasNextPage && (
        <div className="mt-4 flex justify-center">
          <Button
            variant="outline"
            onClick={() => suggestions.fetchNextPage()}
            disabled={suggestions.isFetchingNextPage}
          >
            {suggestions.isFetchingNextPage ? "Carregando…" : "Carregar mais"}
          </Button>
        </div>
      )}
    </main>
  );
}

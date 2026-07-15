"use client";

import { useState } from "react";
import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";
import { MessageSquare, Pencil, Send, Trash2 } from "lucide-react";
import { api, type Paginated } from "@/lib/api-client";
import ReportButton from "@/components/ReportButton";
import { UserAvatar } from "@/components/user-avatar";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { Textarea } from "@/components/ui/textarea";

interface Comment {
  id: string;
  author: string | null;
  author_name: string | null;
  avatar_url: string | null;
  body: string;
  created_at: string;
  edited_at: string | null;
}

function nextPath(next: string | null): string | null {
  if (!next) return null;
  const marker = "/api/v1";
  return next.slice(next.indexOf(marker) + marker.length);
}

function formatDate(iso: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(new Date(iso));
}

export default function CommentThread({ noteId }: { noteId: string }) {
  const queryClient = useQueryClient();
  const queryKey = ["note-comments", noteId];
  const [body, setBody] = useState("");
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editBody, setEditBody] = useState("");
  const [notice, setNotice] = useState("");

  const me = useQuery<{ id: string }>({
    queryKey: ["me"],
    queryFn: () => api.get("/accounts/me/"),
    retry: false,
  });
  const comments = useInfiniteQuery({
    queryKey,
    queryFn: ({ pageParam }) => api.get<Paginated<Comment>>(pageParam),
    initialPageParam: `/notes/${noteId}/comments/`,
    getNextPageParam: (lastPage) => nextPath(lastPage.next),
    retry: false,
  });
  const refresh = () => queryClient.invalidateQueries({ queryKey });

  const createComment = useMutation({
    mutationFn: () =>
      api.post<Comment>(`/notes/${noteId}/comments/`, { body: body.trim() }),
    onSuccess: () => {
      setBody("");
      setNotice("Comentário publicado.");
      refresh();
    },
  });
  const editComment = useMutation({
    mutationFn: ({ id, body }: { id: string; body: string }) =>
      api.patch<Comment>(`/comments/${id}/`, { body: body.trim() }),
    onSuccess: () => {
      setEditingId(null);
      setNotice("Comentário atualizado.");
      refresh();
    },
  });
  const deleteComment = useMutation({
    mutationFn: (id: string) => api.delete(`/comments/${id}/`),
    onSuccess: () => {
      setNotice("Comentário excluído.");
      refresh();
    },
  });

  const results = comments.data?.pages.flatMap((page) => page.results) ?? [];
  const mutationFailed =
    createComment.isError || editComment.isError || deleteComment.isError;

  return (
    <section
      aria-labelledby={`comments-title-${noteId}`}
      className="border-t pt-4"
    >
      <div className="mb-4 flex items-center gap-2">
        <MessageSquare aria-hidden className="size-5 text-primary" />
        <h3 id={`comments-title-${noteId}`} className="font-semibold">
          Discussão geral
        </h3>
      </div>

      <div aria-live="polite" className="sr-only">
        {notice}
      </div>

      {comments.isPending && (
        <div
          className="flex flex-col gap-3"
          aria-label="Carregando comentários"
        >
          <Skeleton className="h-16 w-full" />
          <Skeleton className="h-16 w-full" />
        </div>
      )}

      {comments.isError && (
        <Alert variant="destructive">
          <AlertTitle>Não foi possível carregar a discussão</AlertTitle>
          <AlertDescription className="flex flex-wrap items-center gap-2">
            <span>Confira sua conexão e tente novamente.</span>
            <Button
              type="button"
              size="sm"
              variant="outline"
              disabled={comments.isFetching}
              onClick={() => comments.refetch()}
            >
              {comments.isFetching ? "Tentando novamente…" : "Tentar novamente"}
            </Button>
          </AlertDescription>
        </Alert>
      )}

      {comments.isSuccess && results.length === 0 && (
        <div className="py-6 text-center">
          <p className="font-medium">Comece a conversa</p>
          <p className="text-sm text-muted-foreground">
            Compartilhe uma dúvida ou contexto útil sobre esta nota.
          </p>
        </div>
      )}

      {results.length > 0 && (
        <ol className="mb-4 divide-y" aria-label="Comentários da nota">
          {results.map((comment) => {
            const own = comment.author === me.data?.id;
            const editing = editingId === comment.id;

            return (
              <li key={comment.id} className="py-4 first:pt-0">
                <div className="mb-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm">
                  <UserAvatar
                    avatarUrl={comment.avatar_url}
                    name={comment.author_name}
                    className="size-6"
                  />
                  <span className="font-medium">
                    {own
                      ? "Você"
                      : comment.author_name ||
                        (comment.author ? "Usuário" : "Usuário removido")}
                  </span>
                  <span className="text-muted-foreground">
                    {formatDate(comment.created_at)}
                    {comment.edited_at ? " · editado" : ""}
                  </span>
                </div>

                {editing ? (
                  <form
                    className="flex flex-col gap-2"
                    onSubmit={(event) => {
                      event.preventDefault();
                      if (editBody.trim()) {
                        editComment.mutate({ id: comment.id, body: editBody });
                      }
                    }}
                  >
                    <Label htmlFor={`edit-comment-${comment.id}`}>
                      Editar comentário
                    </Label>
                    <Textarea
                      id={`edit-comment-${comment.id}`}
                      value={editBody}
                      onChange={(event) => setEditBody(event.target.value)}
                      disabled={editComment.isPending}
                    />
                    <div className="flex flex-wrap gap-2">
                      <Button
                        type="submit"
                        size="sm"
                        className="min-h-11"
                        disabled={!editBody.trim() || editComment.isPending}
                      >
                        {editComment.isPending ? "Salvando…" : "Salvar"}
                      </Button>
                      <Button
                        type="button"
                        size="sm"
                        variant="ghost"
                        className="min-h-11"
                        onClick={() => setEditingId(null)}
                      >
                        Cancelar
                      </Button>
                    </div>
                  </form>
                ) : (
                  <>
                    <p className="max-w-[70ch] whitespace-pre-wrap text-pretty">
                      {comment.body}
                    </p>
                    {own && (
                      <div className="mt-2 flex flex-wrap gap-2">
                        <Button
                          type="button"
                          size="sm"
                          variant="ghost"
                          className="min-h-11"
                          onClick={() => {
                            setEditingId(comment.id);
                            setEditBody(comment.body);
                          }}
                        >
                          <Pencil aria-hidden /> Editar
                        </Button>
                        <Button
                          type="button"
                          size="sm"
                          variant="destructive"
                          className="min-h-11"
                          disabled={deleteComment.isPending}
                          onClick={() => {
                            if (window.confirm("Excluir este comentário?")) {
                              deleteComment.mutate(comment.id);
                            }
                          }}
                        >
                          <Trash2 aria-hidden /> Excluir
                        </Button>
                      </div>
                    )}
                    <ReportButton commentId={comment.id} />
                  </>
                )}
              </li>
            );
          })}
        </ol>
      )}

      {comments.hasNextPage && (
        <Button
          type="button"
          variant="outline"
          className="mb-4 min-h-11"
          disabled={comments.isFetchingNextPage}
          onClick={() => comments.fetchNextPage()}
        >
          {comments.isFetchingNextPage
            ? "Carregando…"
            : "Carregar mais comentários"}
        </Button>
      )}

      <form
        className="flex flex-col gap-2"
        onSubmit={(event) => {
          event.preventDefault();
          if (body.trim()) createComment.mutate();
        }}
      >
        <Label htmlFor={`new-comment-${noteId}`}>Novo comentário</Label>
        <Textarea
          id={`new-comment-${noteId}`}
          value={body}
          onChange={(event) => setBody(event.target.value)}
          placeholder="Escreva uma dúvida ou observação"
          disabled={createComment.isPending}
        />
        <p className="text-sm text-muted-foreground">
          Esta é a conversa geral da nota, separada das sugestões de mudança.
        </p>
        {mutationFailed && (
          <p role="alert" className="text-sm text-destructive">
            Não foi possível concluir a ação. Tente novamente.
          </p>
        )}
        <Button
          type="submit"
          className="min-h-11 self-start"
          disabled={!body.trim() || createComment.isPending}
        >
          <Send aria-hidden />
          {createComment.isPending ? "Enviando…" : "Comentar"}
        </Button>
      </form>
    </section>
  );
}

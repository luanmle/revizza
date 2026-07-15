"use client";

import { Bell } from "lucide-react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { notificationsApi } from "@/lib/notifications";

const LABELS: Record<string, string> = {
  suggestion_accepted: "Sua sugestão foi aceita",
  suggestion_rejected: "Sua sugestão foi rejeitada",
  new_suggestion: "Nova sugestão para revisar",
  sync_pending: "Mudanças aguardando sincronização",
};

export default function NotificationBell() {
  const queryClient = useQueryClient();

  const { data: unreadCount } = useQuery({
    queryKey: ["notifications", "unread-count"],
    queryFn: () => notificationsApi.unreadCount(),
    refetchInterval: 45_000,
    select: (data) => data.count,
  });

  const { data: page, refetch } = useQuery({
    queryKey: ["notifications", "list"],
    queryFn: () => notificationsApi.list(),
    enabled: false,
  });

  const readAll = useMutation({
    mutationFn: notificationsApi.readAll,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });

  return (
    <DropdownMenu onOpenChange={(open) => open && refetch()}>
      <DropdownMenuTrigger
        render={
          <Button variant="ghost" size="icon" aria-label="Notificações" />
        }
      >
        <span className="relative">
          <Bell className="size-5" aria-hidden />
          {!!unreadCount && (
            <Badge
              variant="destructive"
              className="absolute -top-2 -right-2 h-4 min-w-4 px-1 text-[10px]"
            >
              {unreadCount}
            </Badge>
          )}
        </span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-80">
        {!page?.results.length && (
          <p className="px-2 py-4 text-center text-sm text-muted-foreground">
            Nenhuma notificação ainda.
          </p>
        )}
        {page?.results.map((notification) => (
          <DropdownMenuItem
            key={notification.id}
            className="flex flex-col items-start gap-0.5 whitespace-normal"
            onClick={() =>
              notificationsApi
                .markRead(notification.id)
                .then(() =>
                  queryClient.invalidateQueries({ queryKey: ["notifications"] }),
                )
            }
          >
            <span className="text-sm font-medium">
              {LABELS[notification.type]}
            </span>
            <span className="text-xs text-muted-foreground">
              {notification.deck_name}
              {notification.rejection_reason &&
                ` — ${notification.rejection_reason}`}
            </span>
          </DropdownMenuItem>
        ))}
        {!!page?.results.length && (
          <DropdownMenuItem onClick={() => readAll.mutate()}>
            Marcar todas como lidas
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

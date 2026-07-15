import { api, Paginated } from "./api-client";

export type NotificationType =
  | "suggestion_accepted"
  | "suggestion_rejected"
  | "new_suggestion"
  | "sync_pending";

export interface Notification {
  id: string;
  type: NotificationType;
  deck_id: string;
  deck_name: string;
  suggestion_id: string | null;
  note_id: string | null;
  rejection_reason: string | null;
  read_at: string | null;
  created_at: string;
}

export const notificationsApi = {
  list: () => api.get<Paginated<Notification>>("/notifications/"),
  unreadCount: () => api.get<{ count: number }>("/notifications/unread-count/"),
  markRead: (id: string) => api.post(`/notifications/${id}/read/`),
  readAll: () => api.post("/notifications/read-all/"),
};

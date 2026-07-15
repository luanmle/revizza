import { cn } from "@/lib/utils";

/** Avatar de usuário nos pontos de autoria (sugestões, comentários, moderadores).
 * Sem avatar: initials do nome, ou "?" para nome vazio/ausente. */
export function UserAvatar({
  avatarUrl,
  name,
  className,
}: {
  avatarUrl?: string | null;
  name?: string | null;
  className?: string;
}) {
  if (avatarUrl) {
    return (
      <img
        src={avatarUrl}
        alt=""
        className={cn("size-8 shrink-0 rounded-full object-cover", className)}
      />
    );
  }
  return (
    <span
      aria-hidden
      className={cn(
        "flex size-8 shrink-0 items-center justify-center rounded-full bg-muted text-sm font-medium text-muted-foreground",
        className,
      )}
    >
      {name?.trim()?.[0]?.toUpperCase() ?? "?"}
    </span>
  );
}

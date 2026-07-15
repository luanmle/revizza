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
  return (
    <span
      aria-hidden
      className={cn(
        "relative flex size-8 shrink-0 items-center justify-center overflow-hidden rounded-full bg-muted text-sm font-medium text-muted-foreground",
        className,
      )}
    >
      {name?.trim()?.[0]?.toUpperCase() ?? "?"}
      {avatarUrl && (
        // Dynamic avatar hosts are not allowlisted for next/image.
        // eslint-disable-next-line @next/next/no-img-element
        <img
          src={avatarUrl}
          alt=""
          width={32}
          height={32}
          loading="lazy"
          decoding="async"
          className="absolute inset-0 size-full object-cover"
          onLoad={(event) => {
            event.currentTarget.hidden = false;
          }}
          onError={(event) => {
            event.currentTarget.hidden = true;
          }}
        />
      )}
    </span>
  );
}

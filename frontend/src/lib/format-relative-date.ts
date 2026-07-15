const formatter = new Intl.RelativeTimeFormat("pt-BR", { numeric: "auto" });

export function formatRelativeDate(value: string) {
  const seconds = (new Date(value).getTime() - Date.now()) / 1000;
  if (Math.abs(seconds) < 60) return formatter.format(0, "second");
  const minutes = seconds / 60;
  if (Math.abs(minutes) < 60)
    return formatter.format(Math.round(minutes), "minute");
  const hours = minutes / 60;
  if (Math.abs(hours) < 24) return formatter.format(Math.round(hours), "hour");
  return formatter.format(Math.round(hours / 24), "day");
}

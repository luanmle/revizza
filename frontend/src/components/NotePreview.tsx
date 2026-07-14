/**
 * Preview fiel de nota (FR-011): template + CSS originais do Anki renderizados em
 * iframe `sandbox` com `srcDoc` — isolamento total de CSS nos dois sentidos e sem
 * execução de script, segunda camada de defesa além do nh3 (research.md #13).
 */

export interface NoteTypeInfo {
  templates: { name: string; qfmt: string; afmt: string }[];
  css: string;
}

interface RenderOptions {
  side?: "question" | "answer";
  clozeOrdinal?: number;
}

function stripHtml(html: string): string {
  return html
    .replace(/<[^>]*>/g, "")
    .replace(/&(nbsp|#160);/gi, " ")
    .replace(/&lt;/gi, "<")
    .replace(/&gt;/gi, ">")
    .replace(/&amp;/gi, "&")
    .replace(/&quot;/gi, '"')
    .replace(/&#39;|&apos;/gi, "'");
}

function clozeOrdinals(fields: Record<string, string>): number[] {
  const ordinals = Object.values(fields).flatMap((value) =>
    [...value.matchAll(/\{\{c(\d+)::/gi)].map((match) => Number(match[1])),
  );
  return ordinals.length ? [...new Set(ordinals)].sort((a, b) => a - b) : [1];
}

function renderCloze(
  value: string,
  side: "question" | "answer",
  ordinal: number,
) {
  return value.replace(
    /\{\{c(\d+)::([\s\S]*?)(?:::(.*?))?\}\}/gi,
    (_, rawOrdinal, content, hint) => {
      if (Number(rawOrdinal) !== ordinal) return content;
      return side === "question"
        ? `<span class="cloze">[${hint || "..."}]</span>`
        : `<span class="cloze">${content}</span>`;
    },
  );
}

function renderConditionals(
  template: string,
  fields: Record<string, string>,
  clozeOrdinal: number,
): string {
  function present(name: string) {
    const cloze = /^c(\d+)$/i.exec(name);
    return cloze
      ? Number(cloze[1]) === clozeOrdinal
      : stripHtml(fields[name] ?? "").trim().length > 0;
  }

  function walk(start: number, closing?: string): [string, number, boolean] {
    const tag = /\{\{([#^/])([^{}]+)\}\}/g;
    let cursor = start;
    let output = "";

    while (cursor < template.length) {
      tag.lastIndex = cursor;
      const match = tag.exec(template);
      if (!match)
        return [output + template.slice(cursor), template.length, false];
      output += template.slice(cursor, match.index);
      const [, marker, rawName] = match;
      const name = rawName.trim();

      if (marker === "/") {
        if (name === closing) return [output, tag.lastIndex, true];
        output += match[0];
        cursor = tag.lastIndex;
        continue;
      }

      const [content, next, closed] = walk(tag.lastIndex, name);
      if (!closed) return [output + match[0] + content, next, false];
      if ((marker === "#") === present(name)) output += content;
      cursor = next;
    }
    return [output, cursor, false];
  }

  return walk(0)[0];
}

export function renderAnkiTemplate(
  template: string,
  fields: Record<string, string>,
  options: RenderOptions = {},
): string {
  const side = options.side ?? "question";
  const clozeOrdinal = options.clozeOrdinal ?? clozeOrdinals(fields)[0];
  return renderConditionals(template, fields, clozeOrdinal).replace(
    /\{\{([^#^/][^{}]*)\}\}/g,
    (match, expression) => {
      const parts = String(expression)
        .split(":")
        .map((part) => part.trim());
      const field = parts.pop() ?? "";
      if (!(field in fields)) return match;
      let value = fields[field];

      for (const filter of parts.reverse()) {
        if (filter === "cloze") value = renderCloze(value, side, clozeOrdinal);
        else if (filter === "text") value = stripHtml(value);
        else if (filter === "hint") {
          value = value
            ? `<details class="hint"><summary>Mostrar dica</summary>${value}</details>`
            : "";
        } else if (filter === "type") {
          value =
            side === "question"
              ? '<input class="typeans" aria-label="Digite a resposta" autocomplete="off">'
              : value;
        } else return match;
      }
      return value;
    },
  );
}

export function buildCardDoc(
  template: { qfmt: string; afmt: string },
  fields: Record<string, string>,
  css: string,
  clozeOrdinal = clozeOrdinals(fields)[0],
): string {
  const front = renderAnkiTemplate(template.qfmt, fields, {
    side: "question",
    clozeOrdinal,
  });
  const back = renderAnkiTemplate(
    template.afmt,
    { ...fields, FrontSide: front },
    { side: "answer", clozeOrdinal },
  );
  return `<!doctype html><html><head><meta charset="utf-8"><style>${css}</style></head><body class="card">${back}</body></html>`;
}

export default function NotePreview({
  noteType,
  fieldValues,
}: {
  noteType: NoteTypeInfo;
  fieldValues: Record<string, string>;
}) {
  return (
    <div className="flex flex-col gap-3">
      {noteType.templates.flatMap((template) => {
        const ordinals = template.qfmt.includes("{{cloze:")
          ? clozeOrdinals(fieldValues)
          : [undefined];
        return ordinals.map((ordinal) => {
          const label = ordinal
            ? `${template.name} · C${ordinal}`
            : template.name;
          return (
            <div key={label} className="flex flex-col gap-1">
              {(noteType.templates.length > 1 || ordinal) && (
                <p className="text-sm font-medium text-muted-foreground">
                  {label}
                </p>
              )}
              <iframe
                sandbox=""
                referrerPolicy="no-referrer"
                loading="lazy"
                srcDoc={buildCardDoc(
                  template,
                  fieldValues,
                  noteType.css,
                  ordinal,
                )}
                title={`Preview do card ${label}`}
                className="h-64 w-full rounded-lg border bg-white"
              />
            </div>
          );
        });
      })}
    </div>
  );
}

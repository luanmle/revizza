/**
 * Preview fiel de nota (FR-011): template + CSS originais do Anki renderizados em
 * iframe `sandbox` com `srcDoc` — isolamento total de CSS nos dois sentidos e sem
 * execução de script, segunda camada de defesa além do nh3 (research.md #13).
 */

export interface NoteTypeInfo {
  templates: { name: string; qfmt: string; afmt: string }[];
  css: string;
}

// ponytail: subconjunto do template Anki — {{Campo}}, {{FrontSide}} e seções
// {{#C}}/{{^C}} não aninhadas; cloze/hint/filtros ficam para quando um deck real precisar
export function renderAnkiTemplate(
  template: string,
  fields: Record<string, string>,
): string {
  const value = (name: string) => fields[name.trim()] ?? "";
  return template
    .replace(/\{\{#([^}]+)\}\}([\s\S]*?)\{\{\/\1\}\}/g, (_, name, content) =>
      value(name).trim() ? content : "",
    )
    .replace(/\{\{\^([^}]+)\}\}([\s\S]*?)\{\{\/\1\}\}/g, (_, name, content) =>
      value(name).trim() ? "" : content,
    )
    .replace(/\{\{([^#^/][^}]*)\}\}/g, (match, name) =>
      fields[name.trim()] !== undefined ? fields[name.trim()] : match,
    );
}

export function buildCardDoc(
  template: { qfmt: string; afmt: string },
  fields: Record<string, string>,
  css: string,
): string {
  const front = renderAnkiTemplate(template.qfmt, fields);
  const back = renderAnkiTemplate(template.afmt, { ...fields, FrontSide: front });
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
      {noteType.templates.map((template) => (
        <div key={template.name} className="flex flex-col gap-1">
          {noteType.templates.length > 1 && (
            <p className="text-sm font-medium text-muted-foreground">{template.name}</p>
          )}
          <iframe
            sandbox=""
            srcDoc={buildCardDoc(template, fieldValues, noteType.css)}
            title={`Preview do card ${template.name}`}
            className="h-64 w-full rounded-lg border bg-white"
          />
        </div>
      ))}
    </div>
  );
}

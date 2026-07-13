import { describe, expect, it } from "vitest";
import { buildCardDoc, renderAnkiTemplate } from "@/components/NotePreview";

const fields = { Frente: "Qual o prazo?", Verso: "<b>15 dias</b>", Extra: "" };

describe("renderAnkiTemplate", () => {
  it("substitui {{Campo}} pelo valor", () => {
    expect(renderAnkiTemplate("{{Frente}} — {{Verso}}", fields)).toBe(
      "Qual o prazo? — <b>15 dias</b>",
    );
  });

  it("mantém diretivas desconhecidas intactas", () => {
    expect(renderAnkiTemplate("{{cloze:Texto}}", fields)).toBe("{{cloze:Texto}}");
  });

  it("seção {{#C}} aparece só com campo preenchido", () => {
    const template = "{{#Extra}}tem extra{{/Extra}}{{^Extra}}sem extra{{/Extra}}";
    expect(renderAnkiTemplate(template, fields)).toBe("sem extra");
    expect(renderAnkiTemplate(template, { ...fields, Extra: "x" })).toBe("tem extra");
  });
});

describe("buildCardDoc", () => {
  it("injeta CSS e resolve {{FrontSide}} no verso", () => {
    const doc = buildCardDoc(
      { qfmt: "{{Frente}}", afmt: "{{FrontSide}}<hr>{{Verso}}" },
      fields,
      ".card { color: red }",
    );
    expect(doc).toContain("<style>.card { color: red }</style>");
    expect(doc).toContain("Qual o prazo?<hr><b>15 dias</b>");
    expect(doc).toContain('<body class="card">');
  });
});

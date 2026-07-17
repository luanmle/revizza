import { describe, expect, it } from "vitest";
import { buildCardDoc, renderAnkiTemplate } from "@/components/NotePreview";

const fields = { Frente: "Qual o prazo?", Verso: "<b>15 dias</b>", Extra: "" };

describe("renderAnkiTemplate", () => {
  it("substitui {{Campo}} pelo valor", () => {
    expect(renderAnkiTemplate("{{Frente}} — {{Verso}}", fields)).toBe(
      "Qual o prazo? — <b>15 dias</b>",
    );
  });

  it("renderiza cloze na frente e no verso", () => {
    const clozeFields = { Texto: "A capital é {{c1::Brasília::cidade}}." };
    expect(renderAnkiTemplate("{{cloze:Texto}}", clozeFields)).toBe(
      'A capital é <span class="cloze">[cidade]</span>.',
    );
    expect(
      renderAnkiTemplate("{{cloze:Texto}}", clozeFields, { side: "answer" }),
    ).toBe('A capital é <span class="cloze">Brasília</span>.');
  });

  it("seção {{#C}} aparece só com campo preenchido", () => {
    const template =
      "{{#Extra}}tem extra{{/Extra}}{{^Extra}}sem extra{{/Extra}}";
    expect(renderAnkiTemplate(template, fields)).toBe("sem extra");
    expect(renderAnkiTemplate(template, { ...fields, Extra: "x" })).toBe(
      "tem extra",
    );
  });

  it("campo só com <img> conta como preenchido no condicional", () => {
    const template = "{{#Extra}}{{Extra}}{{/Extra}}{{^Extra}}vazio{{/Extra}}";
    const img = '<img src="https://x/f.png">';
    expect(renderAnkiTemplate(template, { ...fields, Extra: img })).toBe(img);
  });

  it("resolve condicionais aninhadas e a condição do cloze ativo", () => {
    const template =
      "{{#Frente}}fora {{#Verso}}dentro{{/Verso}}{{/Frente}} {{#c1}}dica{{/c1}}";
    expect(renderAnkiTemplate(template, fields)).toBe("fora dentro dica");
    expect(renderAnkiTemplate(template, { ...fields, Frente: "" })).toBe(
      " dica",
    );
  });

  it("aplica filtros de dica, texto e resposta digitada", () => {
    expect(renderAnkiTemplate("{{hint:Verso}}", fields)).toContain(
      "<summary>Mostrar dica</summary><b>15 dias</b>",
    );
    expect(renderAnkiTemplate("{{text:Verso}}", fields)).toBe("15 dias");
    expect(renderAnkiTemplate("{{type:Frente}}", fields)).toContain(
      'class="typeans"',
    );
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

  it("renderiza o ordinal de cloze solicitado", () => {
    const doc = buildCardDoc(
      { qfmt: "{{cloze:Texto}}", afmt: "{{cloze:Texto}}" },
      { Texto: "{{c1::um}} e {{c2::dois}}" },
      "",
      2,
    );
    expect(doc).toContain('um e <span class="cloze">dois</span>');
  });
});

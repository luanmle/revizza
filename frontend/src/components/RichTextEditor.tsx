"use client";

import { useEffect, useState } from "react";
import { EditorContent, useEditor, useEditorState } from "@tiptap/react";
import StarterKit from "@tiptap/starter-kit";
import {
  Bold,
  Code,
  Italic,
  Link as LinkIcon,
  List,
  ListOrdered,
  Strikethrough,
  Underline,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";

interface Props {
  value: string;
  onChange: (html: string) => void;
  ariaLabel?: string;
}

/**
 * Editor rich text de campos de nota (FR-014, MASTER.md §6): produz o mesmo HTML
 * aceito pelo allowlist nh3 do backend, com toggle para editar o HTML bruto.
 */
export default function RichTextEditor({ value, onChange, ariaLabel }: Props) {
  const [rawMode, setRawMode] = useState(false);

  const editor = useEditor({
    extensions: [
      StarterKit.configure({
        // somente marcas que o allowlist do backend aceita (apps/notes/sanitize.py)
        heading: false,
        blockquote: false,
        code: false,
        codeBlock: false,
        horizontalRule: false,
        link: { openOnClick: false },
      }),
    ],
    content: value,
    immediatelyRender: false,
    onUpdate: ({ editor }) => onChange(editor.getHTML()),
    editorProps: {
      attributes: {
        class:
          "min-h-24 rounded-b-lg bg-background p-3 text-base outline-none [&_ul]:list-disc [&_ol]:list-decimal [&_li]:ml-5 [&_a]:text-primary [&_a]:underline",
        ...(ariaLabel ? { "aria-label": ariaLabel } : {}),
      },
    },
  });

  // valor externo mudou (ex.: carregamento da nota ou edição em modo HTML)
  useEffect(() => {
    if (editor && !rawMode && value !== editor.getHTML()) {
      editor.commands.setContent(value);
    }
  }, [editor, rawMode, value]);

  const active = useEditorState({
    editor,
    selector: ({ editor: e }) => ({
      bold: e?.isActive("bold") ?? false,
      italic: e?.isActive("italic") ?? false,
      underline: e?.isActive("underline") ?? false,
      strike: e?.isActive("strike") ?? false,
      bulletList: e?.isActive("bulletList") ?? false,
      orderedList: e?.isActive("orderedList") ?? false,
      link: e?.isActive("link") ?? false,
    }),
  });

  function setLink() {
    if (!editor) return;
    if (editor.isActive("link")) {
      editor.chain().focus().unsetLink().run();
      return;
    }
    const href = window.prompt("URL do link (http/https):");
    if (href) editor.chain().focus().setLink({ href }).run();
  }

  const marks = [
    { icon: Bold, label: "Negrito", active: active?.bold, run: () => editor?.chain().focus().toggleBold().run() },
    { icon: Italic, label: "Itálico", active: active?.italic, run: () => editor?.chain().focus().toggleItalic().run() },
    { icon: Underline, label: "Sublinhado", active: active?.underline, run: () => editor?.chain().focus().toggleUnderline().run() },
    { icon: Strikethrough, label: "Riscado", active: active?.strike, run: () => editor?.chain().focus().toggleStrike().run() },
    { icon: List, label: "Lista", active: active?.bulletList, run: () => editor?.chain().focus().toggleBulletList().run() },
    { icon: ListOrdered, label: "Lista numerada", active: active?.orderedList, run: () => editor?.chain().focus().toggleOrderedList().run() },
    { icon: LinkIcon, label: "Link", active: active?.link, run: setLink },
  ];

  return (
    <div className="rounded-lg border focus-within:ring-2 focus-within:ring-ring/50">
      <div className="flex items-center gap-0.5 border-b p-1">
        {!rawMode &&
          marks.map(({ icon: Icon, label, active: isActive, run }) => (
            <Button
              key={label}
              type="button"
              variant="ghost"
              size="icon-sm"
              aria-label={label}
              aria-pressed={isActive}
              className={isActive ? "bg-muted text-foreground" : ""}
              onClick={run}
            >
              <Icon aria-hidden />
            </Button>
          ))}
        <Button
          type="button"
          variant="ghost"
          size="sm"
          aria-pressed={rawMode}
          className={`ml-auto ${rawMode ? "bg-muted text-foreground" : ""}`}
          onClick={() => setRawMode((raw) => !raw)}
        >
          <Code aria-hidden /> HTML
        </Button>
      </div>
      {rawMode ? (
        <Textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          aria-label={ariaLabel ? `${ariaLabel} (HTML bruto)` : "HTML bruto"}
          className="min-h-24 rounded-t-none border-0 font-mono text-sm"
        />
      ) : (
        <EditorContent editor={editor} />
      )}
    </div>
  );
}

"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { ShieldCheck } from "lucide-react";
import { api, ApiError } from "@/lib/api-client";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";

interface DeckDetail {
  id: string;
  name: string;
  note_types: {
    field_names: string[];
  }[];
}

interface ProtectionConfig {
  fields: string[];
  tags: string[];
}

function ProtectionForm({
  deckId,
  fieldNames,
  initial,
}: {
  deckId: string;
  fieldNames: string[];
  initial: ProtectionConfig;
}) {
  const [fields, setFields] = useState(() => new Set(initial.fields));
  const [tagsInput, setTagsInput] = useState(initial.tags.join(", "));
  const [saved, setSaved] = useState(false);
  const tags = tagsInput
    .split(",")
    .map((tag) => tag.trim())
    .filter(Boolean);

  const save = useMutation({
    mutationFn: () =>
      api.put<ProtectionConfig>(`/decks/${deckId}/protection/me/`, {
        fields: [...fields],
        tags,
      }),
    onSuccess: () => setSaved(true),
  });

  function toggleField(field: string, checked: boolean) {
    setSaved(false);
    setFields((current) => {
      const next = new Set(current);
      if (checked) next.add(field);
      else next.delete(field);
      return next;
    });
  }

  return (
    <form
      className="flex flex-col gap-6"
      onSubmit={(event) => {
        event.preventDefault();
        setSaved(false);
        save.mutate();
      }}
    >
      <fieldset className="flex flex-col gap-2">
        <legend className="mb-2 font-medium">Campos protegidos</legend>
        <p className="mb-2 max-w-[70ch] text-sm text-muted-foreground">
          O conteúdo local destes campos nunca será substituído por uma
          atualização do deck.
        </p>
        {fieldNames.map((field) => (
          <label
            key={field}
            className="flex min-h-11 cursor-pointer items-center gap-3 rounded-lg border p-3 hover:bg-muted"
          >
            <Checkbox
              checked={fields.has(field)}
              onCheckedChange={(checked) =>
                toggleField(field, checked === true)
              }
            />
            <span className="text-sm font-medium">{field}</span>
          </label>
        ))}
      </fieldset>

      <div className="flex flex-col gap-2">
        <Label htmlFor="protected-tags">Tags pessoais protegidas</Label>
        <Input
          id="protected-tags"
          value={tagsInput}
          onChange={(event) => {
            setSaved(false);
            setTagsInput(event.target.value);
          }}
          placeholder="Ex.: pessoal, revisar-depois"
        />
        <p className="text-sm text-muted-foreground">
          Separe por vírgulas. As tags internas “leech” e “marked” já são
          preservadas automaticamente.
        </p>
      </div>

      <div className="rounded-lg bg-muted p-3 text-sm">
        Para proteger só um campo de uma nota específica, adicione no Anki a tag{" "}
        <code>AnkiHubBR_Protect::NomeDoCampo</code>.
      </div>

      {save.isError && (
        <p role="alert" className="text-sm text-destructive">
          Não foi possível salvar a proteção. Revise as tags e tente novamente.
        </p>
      )}
      {saved && (
        <p role="status" className="text-sm text-success">
          Proteção atualizada.
        </p>
      )}

      <Button
        type="submit"
        className="min-h-11 self-start"
        disabled={save.isPending}
      >
        <ShieldCheck aria-hidden />
        {save.isPending ? "Salvando…" : "Salvar proteção"}
      </Button>
    </form>
  );
}

export default function ProtectionPage() {
  const { id } = useParams<{ id: string }>();
  const deck = useQuery<DeckDetail>({
    queryKey: ["deck", id],
    queryFn: () => api.get(`/decks/${id}/`),
    retry: false,
  });
  const config = useQuery<ProtectionConfig>({
    queryKey: ["protection", id],
    queryFn: () => api.get(`/decks/${id}/protection/me/`),
    retry: false,
  });
  const error = deck.error || config.error;

  if (error instanceof ApiError && error.status === 401) {
    return (
      <main className="mx-auto max-w-3xl p-4 md:p-6">
        <p>
          <Link href="/login" className="text-primary underline">
            Entre
          </Link>{" "}
          para configurar a proteção.
        </p>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-3xl p-4 md:p-6">
      <nav
        aria-label="Trilha de navegação"
        className="mb-4 text-sm text-muted-foreground"
      >
        <Link href="/decks" className="hover:text-foreground">
          Catálogo
        </Link>{" "}
        /{" "}
        <Link href={`/decks/${id}`} className="hover:text-foreground">
          {deck.data?.name ?? "Deck"}
        </Link>{" "}
        / <span className="text-foreground">Proteção pessoal</span>
      </nav>

      <h1 className="mb-2 text-2xl font-semibold tracking-tight">
        Proteção pessoal
      </h1>
      <p className="mb-6 max-w-[70ch] text-sm text-muted-foreground">
        Escolha o conteúdo local que deve sobreviver intacto às sincronizações.
      </p>

      {(deck.isPending || config.isPending) && (
        <div className="flex flex-col gap-3">
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-14 w-full" />
          <Skeleton className="h-24 w-full" />
        </div>
      )}

      {error && !(error instanceof ApiError && error.status === 401) && (
        <Alert variant="destructive">
          <AlertTitle>Não foi possível carregar a proteção</AlertTitle>
          <AlertDescription>
            Confirme que você assina este deck e tente novamente.
          </AlertDescription>
        </Alert>
      )}

      {deck.data && config.data && (
        <ProtectionForm
          deckId={id}
          fieldNames={[
            ...new Set(deck.data.note_types.flatMap((t) => t.field_names)),
          ]}
          initial={config.data}
        />
      )}
    </main>
  );
}

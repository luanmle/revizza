"use client";

import Link from "next/link";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Download, RotateCcw, Trash2 } from "lucide-react";
import { api, ApiError } from "@/lib/api-client";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";

interface Profile {
  email: string;
  consent_marketing_emails: boolean;
  consent_research_data: boolean;
  deletion_requested_at: string | null;
}

function scheduledDate(requestedAt: string): string {
  const date = new Date(requestedAt);
  date.setDate(date.getDate() + 7);
  return new Intl.DateTimeFormat("pt-BR", { dateStyle: "long" }).format(date);
}

export default function AccountPrivacyPage() {
  const queryClient = useQueryClient();
  const me = useQuery<Profile>({
    queryKey: ["me"],
    queryFn: () => api.get("/accounts/me/"),
    retry: false,
  });
  const refresh = () => queryClient.invalidateQueries({ queryKey: ["me"] });

  const consent = useMutation({
    mutationFn: (patch: Partial<Profile>) =>
      api.patch("/accounts/me/consents/", patch),
    onSuccess: refresh,
  });
  const exportData = useMutation({
    mutationFn: () => api.get<Record<string, unknown>>("/accounts/me/export/"),
    onSuccess: (data) => {
      const url = URL.createObjectURL(
        new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }),
      );
      const link = document.createElement("a");
      link.href = url;
      link.download = "ankihub-brasil-dados.json";
      link.click();
      URL.revokeObjectURL(url);
    },
  });
  const scheduleDeletion = useMutation({
    mutationFn: () => api.post("/accounts/me/deletion-request/"),
    onSuccess: refresh,
  });
  const cancelDeletion = useMutation({
    mutationFn: () => api.delete("/accounts/me/deletion-request/"),
    onSuccess: refresh,
  });

  if (me.error instanceof ApiError && me.error.status === 401) {
    return (
      <main className="mx-auto max-w-2xl p-4 md:p-6">
        <p>
          Você precisa{" "}
          <Link href="/login" className="text-primary underline">
            entrar
          </Link>{" "}
          para acessar sua privacidade.
        </p>
      </main>
    );
  }

  const mutationError =
    consent.isError ||
    exportData.isError ||
    scheduleDeletion.isError ||
    cancelDeletion.isError;

  return (
    <main className="mx-auto max-w-2xl p-4 md:p-6">
      <nav
        aria-label="Trilha de navegação"
        className="mb-4 text-sm text-muted-foreground"
      >
        <Link href="/account" className="hover:text-foreground">
          Minha conta
        </Link>{" "}
        / <span className="text-foreground">Privacidade</span>
      </nav>

      <h1 className="mb-2 text-2xl font-semibold tracking-tight">
        Privacidade e dados
      </h1>
      <p className="mb-8 max-w-[70ch] text-sm text-muted-foreground">
        Controle seus consentimentos, baixe seus dados e solicite a exclusão da conta.
      </p>

      {me.isPending && (
        <div className="flex flex-col gap-4">
          <Skeleton className="h-28 w-full" />
          <Skeleton className="h-28 w-full" />
        </div>
      )}

      {me.data && (
        <div className="flex flex-col gap-8">
          <section aria-labelledby="consents-title" className="border-b pb-8">
            <h2 id="consents-title" className="mb-2 text-lg font-semibold">
              Consentimentos
            </h2>
            <p className="mb-4 text-sm text-muted-foreground">
              Alterações têm efeito imediato.
            </p>
            <div className="flex flex-col gap-2">
              <label className="flex min-h-11 cursor-pointer items-center gap-3 rounded-lg border p-3">
                <Checkbox
                  checked={me.data.consent_marketing_emails}
                  disabled={consent.isPending}
                  onCheckedChange={(checked) =>
                    consent.mutate({ consent_marketing_emails: checked === true })
                  }
                />
                <span className="text-sm">Receber e-mails de novidades</span>
              </label>
              <label className="flex min-h-11 cursor-pointer items-center gap-3 rounded-lg border p-3">
                <Checkbox
                  checked={me.data.consent_research_data}
                  disabled={consent.isPending}
                  onCheckedChange={(checked) =>
                    consent.mutate({ consent_research_data: checked === true })
                  }
                />
                <span className="text-sm">
                  Autorizar uso de dados anonimizados em pesquisa
                </span>
              </label>
            </div>
          </section>

          <section aria-labelledby="export-title" className="border-b pb-8">
            <h2 id="export-title" className="mb-2 text-lg font-semibold">
              Exportar dados
            </h2>
            <p className="mb-4 max-w-[70ch] text-sm text-muted-foreground">
              Baixe um JSON com seu perfil, sugestões e comentários.
            </p>
            <Button
              variant="outline"
              className="min-h-11"
              disabled={exportData.isPending}
              onClick={() => exportData.mutate()}
            >
              <Download aria-hidden />
              {exportData.isPending ? "Preparando…" : "Baixar meus dados"}
            </Button>
          </section>

          <section aria-labelledby="deletion-title">
            <h2 id="deletion-title" className="mb-2 text-lg font-semibold">
              Excluir conta
            </h2>
            {me.data.deletion_requested_at ? (
              <Alert variant="destructive">
                <Trash2 aria-hidden />
                <AlertTitle>Exclusão agendada</AlertTitle>
                <AlertDescription>
                  Sua conta será excluída em{" "}
                  {scheduledDate(me.data.deletion_requested_at)}. Você pode cancelar
                  durante a carência.
                  <Button
                    variant="outline"
                    className="mt-4 min-h-11"
                    disabled={cancelDeletion.isPending}
                    onClick={() => cancelDeletion.mutate()}
                  >
                    <RotateCcw aria-hidden />
                    {cancelDeletion.isPending ? "Cancelando…" : "Cancelar exclusão"}
                  </Button>
                </AlertDescription>
              </Alert>
            ) : (
              <>
                <p className="mb-4 max-w-[70ch] text-sm text-muted-foreground">
                  A exclusão é agendada com carência de 7 dias. Depois desse prazo, seu
                  perfil e conteúdo autoral serão removidos.
                </p>
                <Button
                  variant="destructive"
                  className="min-h-11"
                  disabled={scheduleDeletion.isPending}
                  onClick={() => {
                    if (
                      window.confirm(
                        "Agendar a exclusão da conta para daqui a 7 dias?",
                      )
                    ) {
                      scheduleDeletion.mutate();
                    }
                  }}
                >
                  <Trash2 aria-hidden />
                  {scheduleDeletion.isPending
                    ? "Agendando…"
                    : "Agendar exclusão da conta"}
                </Button>
              </>
            )}
          </section>

          {mutationError && (
            <p role="alert" className="text-sm text-destructive">
              Não foi possível concluir a ação. Tente novamente.
            </p>
          )}
        </div>
      )}
    </main>
  );
}

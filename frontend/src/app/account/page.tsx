"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Skeleton } from "@/components/ui/skeleton";
import { api, ApiError } from "@/lib/api-client";

interface Profile {
  email: string;
  target_career: string | null;
  target_board: string | null;
  consent_marketing_emails: boolean;
  consent_research_data: boolean;
}

export default function AccountPage() {
  const queryClient = useQueryClient();
  const { data: me, error } = useQuery<Profile>({
    queryKey: ["me"],
    queryFn: () => api.get<Profile>("/accounts/me/"),
    retry: false,
  });

  const updateConsent = useMutation({
    // FR-045: efeito imediato ao alternar
    mutationFn: (patch: Partial<Profile>) =>
      api.patch<Profile>("/accounts/me/consents/", patch),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["me"] }),
  });

  if (error instanceof ApiError && error.status === 401) {
    return (
      <main className="mx-auto w-full max-w-2xl p-4 md:p-6">
        <Alert>
          <AlertDescription>
            Você precisa <Link href="/login">entrar</Link> para acessar sua
            conta.
          </AlertDescription>
        </Alert>
      </main>
    );
  }
  if (!me) {
    return (
      <main className="mx-auto w-full max-w-2xl p-4 md:p-6">
        <span className="sr-only">Carregando conta…</span>
        <Skeleton className="mb-4 h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-2xl p-4 md:p-6">
      <h1 className="mb-2 text-2xl font-semibold tracking-tight">
        Minha conta
      </h1>
      <p className="mb-8 text-sm text-muted-foreground">
        Perfil e preferências de privacidade.
      </p>

      <div className="grid gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Perfil</CardTitle>
            <CardDescription>{me.email}</CardDescription>
          </CardHeader>
          {(me.target_career || me.target_board) && (
            <CardContent className="grid gap-2 text-sm">
              {me.target_career && (
                <p>
                  <span className="text-muted-foreground">Carreira alvo:</span>{" "}
                  {me.target_career}
                </p>
              )}
              {me.target_board && (
                <p>
                  <span className="text-muted-foreground">
                    Banca ou edital:
                  </span>{" "}
                  {me.target_board}
                </p>
              )}
            </CardContent>
          )}
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Consentimentos (LGPD)</CardTitle>
            <CardDescription>
              As alterações são salvas e entram em vigor imediatamente.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <label
              htmlFor="marketing-consent"
              className="flex min-h-11 cursor-pointer items-center gap-3 rounded-lg border p-3"
            >
              <Checkbox
                id="marketing-consent"
                checked={me.consent_marketing_emails}
                disabled={updateConsent.isPending}
                onCheckedChange={(checked) =>
                  updateConsent.mutate({
                    consent_marketing_emails: checked === true,
                  })
                }
              />
              <span className="text-sm">Receber e-mails de novidades</span>
            </label>
            <label
              htmlFor="research-consent"
              className="flex min-h-11 cursor-pointer items-center gap-3 rounded-lg border p-3"
            >
              <Checkbox
                id="research-consent"
                checked={me.consent_research_data}
                disabled={updateConsent.isPending}
                onCheckedChange={(checked) =>
                  updateConsent.mutate({
                    consent_research_data: checked === true,
                  })
                }
              />
              <span className="text-sm">
                Uso de dados anonimizados em pesquisa
              </span>
            </label>
            {updateConsent.isError && (
              <p role="alert" className="text-sm text-destructive">
                Não foi possível salvar o consentimento. Tente novamente.
              </p>
            )}
          </CardContent>
        </Card>

        <Button
          variant="outline"
          size="lg"
          className="justify-start"
          nativeButton={false}
          render={<Link href="/account/privacy" />}
        >
          <ShieldCheck aria-hidden />
          Privacidade, exportação e exclusão
        </Button>
      </div>
    </main>
  );
}

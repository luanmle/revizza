"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
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
      <main className="form-page">
        <p>
          Você precisa <Link href="/login">entrar</Link> para acessar sua conta.
        </p>
      </main>
    );
  }
  if (!me) return <main className="form-page">Carregando…</main>;

  return (
    <main className="form-page">
      <h1>Minha conta</h1>
      <p>{me.email}</p>
      {me.target_career && <p>Carreira alvo: {me.target_career}</p>}
      {me.target_board && <p>Banca/edital: {me.target_board}</p>}

      <h2>Consentimentos (LGPD)</h2>
      <label className="checkbox">
        <input
          type="checkbox"
          checked={me.consent_marketing_emails}
          disabled={updateConsent.isPending}
          onChange={(e) =>
            updateConsent.mutate({ consent_marketing_emails: e.target.checked })
          }
        />
        Receber e-mails de novidades
      </label>
      <label className="checkbox">
        <input
          type="checkbox"
          checked={me.consent_research_data}
          disabled={updateConsent.isPending}
          onChange={(e) =>
            updateConsent.mutate({ consent_research_data: e.target.checked })
          }
        />
        Uso de dados anonimizados em pesquisa
      </label>
      <p>
        <Link href="/account/privacy">Privacidade, exportação e exclusão</Link>
      </p>
    </main>
  );
}

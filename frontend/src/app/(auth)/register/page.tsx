"use client";

import { useState } from "react";
import Link from "next/link";
import { api, ApiError } from "@/lib/api-client";

const CAREERS = [
  ["", "Prefiro não informar"],
  ["fiscal", "Fiscal"],
  ["policial", "Policial"],
  ["juridica", "Jurídica"],
  ["outra", "Outra"],
] as const;

export default function RegisterPage() {
  const [error, setError] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    const form = new FormData(event.currentTarget);
    try {
      await api.post("/accounts/register/", {
        email: form.get("email"),
        password: form.get("password"),
        target_career: form.get("target_career") || null,
        target_board: form.get("target_board") || "",
        // FR-005: só true se o usuário marcou — nunca pré-marcado
        consent_marketing_emails: form.get("consent_marketing_emails") === "on",
        consent_research_data: form.get("consent_research_data") === "on",
      });
      setDone(true);
    } catch (e) {
      setError(
        e instanceof ApiError && e.body && typeof e.body === "object"
          ? JSON.stringify(e.body)
          : "Não foi possível concluir o cadastro. Tente novamente.",
      );
    } finally {
      setSubmitting(false);
    }
  }

  if (done) {
    return (
      <main className="form-page">
        <h1>Conta criada!</h1>
        <p>
          Enviamos um e-mail de verificação. Confirme seu endereço e depois{" "}
          <Link href="/login">faça login</Link>.
        </p>
      </main>
    );
  }

  return (
    <main className="form-page">
      <h1>Criar conta</h1>
      <form onSubmit={onSubmit}>
        <label>
          E-mail
          <input name="email" type="email" required autoComplete="email" />
        </label>
        <label>
          Senha
          <input
            name="password"
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
          />
        </label>

        <fieldset>
          <legend>Opcional: personalize suas recomendações</legend>
          <label>
            Carreira alvo
            <select name="target_career" defaultValue="">
              {CAREERS.map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label>
            Banca ou edital de interesse
            <input name="target_board" type="text" placeholder="ex.: CEBRASPE" />
          </label>
        </fieldset>

        <fieldset>
          <legend>Privacidade (LGPD)</legend>
          <label className="checkbox">
            <input name="consent_marketing_emails" type="checkbox" />
            Aceito receber e-mails de novidades
          </label>
          <label className="checkbox">
            <input name="consent_research_data" type="checkbox" />
            Autorizo o uso de dados anonimizados em pesquisa
          </label>
        </fieldset>

        {error && <p role="alert">{error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? "Criando…" : "Criar conta"}
        </button>
      </form>
      <p>
        Já tem conta? <Link href="/login">Entrar</Link>
      </p>
    </main>
  );
}

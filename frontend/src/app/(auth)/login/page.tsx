"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setSubmitting(true);
    const form = new FormData(event.currentTarget);
    const { error } = await supabase.auth.signInWithPassword({
      email: String(form.get("email")),
      password: String(form.get("password")),
    });
    setSubmitting(false);
    if (error) {
      setError("E-mail ou senha inválidos, ou e-mail ainda não confirmado.");
      return;
    }
    router.push("/account");
  }

  return (
    <main className="form-page">
      <h1>Entrar</h1>
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
            autoComplete="current-password"
          />
        </label>
        {error && <p role="alert">{error}</p>}
        <button type="submit" disabled={submitting}>
          {submitting ? "Entrando…" : "Entrar"}
        </button>
      </form>
      <p>
        <Link href="/password-reset">Esqueci minha senha</Link>
      </p>
      <p>
        Não tem conta? <Link href="/register">Cadastre-se</Link>
      </p>
    </main>
  );
}

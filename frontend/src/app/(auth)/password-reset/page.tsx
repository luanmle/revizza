"use client";

import { useState } from "react";
import Link from "next/link";
import { api } from "@/lib/api-client";

export default function PasswordResetPage() {
  const [sent, setSent] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    await api.post("/accounts/password-reset/", { email: form.get("email") });
    setSent(true);
  }

  return (
    <main className="form-page">
      <h1>Recuperar senha</h1>
      {sent ? (
        <p>
          Se o e-mail existir, você receberá um link de redefinição.{" "}
          <Link href="/login">Voltar ao login</Link>
        </p>
      ) : (
        <form onSubmit={onSubmit}>
          <label>
            E-mail
            <input name="email" type="email" required autoComplete="email" />
          </label>
          <button type="submit">Enviar link de recuperação</button>
        </form>
      )}
    </main>
  );
}

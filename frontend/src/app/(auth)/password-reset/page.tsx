"use client";

import { useState } from "react";
import Link from "next/link";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api-client";

export default function PasswordResetPage() {
  const [error, setError] = useState(false);
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setError(false);
    setSubmitting(true);
    try {
      await api.post("/accounts/password-reset/", { email: form.get("email") });
      setSent(true);
    } catch {
      setError(true);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-md p-4 py-10 md:p-6 md:py-16">
      <Card>
        <CardHeader>
          <h1
            data-slot="card-title"
            className="font-heading text-2xl leading-snug font-semibold tracking-tight"
          >
            Recuperar senha
          </h1>
          <CardDescription>
            Informe o e-mail usado no cadastro para receber um link seguro.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {sent ? (
            <Alert>
              <CheckCircle2 className="text-success" aria-hidden />
              <AlertDescription>
                Se o e-mail existir, você receberá um link de redefinição.
              </AlertDescription>
            </Alert>
          ) : (
            <form className="flex flex-col gap-4" onSubmit={onSubmit}>
              <div className="grid gap-2">
                <Label htmlFor="email">E-mail</Label>
                <Input
                  id="email"
                  name="email"
                  type="email"
                  required
                  autoComplete="email"
                />
              </div>
              {error && (
                <Alert variant="destructive">
                  <AlertCircle aria-hidden />
                  <AlertDescription>
                    Não foi possível enviar o link. Tente novamente.
                  </AlertDescription>
                </Alert>
              )}
              <Button type="submit" size="lg" disabled={submitting}>
                {submitting ? "Enviando…" : "Enviar link de recuperação"}
              </Button>
            </form>
          )}
        </CardContent>
        <CardFooter className="justify-center text-sm">
          <Link
            href="/login"
            className="font-medium text-primary underline-offset-4 hover:underline"
          >
            Voltar ao login
          </Link>
        </CardFooter>
      </Card>
    </main>
  );
}

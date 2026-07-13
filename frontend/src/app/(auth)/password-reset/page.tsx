"use client";

import { useState } from "react";
import Link from "next/link";
import { CheckCircle2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { api } from "@/lib/api-client";

export default function PasswordResetPage() {
  const [sent, setSent] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setSubmitting(true);
    try {
      await api.post("/accounts/password-reset/", { email: form.get("email") });
      setSent(true);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="mx-auto w-full max-w-md p-4 py-10 md:p-6 md:py-16">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-semibold tracking-tight">
            Recuperar senha
          </CardTitle>
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

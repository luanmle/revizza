"use client";

import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { AlertCircle } from "lucide-react";
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
    <main className="mx-auto w-full max-w-md p-4 py-10 md:p-6 md:py-16">
      <Card>
        <CardHeader>
          <h1
            data-slot="card-title"
            className="font-heading text-2xl leading-snug font-semibold tracking-tight"
          >
            Entrar
          </h1>
          <CardDescription>
            Acesse seus decks, notas e sugestões da comunidade.
          </CardDescription>
        </CardHeader>
        <CardContent>
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
            <div className="grid gap-2">
              <div className="flex items-center justify-between gap-4">
                <Label htmlFor="password">Senha</Label>
                <Link
                  href="/password-reset"
                  className="text-sm text-primary underline-offset-4 hover:underline"
                >
                  Esqueci minha senha
                </Link>
              </div>
              <Input
                id="password"
                name="password"
                type="password"
                required
                autoComplete="current-password"
              />
            </div>
            {error && (
              <Alert variant="destructive">
                <AlertCircle aria-hidden />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <Button type="submit" size="lg" disabled={submitting}>
              {submitting ? "Entrando…" : "Entrar"}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="justify-center text-sm text-muted-foreground">
          Não tem conta?&nbsp;
          <Link
            href="/register"
            className="font-medium text-primary underline-offset-4 hover:underline"
          >
            Cadastre-se
          </Link>
        </CardFooter>
      </Card>
    </main>
  );
}

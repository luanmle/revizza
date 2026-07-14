"use client";

import { useEffect, useState } from "react";
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
  CardTitle,
} from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { supabase } from "@/lib/supabase";

type RecoveryStatus = "checking" | "ready" | "invalid" | "success";

export default function PasswordResetCallbackPage() {
  const [status, setStatus] = useState<RecoveryStatus>("checking");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    let active = true;
    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((event, session) => {
      if (active && event === "PASSWORD_RECOVERY" && session) {
        setStatus("ready");
      }
    });

    void supabase.auth.getSession().then(({ data, error }) => {
      if (!active) return;
      setStatus(!error && data.session ? "ready" : "invalid");
    });

    return () => {
      active = false;
      subscription.unsubscribe();
    };
  }, []);

  async function onSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const password = String(form.get("password"));
    const confirmation = String(form.get("password-confirmation"));

    setError(null);
    if (password !== confirmation) {
      setError("As senhas não coincidem.");
      return;
    }

    setSubmitting(true);
    const { error } = await supabase.auth.updateUser({ password });
    setSubmitting(false);
    if (error) {
      setError("Não foi possível alterar a senha. Solicite um novo link.");
      return;
    }
    setStatus("success");
  }

  return (
    <main className="mx-auto w-full max-w-md p-4 py-10 md:p-6 md:py-16">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-semibold tracking-tight">
            Criar nova senha
          </CardTitle>
          <CardDescription>
            Escolha uma senha diferente da anterior para proteger sua conta.
          </CardDescription>
        </CardHeader>
        <CardContent aria-live="polite">
          {status === "checking" && (
            <div
              className="grid gap-3"
              aria-label="Validando link de recuperação"
            >
              <Skeleton className="h-11 w-full" />
              <Skeleton className="h-11 w-full" />
              <Skeleton className="h-11 w-full" />
            </div>
          )}

          {status === "invalid" && (
            <Alert variant="destructive">
              <AlertCircle aria-hidden />
              <AlertDescription>
                Este link é inválido ou expirou. Solicite uma nova recuperação.
              </AlertDescription>
            </Alert>
          )}

          {status === "success" && (
            <Alert>
              <CheckCircle2 className="text-success" aria-hidden />
              <AlertDescription>
                Senha alterada. Você já pode usar a nova senha.
              </AlertDescription>
            </Alert>
          )}

          {status === "ready" && (
            <form className="flex flex-col gap-4" onSubmit={onSubmit}>
              <div className="grid gap-2">
                <Label htmlFor="password">Nova senha</Label>
                <Input
                  id="password"
                  name="password"
                  type="password"
                  required
                  minLength={8}
                  autoComplete="new-password"
                  aria-describedby="password-help"
                />
                <p id="password-help" className="text-xs text-muted-foreground">
                  Use pelo menos 8 caracteres.
                </p>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="password-confirmation">
                  Confirmar nova senha
                </Label>
                <Input
                  id="password-confirmation"
                  name="password-confirmation"
                  type="password"
                  required
                  minLength={8}
                  autoComplete="new-password"
                />
              </div>
              {error && (
                <Alert variant="destructive">
                  <AlertCircle aria-hidden />
                  <AlertDescription>{error}</AlertDescription>
                </Alert>
              )}
              <Button type="submit" size="lg" disabled={submitting}>
                {submitting ? "Alterando…" : "Alterar senha"}
              </Button>
            </form>
          )}
        </CardContent>
        <CardFooter className="justify-center text-sm">
          <Link
            href={status === "invalid" ? "/password-reset" : "/login"}
            className="font-medium text-primary underline-offset-4 hover:underline"
          >
            {status === "invalid" ? "Solicitar novo link" : "Voltar ao login"}
          </Link>
        </CardFooter>
      </Card>
    </main>
  );
}

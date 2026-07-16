"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { AlertCircle, CheckCircle2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { supabase } from "@/lib/supabase";

type Status = "checking" | "success" | "invalid";

export default function VerifyEmailPage() {
  const [status, setStatus] = useState<Status>("checking");

  useEffect(() => {
    async function verifyEmail() {
      const params = new URLSearchParams(window.location.search);
      const tokenHash = params.get("token_hash");
      const token = params.get("token");
      const email = params.get("email");
      const type = params.get("type") || "email";

      if (!tokenHash && (!token || !email)) {
        setStatus("invalid");
        return;
      }

      const result = tokenHash
        ? await supabase.auth.verifyOtp({ token_hash: tokenHash, type: type as "email" })
        : await supabase.auth.verifyOtp({
            email: email!,
            token: token!,
            type: type as "email",
          });
      setStatus(result.error ? "invalid" : "success");
    }

    void verifyEmail();
  }, []);

  return (
    <main className="mx-auto w-full max-w-md p-4 py-10 md:p-6 md:py-16">
      <Card>
        <CardHeader>
          <h1
            data-slot="card-title"
            className="font-heading text-2xl leading-snug font-semibold tracking-tight"
          >
            Confirmar e-mail
          </h1>
        </CardHeader>
        <CardContent aria-live="polite">
          {status === "checking" && (
            <Skeleton className="h-16 w-full" aria-label="Validando e-mail" />
          )}
          {status === "success" && (
            <Alert>
              <CheckCircle2 className="text-success" aria-hidden />
              <AlertDescription>
                E-mail confirmado. <Link href="/login">Faça login</Link> para continuar.
              </AlertDescription>
            </Alert>
          )}
          {status === "invalid" && (
            <Alert variant="destructive">
              <AlertCircle aria-hidden />
              <AlertDescription>
                Este link é inválido ou expirou. Solicite um novo cadastro ou tente novamente.
              </AlertDescription>
            </Alert>
          )}
        </CardContent>
      </Card>
    </main>
  );
}

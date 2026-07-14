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
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { api, ApiError } from "@/lib/api-client";

const CAREERS = [
  ["", "Prefiro não informar"],
  ["fiscal", "Fiscal"],
  ["policial", "Policial"],
  ["juridica", "Jurídica"],
  ["outra", "Outra"],
] as const;

export default function RegisterPage() {
  const [targetCareer, setTargetCareer] = useState("");
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
        name: form.get("name") || "",
        email: form.get("email"),
        password: form.get("password"),
        target_career: targetCareer || null,
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
      <main className="mx-auto w-full max-w-md p-4 py-10 md:p-6 md:py-16">
        <Alert>
          <CheckCircle2 className="text-success" aria-hidden />
          <AlertDescription>
            <strong className="mb-1 block text-foreground">
              Conta criada!
            </strong>
            Enviamos um e-mail de verificação. Confirme seu endereço e depois{" "}
            <Link href="/login">faça login</Link>.
          </AlertDescription>
        </Alert>
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-md p-4 py-10 md:p-6 md:py-16">
      <Card>
        <CardHeader>
          <CardTitle className="text-2xl font-semibold tracking-tight">
            Criar conta
          </CardTitle>
          <CardDescription>
            Comece a estudar e colaborar com decks da comunidade.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form className="flex flex-col gap-6" onSubmit={onSubmit}>
            <div className="grid gap-4">
              <div className="grid gap-2">
                <Label htmlFor="name">
                  Nome{" "}
                  <span className="font-normal text-muted-foreground">
                    (opcional)
                  </span>
                </Label>
                <Input
                  id="name"
                  name="name"
                  type="text"
                  maxLength={120}
                  autoComplete="name"
                  placeholder="Como você quer aparecer na comunidade"
                />
              </div>
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
                <Label htmlFor="password">Senha</Label>
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
            </div>

            <fieldset className="grid gap-4 border-t pt-5">
              <legend className="px-1 text-sm font-semibold">
                Recomendações{" "}
                <span className="font-normal text-muted-foreground">
                  (opcional)
                </span>
              </legend>
              <div className="grid gap-2">
                <Label htmlFor="target-career">Carreira alvo</Label>
                <Select
                  value={targetCareer}
                  onValueChange={(value) => setTargetCareer(value ?? "")}
                  items={CAREERS.map(([value, label]) => ({ value, label }))}
                >
                  <SelectTrigger id="target-career" className="h-11 w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {CAREERS.map(([value, label]) => (
                      <SelectItem key={value} value={value}>
                        {label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid gap-2">
                <Label htmlFor="target-board">
                  Banca ou edital de interesse
                </Label>
                <Input
                  id="target-board"
                  name="target_board"
                  type="text"
                  placeholder="Ex.: Cebraspe"
                />
              </div>
            </fieldset>

            <fieldset className="grid gap-3 border-t pt-5">
              <legend className="px-1 text-sm font-semibold">
                Privacidade (LGPD)
              </legend>
              <label className="flex min-h-11 cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm">
                <Checkbox name="consent_marketing_emails" />
                Aceito receber e-mails de novidades
              </label>
              <label className="flex min-h-11 cursor-pointer items-center gap-3 rounded-lg border p-3 text-sm">
                <Checkbox name="consent_research_data" />
                Autorizo o uso de dados anonimizados em pesquisa
              </label>
              <p className="text-xs text-muted-foreground">
                Nenhuma opção vem marcada. Você pode alterar ambas depois.
              </p>
            </fieldset>

            {error && (
              <Alert variant="destructive">
                <AlertCircle aria-hidden />
                <AlertDescription>{error}</AlertDescription>
              </Alert>
            )}
            <Button type="submit" size="lg" disabled={submitting}>
              {submitting ? "Criando…" : "Criar conta"}
            </Button>
          </form>
        </CardContent>
        <CardFooter className="justify-center text-sm text-muted-foreground">
          Já tem conta?&nbsp;
          <Link
            href="/login"
            className="font-medium text-primary underline-offset-4 hover:underline"
          >
            Entrar
          </Link>
        </CardFooter>
      </Card>
    </main>
  );
}

"use client";

import { useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import Link from "next/link";
import { ShieldCheck } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { UserAvatar } from "@/components/user-avatar";
import { api, ApiError } from "@/lib/api-client";

interface Profile {
  name: string;
  email: string;
  avatar_url: string | null;
  target_career: string | null;
  target_board: string | null;
  consent_marketing_emails: boolean;
  consent_research_data: boolean;
}

const TARGET_CAREERS = [
  { value: "fiscal", label: "Fiscal" },
  { value: "policial", label: "Policial" },
  { value: "juridica", label: "Jurídica" },
  { value: "outra", label: "Outra" },
];

export default function AccountPage() {
  const queryClient = useQueryClient();
  const avatarInputRef = useRef<HTMLInputElement>(null);
  const [avatarError, setAvatarError] = useState("");
  const [selectedAvatarName, setSelectedAvatarName] = useState("");
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
  const updateProfile = useMutation({
    mutationFn: (name: string) => api.patch<Profile>("/accounts/me/", { name }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["me"] }),
  });
  const updateCareer = useMutation({
    mutationFn: (patch: Pick<Profile, "target_career" | "target_board">) =>
      api.patch<Profile>("/accounts/me/", patch),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["me"] }),
  });
  const uploadAvatar = useMutation({
    mutationFn: (file: File) => {
      const form = new FormData();
      form.append("avatar", file);
      return api.patchForm<Profile>("/accounts/me/", form);
    },
    onSuccess: () => {
      setAvatarError("");
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
    onError: (err: unknown) => {
      const body =
        err instanceof ApiError
          ? (err.body as { avatar?: string[] } | null)
          : null;
      setSelectedAvatarName("");
      setAvatarError(body?.avatar?.[0] ?? "Não foi possível enviar a foto.");
    },
  });
  const removeAvatar = useMutation({
    mutationFn: () => api.patch<Profile>("/accounts/me/", { avatar: null }),
    onSuccess: () => {
      setAvatarError("");
      setSelectedAvatarName("");
      queryClient.invalidateQueries({ queryKey: ["me"] });
    },
    onError: () => setAvatarError("Não foi possível remover a foto."),
  });

  if (error instanceof ApiError && error.status === 401) {
    return (
      <main className="mx-auto w-full max-w-2xl p-4 md:p-6">
        <Alert>
          <AlertDescription>
            Você precisa <Link href="/login">entrar</Link> para acessar sua
            conta.
          </AlertDescription>
        </Alert>
      </main>
    );
  }
  if (!me) {
    return (
      <main className="mx-auto w-full max-w-2xl p-4 md:p-6">
        <span className="sr-only">Carregando conta…</span>
        <Skeleton className="mb-4 h-8 w-48" />
        <Skeleton className="h-64 w-full" />
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-2xl p-4 md:p-6">
      <h1 className="mb-2 text-2xl font-semibold tracking-tight">
        Minha conta
      </h1>
      <p className="mb-8 text-sm text-muted-foreground">
        Perfil e preferências de privacidade.
      </p>

      <div className="grid gap-4">
        <Card>
          <CardHeader>
            <CardTitle>Perfil</CardTitle>
            <CardDescription>{me.email}</CardDescription>
          </CardHeader>
          <CardContent className="grid gap-4">
            <div className="flex items-center gap-4">
              <UserAvatar
                avatarUrl={me.avatar_url}
                name={me.name || me.email}
                className="size-16 text-lg"
              />
              <div className="min-w-0 flex-1">
                <input
                  ref={avatarInputRef}
                  id="avatar-upload"
                  type="file"
                  aria-label="Foto de perfil"
                  accept="image/jpeg,image/png,image/webp"
                  className="sr-only"
                  tabIndex={-1}
                  disabled={uploadAvatar.isPending}
                  onChange={(event) => {
                    const file = event.target.files?.[0];
                    setAvatarError("");
                    setSelectedAvatarName(file?.name ?? "");
                    if (file) uploadAvatar.mutate(file);
                    event.target.value = "";
                  }}
                />
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    disabled={uploadAvatar.isPending || removeAvatar.isPending}
                    onClick={() => {
                      setAvatarError("");
                      setSelectedAvatarName("");
                      avatarInputRef.current?.click();
                    }}
                  >
                    {uploadAvatar.isPending ? "Enviando…" : "Alterar foto"}
                  </Button>
                  {me.avatar_url && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      disabled={
                        uploadAvatar.isPending || removeAvatar.isPending
                      }
                      onClick={() => removeAvatar.mutate()}
                    >
                      {removeAvatar.isPending ? "Removendo…" : "Remover foto"}
                    </Button>
                  )}
                </div>
                <p
                  id="avatar-upload-status"
                  aria-live="polite"
                  className="mt-2 break-words text-sm text-muted-foreground"
                >
                  {uploadAvatar.isPending
                    ? `Enviando ${selectedAvatarName}…`
                    : selectedAvatarName
                      ? `Arquivo enviado: ${selectedAvatarName}`
                      : "Nenhum arquivo selecionado."}
                </p>
              </div>
            </div>
            {avatarError && (
              <p role="alert" className="text-sm text-destructive">
                {avatarError}
              </p>
            )}
            <form
              className="grid gap-2"
              onSubmit={(event) => {
                event.preventDefault();
                const form = new FormData(event.currentTarget);
                updateProfile.mutate(String(form.get("name") ?? "").trim());
              }}
            >
              <Label htmlFor="profile-name">Nome na comunidade</Label>
              <div className="flex flex-col gap-2 sm:flex-row">
                <Input
                  id="profile-name"
                  name="name"
                  defaultValue={me.name}
                  maxLength={120}
                  autoComplete="name"
                  placeholder="Seu nome (opcional)"
                />
                <Button
                  type="submit"
                  variant="outline"
                  disabled={updateProfile.isPending}
                >
                  {updateProfile.isPending ? "Salvando…" : "Salvar nome"}
                </Button>
              </div>
              <p className="text-sm text-muted-foreground">
                Usado como autoria nas sugestões e discussões.
              </p>
              {updateProfile.isError && (
                <p role="alert" className="text-sm text-destructive">
                  Não foi possível salvar o nome.
                </p>
              )}
            </form>
            <form
              className="grid gap-3 sm:grid-cols-2"
              onSubmit={(event) => {
                event.preventDefault();
                const form = new FormData(event.currentTarget);
                updateCareer.mutate({
                  target_career: (form.get("target_career") as string) || null,
                  target_board:
                    String(form.get("target_board") ?? "").trim() || null,
                });
              }}
            >
              <div className="flex flex-col gap-1">
                <Label htmlFor="target-career">Carreira alvo</Label>
                <Select
                  name="target_career"
                  defaultValue={me.target_career ?? undefined}
                  items={TARGET_CAREERS}
                >
                  <SelectTrigger id="target-career" className="w-full">
                    <SelectValue placeholder="Selecione" />
                  </SelectTrigger>
                  <SelectContent>
                    {TARGET_CAREERS.map((c) => (
                      <SelectItem key={c.value} value={c.value}>
                        {c.label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="flex flex-col gap-1">
                <Label htmlFor="target-board">Banca ou edital</Label>
                <Input
                  id="target-board"
                  name="target_board"
                  defaultValue={me.target_board ?? ""}
                  maxLength={120}
                  placeholder="Ex.: CESPE/CEBRASPE"
                />
              </div>
              <div className="sm:col-span-2">
                <Button
                  type="submit"
                  variant="outline"
                  disabled={updateCareer.isPending}
                >
                  {updateCareer.isPending ? "Salvando…" : "Salvar carreira"}
                </Button>
              </div>
              {updateCareer.isError && (
                <p
                  role="alert"
                  className="text-sm text-destructive sm:col-span-2"
                >
                  Não foi possível salvar a carreira alvo.
                </p>
              )}
            </form>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Consentimentos (LGPD)</CardTitle>
            <CardDescription>
              As alterações são salvas e entram em vigor imediatamente.
            </CardDescription>
          </CardHeader>
          <CardContent className="grid gap-3">
            <label
              htmlFor="marketing-consent"
              className="flex min-h-11 cursor-pointer items-center gap-3 rounded-lg border p-3"
            >
              <Checkbox
                id="marketing-consent"
                checked={me.consent_marketing_emails}
                disabled={updateConsent.isPending}
                onCheckedChange={(checked) =>
                  updateConsent.mutate({
                    consent_marketing_emails: checked === true,
                  })
                }
              />
              <span className="text-sm">Receber e-mails de novidades</span>
            </label>
            <label
              htmlFor="research-consent"
              className="flex min-h-11 cursor-pointer items-center gap-3 rounded-lg border p-3"
            >
              <Checkbox
                id="research-consent"
                checked={me.consent_research_data}
                disabled={updateConsent.isPending}
                onCheckedChange={(checked) =>
                  updateConsent.mutate({
                    consent_research_data: checked === true,
                  })
                }
              />
              <span className="text-sm">
                Uso de dados anonimizados em pesquisa
              </span>
            </label>
            {updateConsent.isError && (
              <p role="alert" className="text-sm text-destructive">
                Não foi possível salvar o consentimento. Tente novamente.
              </p>
            )}
          </CardContent>
        </Card>

        <Button
          variant="outline"
          size="lg"
          className="justify-start"
          nativeButton={false}
          render={<Link href="/account/privacy" />}
        >
          <ShieldCheck aria-hidden />
          Privacidade, exportação e exclusão
        </Button>
      </div>
    </main>
  );
}

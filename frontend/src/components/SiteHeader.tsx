"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { CircleUser } from "lucide-react";
import { supabase } from "@/lib/supabase";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import ThemeToggle from "@/components/ThemeToggle";

/** Navegação global (MASTER.md §8): logo, catálogo, tema e menu autenticado/anônimo. */
export default function SiteHeader() {
  const router = useRouter();
  const [authenticated, setAuthenticated] = useState<boolean | null>(null);

  useEffect(() => {
    supabase.auth
      .getSession()
      .then(({ data }) => setAuthenticated(!!data.session));
    const { data: sub } = supabase.auth.onAuthStateChange((_event, session) =>
      setAuthenticated(!!session),
    );
    return () => sub.subscription.unsubscribe();
  }, []);

  async function signOut() {
    await supabase.auth.signOut();
    router.push("/login");
  }

  return (
    <header className="sticky top-0 z-40 border-b bg-background/95 backdrop-blur">
      <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
        <Link href="/decks" className="font-semibold">
          AnkiHub <span className="text-primary">Brasil</span>
        </Link>
        <nav className="flex items-center gap-1">
          <Link
            href="/decks"
            className="hidden px-3 text-sm text-muted-foreground hover:text-foreground sm:block"
          >
            Catálogo
          </Link>
          <ThemeToggle />
          {authenticated === false && (
            <>
              <Button
                variant="ghost"
                size="sm"
                nativeButton={false}
                render={<Link href="/login" />}
              >
                Entrar
              </Button>
              <Button
                size="sm"
                nativeButton={false}
                render={<Link href="/register" />}
              >
                Criar conta
              </Button>
            </>
          )}
          {authenticated && (
            <DropdownMenu>
              <DropdownMenuTrigger
                render={
                  <Button
                    variant="ghost"
                    size="icon"
                    aria-label="Menu do usuário"
                  />
                }
              >
                <CircleUser className="size-5" aria-hidden />
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem render={<Link href="/account" />}>
                  Minha conta
                </DropdownMenuItem>
                <DropdownMenuItem onClick={signOut}>Sair</DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          )}
        </nav>
      </div>
    </header>
  );
}

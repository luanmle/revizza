import Link from "next/link";
import { ArrowRight, BookOpenCheck } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function Home() {
  return (
    <main className="mx-auto flex w-full max-w-3xl flex-1 flex-col justify-center gap-6 p-4 py-12 md:p-6">
      <BookOpenCheck aria-hidden className="size-10 text-primary" />
      <div className="max-w-2xl space-y-3">
        <h1 className="text-3xl font-semibold tracking-tight text-balance">
          Decks de Anki mantidos por quem estuda para concursos
        </h1>
        <p className="max-w-[65ch] text-muted-foreground">
          Assine decks, proponha correções e receba no Anki as melhorias
          aprovadas pela comunidade.
        </p>
      </div>
      <div className="flex flex-col gap-3 sm:flex-row">
        <Button nativeButton={false} render={<Link href="/decks" />}>
          Explorar catálogo <ArrowRight aria-hidden />
        </Button>
        <Button
          variant="outline"
          nativeButton={false}
          render={<Link href="/register" />}
        >
          Criar conta
        </Button>
      </div>
    </main>
  );
}

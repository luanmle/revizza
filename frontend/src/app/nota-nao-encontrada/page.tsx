import Link from "next/link";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

/** Destino amigável do redirect /go/note/<guid>/ quando o GUID não resolve (US1 AS#3). */
export default function NotaNaoEncontradaPage() {
  return (
    <main className="mx-auto max-w-3xl p-4 md:p-6">
      <Alert>
        <AlertTitle>Nota não encontrada no Revizza</AlertTitle>
        <AlertDescription>
          Esta nota não está publicada no Revizza ou foi removida.{" "}
          <Link href="/decks" className="text-primary underline">
            Ver catálogo de decks
          </Link>
        </AlertDescription>
      </Alert>
    </main>
  );
}

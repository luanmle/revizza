"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api, ApiError } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

function decisionError(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 409) return "Esta sugestão já foi decidida por outro moderador.";
    if (error.status === 403) return "Apenas moderadores ativos do deck podem decidir.";
    const body = error.body as { detail?: string } | null;
    if (body?.detail) return body.detail;
  }
  return "Não foi possível registrar a decisão.";
}

/** Botões aceitar/rejeitar — renderizar somente para moderadores (FR-025 a FR-027). */
export default function SuggestionModerationControls({
  suggestionId,
  onDecided,
}: {
  suggestionId: string;
  onDecided: () => void;
}) {
  const [rejectOpen, setRejectOpen] = useState(false);
  const [reason, setReason] = useState("");

  const accept = useMutation({
    mutationFn: () => api.post(`/suggestions/${suggestionId}/accept/`),
    onSuccess: onDecided,
  });
  const reject = useMutation({
    mutationFn: () =>
      api.post(`/suggestions/${suggestionId}/reject/`, { rejection_reason: reason }),
    onSuccess: () => {
      setRejectOpen(false);
      onDecided();
    },
  });

  const busy = accept.isPending || reject.isPending;
  const error = accept.error ?? reject.error;

  return (
    <div className="flex flex-col gap-2">
      <div className="flex gap-2">
        <Button size="sm" onClick={() => accept.mutate()} disabled={busy}>
          {accept.isPending ? "Aceitando…" : "Aceitar"}
        </Button>
        <Button
          size="sm"
          variant="destructive"
          onClick={() => setRejectOpen(true)}
          disabled={busy}
        >
          Rejeitar
        </Button>
      </div>

      {error && !rejectOpen && (
        <p role="alert" className="text-sm text-destructive">
          {decisionError(error)}
        </p>
      )}

      <Dialog open={rejectOpen} onOpenChange={setRejectOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Rejeitar sugestão</DialogTitle>
            <DialogDescription>
              O motivo é opcional e fica visível ao autor. A decisão não pode ser
              revertida pela interface.
            </DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <Label htmlFor={`reject-reason-${suggestionId}`}>Motivo (opcional)</Label>
            <Textarea
              id={`reject-reason-${suggestionId}`}
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Explique ao autor por que a sugestão foi rejeitada"
            />
          </div>
          {reject.isError && (
            <p role="alert" className="text-sm text-destructive">
              {decisionError(reject.error)}
            </p>
          )}
          <DialogFooter>
            <Button variant="outline" onClick={() => setRejectOpen(false)}>
              Cancelar
            </Button>
            <Button
              variant="destructive"
              onClick={() => reject.mutate()}
              disabled={reject.isPending}
            >
              {reject.isPending ? "Rejeitando…" : "Confirmar rejeição"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}

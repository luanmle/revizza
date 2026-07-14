"use client";

import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Flag } from "lucide-react";
import { api } from "@/lib/api-client";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import { Textarea } from "@/components/ui/textarea";

export default function ReportButton({
  commentId,
  suggestionThread = false,
}: {
  commentId: string;
  suggestionThread?: boolean;
}) {
  const [open, setOpen] = useState(false);
  const [reason, setReason] = useState("");
  const report = useMutation({
    mutationFn: () =>
      api.post(
        `/${suggestionThread ? "suggestion-comments" : "comments"}/${commentId}/reports/`,
        { reason: reason.trim() || null },
      ),
  });

  if (report.isSuccess) {
    return (
      <p role="status" className="mt-2 text-sm text-muted-foreground">
        Denúncia enviada para revisão.
      </p>
    );
  }

  if (!open) {
    return (
      <Button
        type="button"
        size="sm"
        variant="ghost"
        className="mt-2 min-h-11"
        onClick={() => setOpen(true)}
      >
        <Flag aria-hidden /> Denunciar
      </Button>
    );
  }

  return (
    <form
      className="mt-3 flex flex-col gap-2 rounded-lg bg-muted p-3"
      onSubmit={(event) => {
        event.preventDefault();
        report.mutate();
      }}
    >
      <Label htmlFor={`report-reason-${commentId}`}>Motivo (opcional)</Label>
      <Textarea
        id={`report-reason-${commentId}`}
        value={reason}
        onChange={(event) => setReason(event.target.value)}
        placeholder="Explique o problema para ajudar a revisão"
        disabled={report.isPending}
      />
      {report.isError && (
        <p role="alert" className="text-sm text-destructive">
          Não foi possível enviar a denúncia. Tente novamente.
        </p>
      )}
      <div className="flex flex-wrap gap-2">
        <Button
          type="submit"
          size="sm"
          className="min-h-11"
          disabled={report.isPending}
        >
          {report.isPending ? "Enviando…" : "Enviar denúncia"}
        </Button>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="min-h-11"
          onClick={() => setOpen(false)}
        >
          Cancelar
        </Button>
      </div>
    </form>
  );
}

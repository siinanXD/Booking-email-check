import { useEffect, useRef, useState, type ReactNode } from "react";
import { Button } from "@/shared/ui/Button";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  message?: ReactNode;
  confirmLabel?: string;
  cancelLabel?: string;
  tone?: "danger" | "primary";
  loading?: boolean;
  /** When set, the confirm button stays disabled until the user types this phrase. */
  requirePhrase?: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export function ConfirmDialog({
  open,
  title,
  message,
  confirmLabel = "Bestätigen",
  cancelLabel = "Abbrechen",
  tone = "primary",
  loading = false,
  requirePhrase,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const [phrase, setPhrase] = useState("");
  const cancelRef = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (open) {
      setPhrase("");
      cancelRef.current?.focus();
    }
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape" && !loading) onCancel();
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [open, loading, onCancel]);

  if (!open) return null;

  const phraseOk = !requirePhrase || phrase.trim() === requirePhrase;

  return (
    <div
      className="fixed inset-0 z-[90] flex items-center justify-center bg-slate-950/50 px-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
      onClick={() => !loading && onCancel()}
    >
      <div
        className="w-full max-w-md animate-pop-in rounded-2xl border border-border bg-surface p-6 shadow-card-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <h2 id="confirm-dialog-title" className="text-lg font-extrabold text-ink">
          {title}
        </h2>
        {message && (
          <div className="mt-2 text-sm text-muted">{message}</div>
        )}
        {requirePhrase && (
          <div className="mt-4 space-y-1">
            <label
              htmlFor="confirm-phrase"
              className="block text-xs font-medium text-faint"
            >
              Tippe zur Bestätigung{" "}
              <span className="font-numeric text-ink2">{requirePhrase}</span>
            </label>
            <input
              id="confirm-phrase"
              value={phrase}
              onChange={(e) => setPhrase(e.target.value)}
              autoComplete="off"
              className="w-full rounded-xl border border-border2 bg-surface2 px-3 py-2 text-sm text-ink focus:border-brand focus:outline-none focus:ring-2 focus:ring-brand/20"
            />
          </div>
        )}
        <div className="mt-6 flex justify-end gap-2">
          <Button
            ref={cancelRef}
            variant="secondary"
            onClick={onCancel}
            disabled={loading}
          >
            {cancelLabel}
          </Button>
          <Button
            variant={tone === "danger" ? "danger" : "primary"}
            onClick={onConfirm}
            loading={loading}
            disabled={!phraseOk}
          >
            {confirmLabel}
          </Button>
        </div>
      </div>
    </div>
  );
}

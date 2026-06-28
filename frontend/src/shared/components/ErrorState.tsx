import { AlertTriangle } from "lucide-react";
import { Button } from "@/shared/ui/Button";

interface ErrorStateProps {
  message?: string;
  onRetry?: () => void;
  className?: string;
}

/** Inline error block for failed queries — distinguishes failure from "empty". */
export function ErrorState({
  message = "Daten konnten nicht geladen werden.",
  onRetry,
  className = "",
}: ErrorStateProps) {
  return (
    <div
      role="alert"
      className={`flex flex-col items-center gap-3 rounded-2xl border border-dangertext/30 bg-dangerbg px-6 py-10 text-center ${className}`}
    >
      <AlertTriangle className="h-6 w-6 text-dangertext" aria-hidden />
      <p className="text-sm font-medium text-dangertext">{message}</p>
      {onRetry && (
        <Button variant="secondary" size="sm" onClick={onRetry}>
          Erneut versuchen
        </Button>
      )}
    </div>
  );
}

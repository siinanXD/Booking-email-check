import type { ReactNode } from "react";
import { Link } from "react-router-dom";
import { Inbox } from "lucide-react";
import { Button } from "@/shared/ui/Button";

type Action = {
  label: string;
  onClick?: () => void;
  to?: string;
};

interface EmptyStateProps {
  title: string;
  message?: string;
  icon?: ReactNode;
  action?: Action;
  /** Drop the bordered/white card chrome when already inside a container. */
  bare?: boolean;
  className?: string;
}

/**
 * Neutral "nothing here yet" block — distinct from ErrorState (a failure).
 * Optionally renders a single call-to-action (button or router link).
 */
export function EmptyState({
  title,
  message,
  icon,
  action,
  bare = false,
  className = "",
}: EmptyStateProps) {
  const chrome = bare
    ? "px-6 py-12"
    : "rounded-2xl border border-border bg-surface px-6 py-12";
  return (
    <div
      className={`flex flex-col items-center gap-3 text-center ${chrome} ${className}`}
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-brandsoft text-brandink">
        {icon ?? <Inbox size={22} aria-hidden />}
      </div>
      <div className="space-y-1">
        <p className="text-sm font-extrabold text-ink">{title}</p>
        {message && (
          <p className="mx-auto max-w-md text-sm text-muted">{message}</p>
        )}
      </div>
      {action &&
        (action.to ? (
          <Link
            to={action.to}
            className="inline-flex items-center justify-center gap-1.5 rounded-xl border border-border2 bg-surface px-3 py-1.5 text-xs font-semibold text-ink2 no-underline transition-colors hover:bg-app focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand"
          >
            {action.label}
          </Link>
        ) : (
          <Button variant="secondary" size="sm" onClick={action.onClick}>
            {action.label}
          </Button>
        ))}
    </div>
  );
}

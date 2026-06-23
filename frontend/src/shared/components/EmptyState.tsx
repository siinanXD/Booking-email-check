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
    : "rounded-xl border border-slate-200/80 bg-white px-6 py-12";
  return (
    <div
      className={`flex flex-col items-center gap-3 text-center ${chrome} ${className}`}
    >
      <div className="flex h-11 w-11 items-center justify-center rounded-full bg-slate-100 text-slate-400">
        {icon ?? <Inbox size={20} aria-hidden />}
      </div>
      <div className="space-y-1">
        <p className="text-sm font-semibold text-slate-700">{title}</p>
        {message && (
          <p className="mx-auto max-w-md text-sm text-slate-500">{message}</p>
        )}
      </div>
      {action &&
        (action.to ? (
          <Link
            to={action.to}
            className="inline-flex items-center justify-center gap-1.5 rounded-md border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-700 no-underline shadow-sm transition-all duration-150 hover:border-slate-300 hover:bg-slate-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-1"
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

import { useEffect } from "react";
import type { ReviewQueueItem } from "@/lib/types/api";

interface Handlers {
  /** Move highlight by delta (J = +1, K = -1). */
  onMove: (delta: number) => void;
  onApprove: () => void;
  onEdit: () => void;
  onReject: () => void;
}

function isTypingTarget(target: EventTarget | null): boolean {
  const el = target as HTMLElement | null;
  if (!el) return false;
  const tag = el.tagName;
  return (
    tag === "INPUT" ||
    tag === "TEXTAREA" ||
    tag === "SELECT" ||
    el.isContentEditable
  );
}

/**
 * Keyboard shortcuts for the review queue:
 * J/K move the highlight, Enter approves, E edits, R rejects.
 * Ignores events while an input/textarea/select is focused.
 */
export function useReviewShortcuts(
  items: ReviewQueueItem[] | undefined,
  handlers: Handlers
) {
  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => {
      if (isTypingTarget(e.target)) return;
      if (e.metaKey || e.ctrlKey || e.altKey) return;
      if (!items || items.length === 0) return;

      switch (e.key.toLowerCase()) {
        case "j":
          e.preventDefault();
          handlers.onMove(1);
          break;
        case "k":
          e.preventDefault();
          handlers.onMove(-1);
          break;
        case "enter":
          e.preventDefault();
          handlers.onApprove();
          break;
        case "e":
          e.preventDefault();
          handlers.onEdit();
          break;
        case "r":
          e.preventDefault();
          handlers.onReject();
          break;
        default:
          break;
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [items, handlers]);
}

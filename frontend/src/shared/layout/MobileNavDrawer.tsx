import { useEffect, useId, useRef } from "react";
import { X } from "lucide-react";
import { SidebarBrand, SidebarNav } from "@/shared/layout/sidebarNav";

type Props = {
  open: boolean;
  onClose: () => void;
};

export function MobileNavDrawer({ open, onClose }: Props) {
  const titleId = useId();
  const closeButtonRef = useRef<HTMLButtonElement>(null);
  const panelRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        onClose();
        return;
      }
      if (event.key !== "Tab" || !panelRef.current) return;
      const focusable = panelRef.current.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])'
      );
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
      previouslyFocused?.focus?.();
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 lg:hidden" role="presentation">
      <button
        type="button"
        className="absolute inset-0 bg-slate-950/60 backdrop-blur-[1px]"
        aria-label="Menü schließen"
        onClick={onClose}
      />
      <aside
        ref={panelRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="relative flex h-full w-[min(100%,20rem)] max-w-[85vw] flex-col bg-rail-gradient text-railtext shadow-xl transition-transform duration-200 ease-out"
      >
        <p id={titleId} className="sr-only">
          Navigation
        </p>
        <div className="flex items-center justify-between border-b border-white/[0.07]">
          <div className="min-w-0 flex-1">
            <SidebarBrand />
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            className="mr-2 inline-flex min-h-11 min-w-11 shrink-0 items-center justify-center rounded-lg text-railtext hover:bg-white/[0.06]"
            aria-label="Menü schließen"
            onClick={onClose}
          >
            <X size={22} aria-hidden="true" />
          </button>
        </div>
        <SidebarNav onNavigate={onClose} />
      </aside>
    </div>
  );
}

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

  useEffect(() => {
    if (!open) return;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeButtonRef.current?.focus();
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") onClose();
    };
    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.body.style.overflow = previousOverflow;
      document.removeEventListener("keydown", onKeyDown);
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div className="fixed inset-0 z-50 lg:hidden" role="presentation">
      <button
        type="button"
        className="absolute inset-0 bg-slate-900/60 backdrop-blur-[1px]"
        aria-label="Menü schließen"
        onClick={onClose}
      />
      <aside
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        className="relative flex h-full w-[min(100%,20rem)] max-w-[85vw] flex-col bg-slate-900 text-slate-200 shadow-xl transition-transform duration-200 ease-out"
      >
        <p id={titleId} className="sr-only">
          Navigation
        </p>
        <div className="flex items-center justify-between border-b border-slate-700">
          <div className="min-w-0 flex-1">
            <SidebarBrand />
          </div>
          <button
            ref={closeButtonRef}
            type="button"
            className="mr-2 inline-flex min-h-11 min-w-11 shrink-0 items-center justify-center rounded-lg text-slate-300 hover:bg-slate-800 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-400"
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

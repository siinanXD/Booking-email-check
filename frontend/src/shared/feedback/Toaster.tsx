import { CheckCircle2, Info, X, XCircle } from "lucide-react";
import { useToastStore, type ToastTone } from "@/shared/feedback/toastStore";

const tones: Record<ToastTone, { box: string; icon: typeof Info }> = {
  success: {
    box: "border-oktext/25 bg-okbg text-oktext",
    icon: CheckCircle2,
  },
  error: { box: "border-dangertext/25 bg-dangerbg text-dangertext", icon: XCircle },
  info: { box: "border-border bg-surface text-ink2", icon: Info },
};

export function Toaster() {
  const toasts = useToastStore((s) => s.toasts);
  const dismiss = useToastStore((s) => s.dismiss);

  if (toasts.length === 0) return null;

  return (
    <div
      className="pointer-events-none fixed right-4 top-4 z-[100] flex w-full max-w-sm flex-col gap-2"
      role="region"
      aria-label="Benachrichtigungen"
    >
      {toasts.map((t) => {
        const { box, icon: Icon } = tones[t.tone];
        return (
          <div
            key={t.id}
            role={t.tone === "error" ? "alert" : "status"}
            aria-live={t.tone === "error" ? "assertive" : "polite"}
            className={`pointer-events-auto flex animate-pop-in items-start gap-2.5 rounded-xl border px-3.5 py-2.5 text-sm shadow-card-lg ${box}`}
          >
            <Icon className="mt-0.5 h-4 w-4 flex-shrink-0" aria-hidden />
            <span className="flex-1 break-words">{t.message}</span>
            <button
              type="button"
              onClick={() => dismiss(t.id)}
              className="flex-shrink-0 rounded p-0.5 opacity-60 transition-opacity hover:opacity-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-current"
              aria-label="Benachrichtigung schließen"
            >
              <X className="h-3.5 w-3.5" aria-hidden />
            </button>
          </div>
        );
      })}
    </div>
  );
}

import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Bell, Mail, CalendarDays, ClipboardCheck, AlertTriangle } from "lucide-react";
import {
  fetchNotifications,
  markNotificationsRead,
  type NotificationItem,
  type NotificationKind,
} from "@/lib/api/notifications";

const ICONS: Record<NotificationKind, { icon: typeof Bell; tone: string }> = {
  new_booking: { icon: CalendarDays, tone: "bg-okbg text-oktext" },
  whatsapp_sent: { icon: Mail, tone: "bg-okbg text-whatsapp" },
  review_waiting: { icon: ClipboardCheck, tone: "bg-warnbg text-warntext" },
  escalation: { icon: AlertTriangle, tone: "bg-dangerbg text-dangertext" },
};

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const min = Math.round(diff / 60000);
  if (min < 1) return "gerade eben";
  if (min < 60) return `vor ${min} Min`;
  const hrs = Math.round(min / 60);
  if (hrs < 24) return `vor ${hrs} Std`;
  return `vor ${Math.round(hrs / 24)} Tg`;
}

export function NotificationBell() {
  const [open, setOpen] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data } = useQuery({
    queryKey: ["notifications"],
    queryFn: fetchNotifications,
    refetchInterval: 30_000,
  });
  const unread = data?.unread ?? 0;

  const markRead = useMutation({
    mutationFn: markNotificationsRead,
    meta: { skipGlobalError: true },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["notifications"] }),
  });

  function open_(item: NotificationItem) {
    setOpen(false);
    if (item.href) navigate(item.href);
  }

  return (
    <div className="relative">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        aria-label="Benachrichtigungen"
        className="relative flex h-[34px] w-[34px] items-center justify-center rounded-lg border border-border bg-app text-muted transition-colors hover:text-ink"
      >
        <Bell size={16} />
        {unread > 0 && (
          <>
            <span className="absolute -right-px -top-px h-[9px] w-[9px] animate-ping-ring rounded-full bg-red-500" />
            <span className="absolute -right-0.5 -top-0.5 h-[9px] w-[9px] rounded-full border-2 border-surface bg-red-500" />
          </>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-[70]" onClick={() => setOpen(false)} />
          <div className="absolute right-0 top-[42px] z-[80] w-80 animate-slide-in-right overflow-hidden rounded-2xl border border-border bg-surface shadow-card-lg">
            <div className="flex items-center justify-between border-b border-border px-4 py-2.5">
              <span className="text-[13px] font-extrabold text-ink">Benachrichtigungen</span>
              <button
                type="button"
                onClick={() => markRead.mutate()}
                disabled={unread === 0}
                className="text-[11.5px] font-bold text-brandink disabled:opacity-40"
              >
                Alle als gelesen
              </button>
            </div>
            <div className="max-h-[60vh] overflow-auto">
              {(data?.items ?? []).length === 0 && (
                <p className="px-4 py-8 text-center text-[12.5px] text-faint">
                  Keine Benachrichtigungen.
                </p>
              )}
              {(data?.items ?? []).map((item) => {
                const { icon: Icon, tone } = ICONS[item.kind];
                return (
                  <button
                    key={item.id}
                    type="button"
                    onClick={() => open_(item)}
                    className={`flex w-full items-start gap-3 border-b border-border px-4 py-3 text-left transition-colors hover:bg-app ${
                      item.read ? "" : "bg-brandsoft/40"
                    }`}
                  >
                    <span className={`flex h-[30px] w-[30px] flex-none items-center justify-center rounded-lg ${tone}`}>
                      <Icon size={15} />
                    </span>
                    <span className="min-w-0">
                      <span className="block text-[12.5px] text-ink">{item.title}</span>
                      <span className="mt-0.5 block text-[11px] text-faint">
                        {relativeTime(item.created_at)}
                        {item.detail ? ` · ${item.detail}` : ""}
                      </span>
                    </span>
                  </button>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

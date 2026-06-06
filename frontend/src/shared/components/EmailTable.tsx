import { EmailRow } from "@/shared/components/EmailRow";
import type { EmailListItem } from "@/lib/types/api";
import { Inbox } from "lucide-react";

export function EmailTable({
  items,
  onRowClick,
  emptyMessage = "Keine Einträge",
  selectedCorrelationId,
}: {
  items: EmailListItem[];
  onRowClick?: (item: EmailListItem) => void;
  emptyMessage?: string;
  selectedCorrelationId?: string;
}) {
  if (items.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center gap-3 rounded-xl border border-dashed border-slate-200 bg-white py-16 text-center">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-slate-100 text-slate-400">
          <Inbox size={20} />
        </div>
        <p className="text-sm text-slate-500">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-xl border border-slate-200/80 bg-white shadow-card">
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-slate-100 bg-slate-50/80">
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Datum</th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Absender</th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Buchung</th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Plattform</th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Intent</th>
              <th className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Betreff</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {items.map((item) => (
              <EmailRow
                key={item.correlation_id}
                item={item}
                isSelected={item.correlation_id === selectedCorrelationId}
                onClick={onRowClick ? () => onRowClick(item) : undefined}
              />
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

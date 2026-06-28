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
      <div className="flex flex-col items-center justify-center gap-3 rounded-2xl border border-dashed border-border bg-surface py-16 text-center">
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-surface2 text-faint">
          <Inbox size={20} />
        </div>
        <p className="text-sm text-muted">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="overflow-hidden rounded-2xl border border-border bg-surface shadow-card">
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b border-border bg-surface2/80">
              <th scope="col" className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-faint">Datum</th>
              <th scope="col" className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-faint">Absender</th>
              <th scope="col" className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-faint">Buchung</th>
              <th scope="col" className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-faint">Plattform</th>
              <th scope="col" className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-faint">Intent</th>
              <th scope="col" className="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-faint">Betreff</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
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

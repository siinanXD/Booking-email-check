import { EmailRow } from "@/shared/components/EmailRow";
import type { EmailListItem } from "@/lib/types/api";

export function EmailTable({
  items,
  onRowClick,
  selectedCorrelationId,
  emptyMessage = "Keine Einträge",
}: {
  items: EmailListItem[];
  onRowClick?: (item: EmailListItem) => void;
  selectedCorrelationId?: string | null;
  emptyMessage?: string;
}) {
  if (items.length === 0) {
    return (
      <p className="py-12 text-center text-sm text-slate-500">{emptyMessage}</p>
    );
  }

  return (
    <div className="overflow-x-auto rounded-xl border border-slate-200 bg-white">
      <table className="w-full text-left">
        <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
          <tr>
            <th className="px-4 py-3">Datum</th>
            <th className="px-4 py-3">Absender</th>
            <th className="px-4 py-3">Buchung</th>
            <th className="px-4 py-3">Plattform</th>
            <th className="px-4 py-3">Intent</th>
            <th className="px-4 py-3">Betreff</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <EmailRow
              key={item.correlation_id}
              item={item}
              selected={item.correlation_id === selectedCorrelationId}
              onClick={onRowClick ? () => onRowClick(item) : undefined}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

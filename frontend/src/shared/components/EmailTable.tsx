import { EmailListCard, EmailRow } from "@/shared/components/EmailRow";
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
    <>
      <div className="space-y-3 md:hidden" aria-label="E-Mail-Liste">
        {items.map((item) => (
          <EmailListCard
            key={item.correlation_id}
            item={item}
            selected={item.correlation_id === selectedCorrelationId}
            onClick={onRowClick ? () => onRowClick(item) : undefined}
          />
        ))}
      </div>
      <div className="hidden overflow-x-auto rounded-xl border border-slate-200 bg-white md:block">
        <table className="w-full min-w-[640px] text-left">
          <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-slate-500">
            <tr>
              <th scope="col" className="px-4 py-3">
                Datum
              </th>
              <th scope="col" className="px-4 py-3">
                Absender
              </th>
              <th scope="col" className="px-4 py-3">
                Buchung
              </th>
              <th scope="col" className="px-4 py-3">
                Plattform
              </th>
              <th scope="col" className="px-4 py-3">
                Intent
              </th>
              <th scope="col" className="px-4 py-3">
                Betreff
              </th>
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
    </>
  );
}

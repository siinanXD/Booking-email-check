import { IntentBadge } from "@/shared/components/IntentBadge";
import { Badge } from "@/shared/ui/Badge";
import type { EmailListItem } from "@/lib/types/api";

export function EmailRow({
  item,
  onClick,
  selected = false,
}: {
  item: EmailListItem;
  onClick?: () => void;
  selected?: boolean;
}) {
  const tone =
    item.review_status === "pending" || item.processing_state === "pending_review"
      ? "pending"
      : item.processing_state;

  return (
    <tr
      className={`border-b border-slate-100 ${
        onClick ? "cursor-pointer hover:bg-slate-50" : ""
      } ${selected ? "bg-indigo-50" : ""}`}
      onClick={onClick}
    >
      <td className="px-4 py-3 text-sm text-slate-600">
        {item.received_at
          ? new Date(item.received_at).toLocaleString("de-DE")
          : "—"}
      </td>
      <td className="px-4 py-3 text-sm">{item.from_address}</td>
      <td className="px-4 py-3 text-sm font-medium">{item.booking_number ?? "—"}</td>
      <td className="px-4 py-3 text-sm">{item.platform ?? "—"}</td>
      <td className="px-4 py-3">
        {item.intent ? (
          <IntentBadge intent={item.intent} />
        ) : (
          <Badge label={item.processing_state} tone={tone} />
        )}
      </td>
      <td className="max-w-xs truncate px-4 py-3 text-sm text-slate-600">
        {item.subject}
      </td>
    </tr>
  );
}

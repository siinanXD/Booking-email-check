import { IntentBadge } from "@/shared/components/IntentBadge";
import { Badge } from "@/shared/ui/Badge";
import type { EmailListItem } from "@/lib/types/api";

function toneForItem(item: EmailListItem) {
  return item.review_status === "pending" || item.processing_state === "pending_review"
    ? "pending"
    : item.processing_state;
}

export function EmailListCard({
  item,
  onClick,
  selected = false,
}: {
  item: EmailListItem;
  onClick?: () => void;
  selected?: boolean;
}) {
  const tone = toneForItem(item);
  const className = `w-full rounded-xl border border-slate-200 bg-white p-4 text-left shadow-sm transition ${
    onClick ? "cursor-pointer hover:border-indigo-200 hover:bg-slate-50" : ""
  } ${selected ? "border-indigo-300 bg-indigo-50 ring-2 ring-indigo-200" : ""}`;
  const body = (
    <>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-slate-900">{item.subject}</p>
          <p className="mt-1 truncate text-xs text-slate-500">{item.from_address}</p>
        </div>
        {item.intent ? (
          <IntentBadge intent={item.intent} />
        ) : (
          <Badge label={item.processing_state} tone={tone} />
        )}
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-xs text-slate-600">
        <div>
          <dt className="text-slate-400">Datum</dt>
          <dd>
            {item.received_at
              ? new Date(item.received_at).toLocaleString("de-DE")
              : "—"}
          </dd>
        </div>
        <div>
          <dt className="text-slate-400">Buchung</dt>
          <dd className="font-medium text-slate-800">{item.booking_number ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-slate-400">Plattform</dt>
          <dd>{item.platform ?? "—"}</dd>
        </div>
      </dl>
    </>
  );

  if (onClick) {
    return (
      <button type="button" className={className} onClick={onClick}>
        {body}
      </button>
    );
  }

  return <article className={className}>{body}</article>;
}

export function EmailRow({
  item,
  onClick,
  isSelected = false,
}: {
  item: EmailListItem;
  onClick?: () => void;
  isSelected?: boolean;
}) {
  const tone = toneForItem(item);

  return (
    <tr
      className={`transition-colors duration-100 ${
        onClick ? "cursor-pointer hover:bg-indigo-50/40" : ""
      } ${isSelected ? "bg-indigo-50" : ""}`}
      onClick={onClick}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={
        onClick
          ? (event) => {
              if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                onClick();
              }
            }
          : undefined
      }
    >
      <td className="px-4 py-3 text-xs tabular-nums text-slate-500">
        {item.received_at
          ? new Date(item.received_at).toLocaleString("de-DE")
          : "—"}
      </td>
      <td className="px-4 py-3 text-sm font-medium text-slate-700">
        {item.from_address}
      </td>
      <td className="px-4 py-3 text-sm font-semibold text-slate-900">
        {item.booking_number ?? "—"}
      </td>
      <td className="px-4 py-3 text-sm text-slate-500">{item.platform ?? "—"}</td>
      <td className="px-4 py-3">
        {item.intent ? (
          <IntentBadge intent={item.intent} />
        ) : (
          <Badge label={item.processing_state} tone={tone} dot />
        )}
      </td>
      <td className="max-w-xs truncate px-4 py-3 text-sm text-slate-600">
        {item.subject}
      </td>
    </tr>
  );
}

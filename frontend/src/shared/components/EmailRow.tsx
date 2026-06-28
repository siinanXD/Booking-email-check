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
  const className = `w-full rounded-xl border border-border bg-surface p-4 text-left shadow-card transition ${
    onClick ? "cursor-pointer hover:border-brand/30 hover:bg-surface2" : ""
  } ${selected ? "border-brand/30 bg-brandsoft ring-2 ring-brand/20" : ""}`;
  const body = (
    <>
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-medium text-ink">{item.subject}</p>
          <p className="mt-1 truncate text-xs text-muted">{item.from_address}</p>
        </div>
        {item.intent ? (
          <IntentBadge intent={item.intent} />
        ) : (
          <Badge label={item.processing_state} tone={tone} />
        )}
      </div>
      <dl className="mt-3 grid grid-cols-2 gap-x-3 gap-y-2 text-xs text-ink2">
        <div>
          <dt className="text-faint">Datum</dt>
          <dd className="font-numeric">
            {item.received_at
              ? new Date(item.received_at).toLocaleString("de-DE")
              : "—"}
          </dd>
        </div>
        <div>
          <dt className="text-faint">Buchung</dt>
          <dd className="font-medium text-ink2 font-numeric">{item.booking_number ?? "—"}</dd>
        </div>
        <div>
          <dt className="text-faint">Plattform</dt>
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
      className={`transition-colors duration-100 focus-visible:outline focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand ${
        onClick ? "cursor-pointer hover:bg-brandsoft/40" : ""
      } ${isSelected ? "bg-brandsoft" : ""}`}
      onClick={onClick}
      role={onClick ? "button" : undefined}
      aria-selected={onClick ? isSelected : undefined}
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
      <td className="px-4 py-3 text-xs tabular-nums font-numeric text-muted">
        {item.received_at
          ? new Date(item.received_at).toLocaleString("de-DE")
          : "—"}
      </td>
      <td className="px-4 py-3 text-sm font-medium text-ink2">
        {item.from_address}
      </td>
      <td className="px-4 py-3 text-sm font-semibold text-ink font-numeric">
        {item.booking_number ?? "—"}
      </td>
      <td className="px-4 py-3 text-sm text-muted">{item.platform ?? "—"}</td>
      <td className="px-4 py-3">
        {item.intent ? (
          <IntentBadge intent={item.intent} />
        ) : (
          <Badge label={item.processing_state} tone={tone} dot />
        )}
      </td>
      <td className="max-w-xs truncate px-4 py-3 text-sm text-ink2">
        {item.subject}
      </td>
    </tr>
  );
}

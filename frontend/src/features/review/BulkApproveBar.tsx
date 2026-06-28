import { CheckCheck } from "lucide-react";
import { Button } from "@/shared/ui/Button";

interface BulkApproveBarProps {
  count: number;
  pending: boolean;
  onApprove: () => void;
  onClear: () => void;
}

/** Sticky-ish action bar shown when one or more rows are checked for bulk approval. */
export function BulkApproveBar({
  count,
  pending,
  onApprove,
  onClear,
}: BulkApproveBarProps) {
  if (count === 0) return null;
  return (
    <div className="flex flex-wrap items-center gap-3 rounded-xl border border-border bg-brandsoft px-4 py-2.5">
      <span className="text-sm font-medium text-brandink font-numeric">
        {count} ausgewählt
      </span>
      <div className="ml-auto flex items-center gap-2">
        <Button variant="ghost" size="sm" onClick={onClear} disabled={pending}>
          Auswahl aufheben
        </Button>
        <Button size="sm" onClick={onApprove} loading={pending}>
          <CheckCheck size={14} />
          Alle freigeben
        </Button>
      </div>
    </div>
  );
}

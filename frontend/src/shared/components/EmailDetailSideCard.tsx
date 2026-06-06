import { useQuery } from "@tanstack/react-query";
import { fetchEmailDetail } from "@/lib/api/emails";
import { EmailDetailPanel } from "@/shared/components/EmailDetailPanel";
import { Card } from "@/shared/ui/Card";
import type { EmailListItem } from "@/lib/types/api";

export function EmailDetailSideCard({
  selected,
}: {
  selected: EmailListItem | null;
}) {
  const correlationId = selected?.correlation_id ?? null;

  const { data: detail, isLoading } = useQuery({
    queryKey: ["email-detail", correlationId],
    queryFn: () => fetchEmailDetail(correlationId!),
    enabled: Boolean(correlationId),
  });

  return (
    <Card className="lg:sticky lg:top-4 lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto">
      {!selected ? (
        <p className="text-sm text-slate-500">
          Zeile in der Liste anklicken, um die volle E-Mail zu lesen.
        </p>
      ) : (
        <EmailDetailPanel
          detail={detail}
          isLoading={isLoading}
          showFullBody
        />
      )}
    </Card>
  );
}

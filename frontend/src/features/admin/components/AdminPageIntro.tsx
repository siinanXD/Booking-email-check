import { Card } from "@/shared/ui/Card";

export function AdminPageIntro({
  title,
  description,
  impact,
}: {
  title: string;
  description: string;
  impact?: string;
}) {
  return (
    <Card className="border-border bg-brandsoft">
      <h2 className="text-lg font-medium text-ink">{title}</h2>
      <p className="mt-2 text-sm leading-relaxed text-muted">{description}</p>
      {impact && (
        <p className="mt-3 rounded-lg border border-border bg-surface/70 px-3 py-2 text-sm text-ink2">
          <span className="font-medium text-brandink">Was sich ändert: </span>
          {impact}
        </p>
      )}
    </Card>
  );
}

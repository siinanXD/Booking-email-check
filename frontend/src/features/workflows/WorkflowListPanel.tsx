import type { TenantWorkflowSummary } from "@/lib/types/api";
import { Badge } from "@/shared/ui/Badge";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";

export interface WorkflowListPanelProps {
  pageSubtitle: string;
  isLoading: boolean;
  items: TenantWorkflowSummary[];
  onCreate: () => void;
  onEdit: (id: string) => void;
}

export function WorkflowListPanel({
  pageSubtitle,
  isLoading,
  items,
  onCreate,
  onEdit,
}: WorkflowListPanelProps) {
  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Workflows</h1>
          <p className="mt-1 text-sm text-slate-600">{pageSubtitle}</p>
        </div>
        <Button onClick={onCreate}>Neuer Workflow</Button>
      </div>

      {isLoading && <p className="text-sm text-slate-500">Lade…</p>}

      <div className="grid gap-4 md:grid-cols-2">
        {items.map((wf) => (
          <Card key={wf.id} className="space-y-3">
            <div className="flex items-start justify-between gap-2">
              <div>
                <h2 className="font-medium text-slate-900">{wf.label}</h2>
                <p className="text-xs text-slate-500">{wf.slug}</p>
              </div>
              <div className="flex flex-wrap gap-1">
                {wf.sandbox_only && <Badge label="Sandbox" tone="pending" />}
                {wf.tests_passed && <Badge label="Tests OK" tone="approved" />}
                {wf.enabled && <Badge label="Live" tone="approved" />}
                {wf.supports_multimodal && (
                  <Badge label="Multimodal" tone="default" />
                )}
              </div>
            </div>
            <p className="text-sm text-slate-600 line-clamp-2">{wf.description}</p>
            <p className="text-xs text-slate-500">
              {wf.test_email_count} Test-Mail(s) · Wichtigkeit: {wf.importance}
            </p>
            <Button variant="secondary" onClick={() => void onEdit(wf.id)}>
              Bearbeiten
            </Button>
          </Card>
        ))}
      </div>

      {!isLoading && items.length === 0 && (
        <Card className="text-sm text-slate-600">
          Noch keine Workflows. Lege einen an — der KI-Assistent schlägt Felder
          und Prompts vor.
        </Card>
      )}
    </div>
  );
}

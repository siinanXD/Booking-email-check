import { useQuery } from "@tanstack/react-query";
import { fetchWhatsAppPreview } from "@/lib/api/review";
import { EMPLOYEE_WHATSAPP_LOCALE_META } from "@/lib/whatsappLocales";
import { Card } from "@/shared/ui/Card";

type Props = {
  correlationId: string | null;
};

function roleLabel(role: string): string {
  return role === "employee" ? "Mitarbeiter" : "Host";
}

export function ReviewWhatsAppCard({ correlationId }: Props) {
  const { data, isLoading } = useQuery({
    queryKey: ["whatsapp-preview", correlationId],
    queryFn: () => fetchWhatsAppPreview(correlationId!),
    enabled: Boolean(correlationId),
  });

  if (!correlationId) return null;

  return (
    <Card className="space-y-3">
      <h4 className="text-sm font-medium text-ink">WhatsApp-Vorschau</h4>
      {isLoading && <p className="text-xs text-muted">Lade…</p>}
      {data?.note && <p className="text-xs text-warntext">{data.note}</p>}
      {(data?.messages ?? []).map((msg) => {
        const localeMeta =
          EMPLOYEE_WHATSAPP_LOCALE_META[
            msg.template_language as keyof typeof EMPLOYEE_WHATSAPP_LOCALE_META
          ];
        const showGermanTranslation =
          msg.template_language !== "de" &&
          msg.generated_body_de.trim() !== msg.generated_body.trim();

        return (
          <div
            key={`${msg.recipient_e164}-${msg.template_name}`}
            className="space-y-2 rounded border border-border p-3 text-xs"
          >
            <div className="flex flex-wrap items-center gap-2">
              <p className="font-medium text-ink">{msg.recipient_e164}</p>
              <span className="rounded bg-surface2 px-2 py-0.5 text-ink2">
                {roleLabel(msg.recipient_role)}
              </span>
              {localeMeta && (
                <span className="inline-flex items-center gap-1 text-muted">
                  <span aria-hidden="true">{localeMeta.flag}</span>
                  <span>{localeMeta.englishName}</span>
                </span>
              )}
            </div>

            <div>
              <p className="mb-1 font-medium uppercase tracking-wide text-muted">
                Versandtext
              </p>
              <pre className="whitespace-pre-wrap rounded bg-surface2 p-2 text-sm text-ink">
                {msg.generated_body || "—"}
              </pre>
            </div>

            {showGermanTranslation && (
              <div>
                <p className="mb-1 font-medium uppercase tracking-wide text-muted">
                  Deutsch (Review)
                </p>
                <pre className="whitespace-pre-wrap rounded bg-brandsoft p-2 text-sm text-ink">
                  {msg.generated_body_de}
                </pre>
              </div>
            )}

            <details className="text-muted">
              <summary className="cursor-pointer text-[11px]">Technische Details</summary>
              <p className="mt-1">{msg.template_name}</p>
              <ul className="mt-1 list-inside list-disc">
                {msg.template_params.map((param, index) => (
                  <li key={index}>{param}</li>
                ))}
              </ul>
            </details>
          </div>
        );
      })}
    </Card>
  );
}

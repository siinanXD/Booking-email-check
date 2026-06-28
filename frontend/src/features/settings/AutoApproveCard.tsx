import { useEffect, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { Save, Zap } from "lucide-react";
import { saveSettings } from "@/lib/api/settings";
import type { AutoApprove, AutoApprovePerIntent } from "@/lib/types/api";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { Input } from "@/shared/ui/Input";
import { Toggle } from "@/shared/ui/Toggle";
import { toast } from "@/shared/feedback/toastStore";

const DEFAULT_THRESHOLD = 97;

const INTENTS: { key: keyof AutoApprovePerIntent; label: string }[] = [
  { key: "booking", label: "Buchung" },
  { key: "cancellation", label: "Storno" },
  { key: "inquiry", label: "Gastnachricht" },
  { key: "change", label: "Änderung" },
];

const EMPTY_PER_INTENT: AutoApprovePerIntent = {
  booking: false,
  cancellation: false,
  inquiry: false,
  change: false,
};

export interface AutoApproveCardProps {
  value: AutoApprove | undefined;
}

export function AutoApproveCard({ value }: AutoApproveCardProps) {
  const queryClient = useQueryClient();
  const [enabled, setEnabled] = useState(false);
  const [threshold, setThreshold] = useState(DEFAULT_THRESHOLD);
  const [perIntent, setPerIntent] =
    useState<AutoApprovePerIntent>(EMPTY_PER_INTENT);

  useEffect(() => {
    if (!value) return;
    setEnabled(value.enabled);
    setThreshold(value.threshold ?? DEFAULT_THRESHOLD);
    setPerIntent({ ...EMPTY_PER_INTENT, ...value.per_intent });
  }, [value]);

  const saveMut = useMutation({
    mutationFn: () =>
      saveSettings({
        auto_approve: { enabled, threshold, per_intent: perIntent },
      }),
    onSuccess: () => {
      toast.success("Auto-Freigabe gespeichert.");
      void queryClient.invalidateQueries({ queryKey: ["settings"] });
    },
  });

  const clampThreshold = (raw: number) =>
    Math.min(100, Math.max(90, Math.round(raw)));

  const setIntent = (key: keyof AutoApprovePerIntent, on: boolean) =>
    setPerIntent((prev) => ({ ...prev, [key]: on }));

  return (
    <Card className="space-y-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-brandsoft text-brandink">
            <Zap size={18} />
          </div>
          <div>
            <h3 className="text-sm font-semibold text-ink">Auto-Freigabe</h3>
            <p className="text-xs text-muted">
              Entwürfe ab einer hohen Konfidenz automatisch freigeben.
            </p>
          </div>
        </div>
        <Toggle checked={enabled} onChange={setEnabled} label="Auto-Freigabe aktiv" />
      </div>

      <div className="space-y-2">
        <label
          htmlFor="auto-approve-threshold"
          className="block text-xs font-medium text-ink2"
        >
          Mindest-Konfidenz (90–100)
        </label>
        <div className="flex items-center gap-3">
          <input
            id="auto-approve-threshold"
            type="range"
            min={90}
            max={100}
            step={1}
            value={threshold}
            disabled={!enabled}
            onChange={(e) => setThreshold(clampThreshold(Number(e.target.value)))}
            className="h-2 flex-1 cursor-pointer appearance-none rounded-full bg-surface2 accent-brand disabled:opacity-50"
          />
          <Input
            type="number"
            min={90}
            max={100}
            value={threshold}
            disabled={!enabled}
            onChange={(e) => setThreshold(clampThreshold(Number(e.target.value)))}
            onBlur={() => setThreshold((t) => clampThreshold(t))}
            className="w-20 font-numeric"
          />
        </div>
      </div>

      <div className="space-y-2">
        <p className="text-xs font-medium text-ink2">Pro Kategorie freigeben</p>
        <div className="space-y-2.5 rounded-xl border border-border bg-surface2/40 p-3">
          {INTENTS.map((it) => (
            <Toggle
              key={it.key}
              label={it.label}
              checked={perIntent[it.key]}
              disabled={!enabled}
              onChange={(on) => setIntent(it.key, on)}
            />
          ))}
        </div>
      </div>

      <div className="flex justify-end">
        <Button onClick={() => saveMut.mutate()} loading={saveMut.isPending}>
          <Save size={15} />
          Auto-Freigabe speichern
        </Button>
      </div>
    </Card>
  );
}

import { AdminPageIntro } from "@/features/admin/components/AdminPageIntro";
import { StatusAmpel } from "@/features/admin/components/pipeline/StatusAmpel";
import { PipelineFunnel } from "@/features/admin/components/pipeline/PipelineFunnel";
import { DecisionPanel } from "@/features/admin/components/pipeline/DecisionPanel";
import { StuckList } from "@/features/admin/components/pipeline/StuckList";

export function AdminPipelinePage() {
  return (
    <div className="space-y-6">
      <AdminPageIntro
        title="Datenfluss"
        description="Ein Bild vom gesamten Verarbeitungsweg: Live-Systemstatus, der Trichter von eingegangener bis freigegebener Mail, die Entscheidungen der Pipeline und alles, was hängengeblieben ist — mandantenübergreifend."
        impact="Reine Beobachtung. Der Systemstatus aktualisiert sich automatisch alle 15 Sekunden; klicke eine hängengebliebene Mail an, um ihren vollständigen Verlauf zu sehen."
      />

      <StatusAmpel />
      <PipelineFunnel />
      <DecisionPanel />
      <StuckList />
    </div>
  );
}

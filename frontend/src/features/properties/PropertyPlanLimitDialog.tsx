import { useNavigate } from "react-router-dom";
import { BILLING_SETTINGS_PATH } from "@/lib/billing/display";
import { ConfirmDialog } from "@/shared/ui/ConfirmDialog";

export function PropertyPlanLimitDialog({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const navigate = useNavigate();
  return (
    <ConfirmDialog
      open={open}
      title="Unterkunfts-Limit erreicht"
      message="Dein aktueller Plan erlaubt keine weiteren Unterkünfte. Bitte upgrade deinen Plan oder entferne eine bestehende Unterkunft."
      confirmLabel="Zu Einstellungen"
      cancelLabel="Schließen"
      onConfirm={() => {
        onClose();
        navigate(BILLING_SETTINGS_PATH);
      }}
      onCancel={onClose}
    />
  );
}

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { Trash2 } from "lucide-react";
import {
  createPartner,
  deletePartner,
  fetchPartners,
  updatePartner,
  type CleaningPartner,
  type PartnerPayload,
} from "@/lib/api/cleaning";
import { toast } from "@/shared/feedback/toastStore";
import { Badge } from "@/shared/ui/Badge";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { ConfirmDialog } from "@/shared/ui/ConfirmDialog";
import { Input } from "@/shared/ui/Input";

interface FormState {
  name: string;
  phone: string;
  address: string;
  contact_person: string;
  property_names: string;
}

const EMPTY: FormState = {
  name: "",
  phone: "",
  address: "",
  contact_person: "",
  property_names: "",
};

function toPayload(form: FormState): PartnerPayload {
  return {
    name: form.name.trim(),
    phone: form.phone.trim() || null,
    address: form.address.trim() || null,
    contact_person: form.contact_person.trim() || null,
    property_names: form.property_names
      .split(",")
      .map((p) => p.trim())
      .filter(Boolean),
  };
}

export function PartnerManager() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<FormState>(EMPTY);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [confirmId, setConfirmId] = useState<string | null>(null);

  const { data } = useQuery({
    queryKey: ["cleaning-partners"],
    queryFn: fetchPartners,
  });

  const invalidate = () => {
    void queryClient.invalidateQueries({ queryKey: ["cleaning-partners"] });
    void queryClient.invalidateQueries({ queryKey: ["cleaning-tasks"] });
  };

  const saveMut = useMutation({
    mutationFn: () =>
      editingId
        ? updatePartner(editingId, toPayload(form))
        : createPartner(toPayload(form)),
    onSuccess: () => {
      toast.success(editingId ? "Partner aktualisiert." : "Partner angelegt.");
      setForm(EMPTY);
      setEditingId(null);
      invalidate();
    },
  });

  const deleteMut = useMutation({
    mutationFn: (id: string) => deletePartner(id),
    onSuccess: () => {
      toast.success("Partner entfernt.");
      setConfirmId(null);
      invalidate();
    },
  });

  const startEdit = (p: CleaningPartner) => {
    setEditingId(p.partner_id);
    setForm({
      name: p.name,
      phone: p.phone ?? "",
      address: p.address ?? "",
      contact_person: p.contact_person ?? "",
      property_names: p.property_names.join(", "),
    });
  };

  return (
    <div className="space-y-4">
      <Card>
        <div className="grid gap-3 sm:grid-cols-2">
          <Input
            label="Name"
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
          />
          <Input
            label="Telefon (E.164, z. B. +49170…)"
            value={form.phone}
            onChange={(e) => setForm({ ...form, phone: e.target.value })}
          />
          <Input
            label="Ansprechpartner"
            value={form.contact_person}
            onChange={(e) => setForm({ ...form, contact_person: e.target.value })}
          />
          <Input
            label="Adresse"
            value={form.address}
            onChange={(e) => setForm({ ...form, address: e.target.value })}
          />
          <Input
            label="Wohnungen (Komma-getrennt)"
            value={form.property_names}
            onChange={(e) =>
              setForm({ ...form, property_names: e.target.value })
            }
          />
        </div>
        <div className="mt-3 flex gap-2">
          <Button
            onClick={() => saveMut.mutate()}
            loading={saveMut.isPending}
            disabled={!form.name.trim()}
          >
            {editingId ? "Speichern" : "Partner anlegen"}
          </Button>
          {editingId && (
            <Button
              variant="ghost"
              onClick={() => {
                setEditingId(null);
                setForm(EMPTY);
              }}
            >
              Abbrechen
            </Button>
          )}
        </div>
      </Card>

      <div className="space-y-2">
        {(data?.items ?? []).map((p) => (
          <Card key={p.partner_id}>
            <div className="flex items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="font-semibold">{p.name}</span>
                  {!p.active && <Badge label="inaktiv" tone="rejected" />}
                </div>
                <div className="text-sm text-oktext/70">
                  {p.phone ?? "—"} ·{" "}
                  {p.property_names.length
                    ? p.property_names.join(", ")
                    : "keine Wohnung zugeordnet"}
                </div>
              </div>
              <div className="flex shrink-0 gap-2">
                <Button variant="outline" size="sm" onClick={() => startEdit(p)}>
                  Bearbeiten
                </Button>
                <Button
                  variant="danger"
                  size="sm"
                  onClick={() => setConfirmId(p.partner_id)}
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </Card>
        ))}
      </div>

      <ConfirmDialog
        open={confirmId !== null}
        title="Partner entfernen?"
        message="Der Partner wird deaktiviert. Bestehende Aufträge bleiben erhalten."
        tone="danger"
        confirmLabel="Entfernen"
        loading={deleteMut.isPending}
        onConfirm={() => confirmId && deleteMut.mutate(confirmId)}
        onCancel={() => setConfirmId(null)}
      />
    </div>
  );
}

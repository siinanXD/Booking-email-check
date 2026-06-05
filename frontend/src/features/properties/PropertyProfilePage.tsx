import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  fetchPropertyProfile,
  fetchPropertyStats,
  updatePropertyProfile,
} from "@/lib/api/properties";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";
import { Input } from "@/shared/ui/Input";

export function PropertyProfilePage() {
  const { propertyId } = useParams<{ propertyId: string }>();
  const queryClient = useQueryClient();
  const year = new Date().getFullYear();

  const { data: profile, isLoading } = useQuery({
    queryKey: ["property-profile", propertyId],
    queryFn: () => fetchPropertyProfile(propertyId!),
    enabled: Boolean(propertyId),
  });

  const { data: stats } = useQuery({
    queryKey: ["property-stats", propertyId, year],
    queryFn: () => fetchPropertyStats(propertyId!, year),
    enabled: Boolean(propertyId),
  });

  const [name, setName] = useState("");
  const [location, setLocation] = useState("");
  const [contactName, setContactName] = useState("");
  const [contactPhone, setContactPhone] = useState("");
  const [contactEmail, setContactEmail] = useState("");
  const [notes, setNotes] = useState("");
  const [whatsappPhone, setWhatsappPhone] = useState("");
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!profile) return;
    setName(profile.name);
    setLocation(profile.location ?? "");
    setContactName(profile.contact_name ?? "");
    setContactPhone(profile.contact_phone ?? "");
    setContactEmail(profile.contact_email ?? "");
    setNotes(profile.notes ?? "");
    setWhatsappPhone(profile.whatsapp_phones[0] ?? "");
  }, [profile]);

  const saveMut = useMutation({
    mutationFn: () =>
      updatePropertyProfile(propertyId!, {
        name: name.trim(),
        location: location.trim() || null,
        contact_name: contactName.trim() || null,
        contact_phone: contactPhone.trim() || null,
        contact_email: contactEmail.trim() || null,
        notes: notes.trim() || null,
        whatsapp_phones: whatsappPhone.trim() ? [whatsappPhone.trim()] : [],
      }),
    onSuccess: () => {
      setSaveMessage("Profil gespeichert.");
      void queryClient.invalidateQueries({ queryKey: ["property-profile", propertyId] });
      void queryClient.invalidateQueries({ queryKey: ["properties"] });
      void queryClient.invalidateQueries({ queryKey: ["property-recipients"] });
    },
    onError: () => setSaveMessage("Speichern fehlgeschlagen."),
  });

  if (!propertyId) {
    return <p className="text-slate-500">Unterkunft nicht gefunden.</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link to="/properties" className="text-sm text-indigo-600 hover:underline">
          ← Zurück
        </Link>
        <h2 className="text-xl font-semibold text-slate-800">Unterkunftsprofil</h2>
      </div>

      {isLoading ? (
        <p className="text-slate-500">Lade…</p>
      ) : (
        <>
          {stats && (
            <Card className="grid gap-2 sm:grid-cols-4 text-sm">
              <div>
                <p className="text-slate-500">Gebuchte Tage ({stats.year})</p>
                <p className="text-lg font-semibold">{stats.booked_days}</p>
              </div>
              <div>
                <p className="text-slate-500">Umsatz ({stats.year})</p>
                <p className="text-lg font-semibold">
                  {stats.revenue.toLocaleString("de-DE", {
                    style: "currency",
                    currency: "EUR",
                  })}
                </p>
              </div>
              <div>
                <p className="text-slate-500">Buchungen</p>
                <p className="text-lg font-semibold">{stats.booking_count}</p>
              </div>
              {stats.incomplete_data_count > 0 && (
                <div>
                  <p className="text-slate-500">Unvollständige Daten</p>
                  <p className="text-lg font-semibold text-amber-600">
                    {stats.incomplete_data_count}
                  </p>
                </div>
              )}
            </Card>
          )}

          <Card className="space-y-4">
            <Input
              placeholder="Name"
              value={name}
              onChange={(e) => setName(e.target.value)}
            />
            <Input
              placeholder="Standort / Adresse"
              value={location}
              onChange={(e) => setLocation(e.target.value)}
            />
            <Input
              placeholder="Kontaktname"
              value={contactName}
              onChange={(e) => setContactName(e.target.value)}
            />
            <Input
              placeholder="Kontakt-Telefon (E.164)"
              value={contactPhone}
              onChange={(e) => setContactPhone(e.target.value)}
            />
            <Input
              placeholder="Kontakt-E-Mail"
              value={contactEmail}
              onChange={(e) => setContactEmail(e.target.value)}
            />
            <Input
              placeholder="WhatsApp +49…"
              value={whatsappPhone}
              onChange={(e) => setWhatsappPhone(e.target.value)}
            />
            <textarea
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
              placeholder="Notizen"
              rows={4}
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
            />
            <Button onClick={() => saveMut.mutate()} disabled={saveMut.isPending}>
              Speichern
            </Button>
            {saveMessage && <p className="text-sm text-slate-600">{saveMessage}</p>}
          </Card>
        </>
      )}
    </div>
  );
}

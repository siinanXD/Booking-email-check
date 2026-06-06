import type { PropertySuggestion } from "@/lib/api/properties";
import { Button } from "@/shared/ui/Button";
import { Card } from "@/shared/ui/Card";

interface Props {
  suggestions: PropertySuggestion[];
  addedNames: Set<string>;
  adoptPending: boolean;
  adoptMessage: string | null;
  onAddToList: (name: string) => void;
  onCreateProfile: (name: string) => void;
}

export function PropertySuggestionsCard({
  suggestions,
  addedNames,
  adoptPending,
  adoptMessage,
  onAddToList,
  onCreateProfile,
}: Props) {
  return (
    <Card>
      <h3 className="mb-2 font-medium">KI-Vorschläge (neue Namen)</h3>
      {suggestions.length === 0 ? (
        <p className="text-sm text-slate-500">Keine Vorschläge.</p>
      ) : (
        <ul className="text-sm space-y-2">
          {suggestions.map((s) => (
            <li
              key={s.property_name}
              className="flex flex-wrap items-center justify-between gap-2"
            >
              <span>
                {s.property_name}{" "}
                <span className="text-slate-400">({s.mail_count} Mails)</span>
              </span>
              <div className="flex gap-2">
                <Button
                  variant="secondary"
                  className="py-1 px-3"
                  disabled={addedNames.has(s.property_name)}
                  onClick={() => onAddToList(s.property_name)}
                >
                  {addedNames.has(s.property_name) ? "Hinzugefügt" : "+ Zur Liste"}
                </Button>
                <Button
                  variant="secondary"
                  className="py-1 px-3"
                  disabled={adoptPending}
                  onClick={() => onCreateProfile(s.property_name)}
                >
                  Profil anlegen
                </Button>
              </div>
            </li>
          ))}
        </ul>
      )}
      {adoptMessage && (
        <p className="mt-2 text-sm text-slate-600">{adoptMessage}</p>
      )}
    </Card>
  );
}

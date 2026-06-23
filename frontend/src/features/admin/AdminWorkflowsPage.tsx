import { Link, useSearchParams } from "react-router-dom";
import { useAllAccounts } from "@/features/admin/useAllAccounts";
import { WorkflowsPage } from "@/features/workflows/WorkflowsPage";
import { Card } from "@/shared/ui/Card";

export function AdminWorkflowsPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const accountId = searchParams.get("account") ?? "";

  const { data: accounts, isLoading } = useAllAccounts();

  const activeAccounts = (accounts?.items ?? []).filter((a) => a.status === "active");
  const selected = activeAccounts.find((a) => a.id === accountId);

  if (!accountId) {
    return (
      <div className="space-y-6">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">Mandanten-Workflows</h2>
          <p className="mt-1 text-sm text-slate-600">
            Wähle einen Mandanten, um dessen Workflows anzulegen oder zu bearbeiten.
            Die Daten bleiben dem Mandanten zugeordnet.
          </p>
        </div>
        {isLoading && <p className="text-sm text-slate-500">Lade Mandanten…</p>}
        <div className="grid gap-3 md:grid-cols-2">
          {activeAccounts.map((account) => (
            <Card key={account.id} className="space-y-2">
              <h3 className="font-medium text-slate-900">{account.display_name}</h3>
              <p className="text-sm text-slate-500">{account.contact_email}</p>
              <button
                type="button"
                className="text-sm font-medium text-indigo-600 hover:underline"
                onClick={() => setSearchParams({ account: account.id })}
              >
                Workflows verwalten →
              </button>
            </Card>
          ))}
        </div>
        {!isLoading && activeAccounts.length === 0 && (
          <Card className="text-sm text-slate-600">
            Keine aktiven Mandanten. Freischaltung unter{" "}
            <Link to="/admin/accounts" className="text-indigo-600 hover:underline">
              Mandanten
            </Link>
            .
          </Card>
        )}
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          className="text-sm text-indigo-600 hover:underline"
          onClick={() => setSearchParams({})}
        >
          ← Mandant wählen
        </button>
        {selected && (
          <p className="text-sm text-slate-600">
            Mandant: <strong>{selected.display_name}</strong> ({selected.contact_email})
          </p>
        )}
        {selected && (
          <Link
            to={`/admin/accounts/${accountId}`}
            className="text-sm text-slate-500 hover:text-indigo-600"
          >
            Mandanten-Details
          </Link>
        )}
      </div>
      <WorkflowsPage
        adminAccountId={accountId}
        subtitle={`Workflows für ${selected?.display_name ?? accountId}`}
      />
    </div>
  );
}

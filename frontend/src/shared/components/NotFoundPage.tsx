import { Link } from "react-router-dom";
import { Button } from "@/shared/ui/Button";

export function NotFoundPage() {
  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3 text-center">
      <p className="text-5xl font-extrabold text-slate-300">404</p>
      <h1 className="text-xl font-bold text-slate-900">Seite nicht gefunden</h1>
      <p className="max-w-sm text-sm text-slate-500">
        Die aufgerufene Adresse existiert nicht oder wurde verschoben.
      </p>
      <Link to="/">
        <Button variant="primary" className="mt-2">
          Zum Dashboard
        </Button>
      </Link>
    </div>
  );
}

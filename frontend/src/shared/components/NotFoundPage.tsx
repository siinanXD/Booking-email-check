import { Link } from "react-router-dom";
import { Button } from "@/shared/ui/Button";

export function NotFoundPage() {
  return (
    <div className="flex min-h-[50vh] flex-col items-center justify-center gap-3 text-center">
      <p className="font-numeric text-5xl font-bold text-border2">404</p>
      <h1 className="text-xl font-extrabold text-ink">Seite nicht gefunden</h1>
      <p className="max-w-sm text-sm text-muted">
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

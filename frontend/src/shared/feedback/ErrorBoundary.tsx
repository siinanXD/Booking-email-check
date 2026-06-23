import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // eslint-disable-next-line no-console
    console.error("Unbehandelter UI-Fehler:", error, info.componentStack);
  }

  handleReload = () => {
    window.location.reload();
  };

  render(): ReactNode {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-slate-50 px-6 text-center">
          <h1 className="text-xl font-bold text-slate-900">
            Etwas ist schiefgelaufen.
          </h1>
          <p className="max-w-md text-sm text-slate-600">
            Die Seite konnte nicht angezeigt werden. Lade die Anwendung neu –
            falls das Problem bestehen bleibt, kontaktiere den Support.
          </p>
          <button
            type="button"
            onClick={this.handleReload}
            className="rounded-lg bg-indigo-600 px-4 py-2 text-sm font-medium text-white shadow-sm transition-colors hover:bg-indigo-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500"
          >
            Neu laden
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}

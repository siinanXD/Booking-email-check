import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Badge } from "@/shared/ui/Badge";

describe("Badge", () => {
  it("renders label text", () => {
    render(<Badge label="pending_review" tone="pending" />);
    expect(screen.getByText("pending_review")).toBeInTheDocument();
  });

  it("falls back to default tone for unknown values", () => {
    const { container } = render(<Badge label="x" tone="unknown" />);
    // Default-Tone nutzt jetzt Token-Klassen (app/muted) statt hartem Slate.
    expect(container.firstChild).toHaveClass("bg-app");
  });
});

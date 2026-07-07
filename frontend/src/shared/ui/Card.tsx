import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  id?: string;
  variant?: "default" | "flat" | "elevated";
  hover?: boolean;
}

const variants = {
  default: "border border-border bg-surface shadow-card",
  flat: "border border-border bg-surface",
  elevated: "border border-border bg-surface shadow-card-lg",
};

export function Card({
  children,
  className = "",
  id,
  variant = "default",
  hover = false,
}: CardProps) {
  return (
    <div
      id={id}
      className={`rounded-2xl p-5 ${variants[variant]} ${
        hover
          ? "cursor-pointer transition-transform duration-200 hover:-translate-y-0.5 hover:shadow-card-lg"
          : ""
      } ${className}`}
    >
      {children}
    </div>
  );
}

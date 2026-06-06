import type { ButtonHTMLAttributes } from "react";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost";
}

const variants: Record<NonNullable<ButtonProps["variant"]>, string> = {
  primary:
    "bg-indigo-600 text-white hover:bg-indigo-700 disabled:bg-indigo-300",
  secondary:
    "bg-white border border-slate-200 text-slate-700 hover:bg-slate-50",
  danger: "bg-red-600 text-white hover:bg-red-700",
  ghost: "text-slate-600 hover:bg-slate-100",
};

export function Button({
  variant = "primary",
  className = "",
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      className={`inline-flex min-h-11 items-center justify-center rounded-lg px-4 py-2.5 text-sm font-medium transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}

import { forwardRef, type ButtonHTMLAttributes } from "react";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/cn";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "danger" | "ghost" | "outline";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
}

const variants: Record<NonNullable<ButtonProps["variant"]>, string> = {
  primary:
    "bg-brand-gradient text-white shadow-glow hover:opacity-95 active:opacity-90 disabled:opacity-50 disabled:shadow-none focus-visible:ring-brand",
  secondary:
    "bg-surface border border-border2 text-ink2 hover:bg-app active:bg-app disabled:opacity-50 focus-visible:ring-brand",
  danger:
    "bg-red-600 text-white shadow-sm hover:bg-red-500 active:bg-red-700 disabled:opacity-50 focus-visible:ring-red-500",
  ghost:
    "text-muted hover:bg-app hover:text-ink active:bg-app disabled:opacity-40 focus-visible:ring-brand",
  outline:
    "border border-brand/30 text-brandink bg-brandsoft hover:opacity-90 active:opacity-80 disabled:opacity-50 focus-visible:ring-brand",
};

const sizes: Record<NonNullable<ButtonProps["size"]>, string> = {
  sm: "px-3 py-1.5 text-xs rounded-lg",
  md: "px-4 py-2 text-sm rounded-xl",
  lg: "px-5 py-2.5 text-sm rounded-xl",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  {
    variant = "primary",
    size = "md",
    loading = false,
    className = "",
    type = "button",
    disabled,
    children,
    ...props
  },
  ref
) {
  return (
    <button
      ref={ref}
      type={type}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={cn(
        "inline-flex items-center justify-center gap-1.5 font-medium transition-all duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-1 disabled:cursor-not-allowed",
        variants[variant],
        sizes[size],
        className
      )}
      {...props}
    >
      {loading && <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden />}
      {children}
    </button>
  );
});

import { forwardRef, useId, type InputHTMLAttributes } from "react";
import { cn } from "@/lib/cn";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(function Input(
  { className = "", label, error, id, ...props },
  ref
) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const errorId = error ? `${inputId}-error` : undefined;

  const field = (
    <input
      ref={ref}
      id={inputId}
      aria-invalid={error ? true : undefined}
      aria-describedby={errorId}
      className={cn(
        "w-full rounded-xl border bg-surface2 px-3 py-2 text-sm text-ink placeholder:text-faint transition-all duration-150 focus:outline-none focus:ring-2 disabled:cursor-not-allowed disabled:opacity-60",
        error
          ? "border-red-400 focus:border-red-400 focus:ring-red-500/15"
          : "border-border2 hover:border-muted focus:border-brand focus:ring-brand/20",
        className
      )}
      {...props}
    />
  );

  if (!label && !error) return field;

  return (
    <div className="space-y-1">
      {label && (
        <label htmlFor={inputId} className="block text-sm font-medium text-ink2">
          {label}
        </label>
      )}
      {field}
      {error && (
        <p id={errorId} className="text-xs text-dangertext">
          {error}
        </p>
      )}
    </div>
  );
});

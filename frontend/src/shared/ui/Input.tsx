import type { InputHTMLAttributes } from "react";

export function Input({
  className = "",
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={`min-h-11 w-full rounded-lg border border-slate-300 px-3 py-2.5 text-base sm:text-sm focus-visible:border-indigo-500 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-0 focus-visible:outline-indigo-500 ${className}`}
      {...props}
    />
  );
}

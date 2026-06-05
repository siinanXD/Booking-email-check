import { useEffect, useRef, useState } from "react";
import {
  EMPLOYEE_WHATSAPP_LOCALE_META,
  EMPLOYEE_WHATSAPP_LOCALES,
  normalizeEmployeeLocale,
  type EmployeeWhatsAppLocale,
} from "@/lib/whatsappLocales";

type EmployeeLocalePickerProps = {
  value: string;
  onChange: (locale: EmployeeWhatsAppLocale) => void;
  className?: string;
};

export function EmployeeLocalePicker({
  value,
  onChange,
  className = "",
}: EmployeeLocalePickerProps) {
  const [open, setOpen] = useState(false);
  const rootRef = useRef<HTMLDivElement>(null);
  const locale = normalizeEmployeeLocale(value);
  const current = EMPLOYEE_WHATSAPP_LOCALE_META[locale];

  useEffect(() => {
    if (!open) return;
    function handlePointerDown(event: MouseEvent) {
      if (rootRef.current?.contains(event.target as Node)) return;
      setOpen(false);
    }
    document.addEventListener("mousedown", handlePointerDown);
    return () => document.removeEventListener("mousedown", handlePointerDown);
  }, [open]);

  return (
    <div ref={rootRef} className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex h-8 w-8 items-center justify-center rounded-md border border-slate-200 bg-white text-lg leading-none shadow-sm transition hover:border-slate-300 hover:bg-slate-50 focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
        aria-label={`Language: ${current.englishName}`}
        aria-expanded={open}
        aria-haspopup="listbox"
        title={current.englishName}
      >
        <span aria-hidden="true">{current.flag}</span>
      </button>

      {open && (
        <ul
          role="listbox"
          aria-label="Select language"
          className="absolute right-0 z-30 mt-1 min-w-[10.5rem] overflow-hidden rounded-lg border border-slate-200 bg-white py-1 shadow-lg"
        >
          {EMPLOYEE_WHATSAPP_LOCALES.map((option) => {
            const meta = EMPLOYEE_WHATSAPP_LOCALE_META[option];
            const selected = option === locale;
            return (
              <li key={option} role="option" aria-selected={selected}>
                <button
                  type="button"
                  onClick={() => {
                    onChange(option);
                    setOpen(false);
                  }}
                  className={`flex w-full items-center gap-2 px-3 py-2 text-left text-sm transition hover:bg-slate-50 ${
                    selected ? "bg-indigo-50 font-medium text-indigo-700" : "text-slate-700"
                  }`}
                >
                  <span className="text-base leading-none" aria-hidden="true">
                    {meta.flag}
                  </span>
                  <span>{meta.englishName}</span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </div>
  );
}

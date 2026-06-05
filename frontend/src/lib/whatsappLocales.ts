export const EMPLOYEE_WHATSAPP_LOCALES = ["de", "en", "pl", "it", "es"] as const;

export type EmployeeWhatsAppLocale = (typeof EMPLOYEE_WHATSAPP_LOCALES)[number];

export const DEFAULT_EMPLOYEE_WHATSAPP_LOCALE: EmployeeWhatsAppLocale = "de";

export const EMPLOYEE_WHATSAPP_LOCALE_META: Record<
  EmployeeWhatsAppLocale,
  { flag: string; englishName: string }
> = {
  de: { flag: "🇩🇪", englishName: "German" },
  en: { flag: "🇬🇧", englishName: "English" },
  pl: { flag: "🇵🇱", englishName: "Polish" },
  it: { flag: "🇮🇹", englishName: "Italian" },
  es: { flag: "🇪🇸", englishName: "Spanish" },
};

/** @deprecated Use EMPLOYEE_WHATSAPP_LOCALE_META[locale].englishName */
export const EMPLOYEE_WHATSAPP_LOCALE_LABELS: Record<EmployeeWhatsAppLocale, string> = {
  de: EMPLOYEE_WHATSAPP_LOCALE_META.de.englishName,
  en: EMPLOYEE_WHATSAPP_LOCALE_META.en.englishName,
  pl: EMPLOYEE_WHATSAPP_LOCALE_META.pl.englishName,
  it: EMPLOYEE_WHATSAPP_LOCALE_META.it.englishName,
  es: EMPLOYEE_WHATSAPP_LOCALE_META.es.englishName,
};

export function normalizeEmployeeLocale(
  locale: string | null | undefined
): EmployeeWhatsAppLocale {
  const key = (locale ?? "").trim().toLowerCase();
  if ((EMPLOYEE_WHATSAPP_LOCALES as readonly string[]).includes(key)) {
    return key as EmployeeWhatsAppLocale;
  }
  return DEFAULT_EMPLOYEE_WHATSAPP_LOCALE;
}

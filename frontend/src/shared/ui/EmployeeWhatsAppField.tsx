import type { EmployeeWhatsAppLocale } from "@/lib/whatsappLocales";
import { EmployeeLocalePicker } from "@/shared/ui/EmployeeLocalePicker";
import { Input } from "@/shared/ui/Input";

type EmployeeWhatsAppFieldProps = {
  phone: string;
  locale: string;
  onPhoneChange: (phone: string) => void;
  onLocaleChange: (locale: EmployeeWhatsAppLocale) => void;
  phonePlaceholder?: string;
};

export function EmployeeWhatsAppField({
  phone,
  locale,
  onPhoneChange,
  onLocaleChange,
  phonePlaceholder = "WhatsApp +49…",
}: EmployeeWhatsAppFieldProps) {
  return (
    <div className="flex items-center gap-2">
      <Input
        className="min-w-0 flex-1"
        placeholder={phonePlaceholder}
        value={phone}
        onChange={(event) => onPhoneChange(event.target.value)}
      />
      <EmployeeLocalePicker value={locale} onChange={onLocaleChange} />
    </div>
  );
}

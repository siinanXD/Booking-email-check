import { Moon, Sun } from "lucide-react";
import { useThemeStore } from "@/shared/theme/themeStore";

type ThemeToggleProps = {
  className?: string;
};

/** Topbar-Button zum Umschalten zwischen hell und dunkel. */
export function ThemeToggle({ className = "" }: ThemeToggleProps) {
  const theme = useThemeStore((s) => s.theme);
  const toggleTheme = useThemeStore((s) => s.toggleTheme);
  const isDark = theme === "dark";

  return (
    <button
      type="button"
      onClick={toggleTheme}
      aria-label={isDark ? "Helles Design" : "Dunkles Design"}
      title={isDark ? "Helles Design" : "Dunkles Design"}
      className={`flex h-[34px] w-[34px] items-center justify-center rounded-lg border border-border bg-app text-muted transition-colors hover:text-ink ${className}`}
    >
      {isDark ? <Sun size={16} /> : <Moon size={16} />}
    </button>
  );
}

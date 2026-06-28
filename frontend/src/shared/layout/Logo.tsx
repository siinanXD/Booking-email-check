type LogoProps = {
  /** Kantenlänge des Verlauf-Quadrats in px. */
  size?: number;
  /** Admin-Punkt (kleiner Indikator) anzeigen. */
  showAdminDot?: boolean;
  className?: string;
};

/** Briefumschlag-Mark auf Brand-Verlauf — kein Bild-Asset, reines SVG. */
export function Logo({ size = 36, showAdminDot = false, className = "" }: LogoProps) {
  const icon = Math.round(size * 0.58);
  return (
    <div
      className={`relative flex flex-none items-center justify-center rounded-xl bg-brand-gradient-140 ${className}`}
      style={{ width: size, height: size }}
    >
      <svg width={icon} height={icon} viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <rect x="3" y="6" width="18" height="13" rx="3.4" stroke="#fff" strokeWidth="1.8" />
        <path
          d="M4.2 8.6l6.9 4.9a1.6 1.6 0 0 0 1.8 0l6.9-4.9"
          stroke="#fff"
          strokeWidth="1.8"
          strokeLinecap="round"
        />
      </svg>
      {showAdminDot && (
        <span className="absolute -right-0.5 -top-0.5 h-2.5 w-2.5 rounded-full border-2 border-rail1 bg-amber-400" />
      )}
    </div>
  );
}

import type { ReactNode } from "react";

export function CheckIcon({ className = "h-3.5 w-3.5" }: { className?: string }) {
  return (
    <svg aria-hidden="true" viewBox="0 0 24 24" className={className} fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round">
      <path d="m5 12 4 4 10-10" />
    </svg>
  );
}

type IconProps = { className?: string };

function StrokeIcon({ className = "h-4 w-4", children }: IconProps & { children: ReactNode }) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 24 24"
      className={className}
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {children}
    </svg>
  );
}

export function DashboardIcon({ className }: IconProps) {
  return (
    <StrokeIcon className={className}>
      <rect x="3" y="3" width="7" height="8" rx="1.5" />
      <rect x="14" y="3" width="7" height="5" rx="1.5" />
      <rect x="14" y="12" width="7" height="9" rx="1.5" />
      <rect x="3" y="15" width="7" height="6" rx="1.5" />
    </StrokeIcon>
  );
}

export function PlusCircleIcon({ className }: IconProps) {
  return (
    <StrokeIcon className={className}>
      <circle cx="12" cy="12" r="9" />
      <path d="M12 8v8" />
      <path d="M8 12h8" />
    </StrokeIcon>
  );
}

export function FileTextIcon({ className }: IconProps) {
  return (
    <StrokeIcon className={className}>
      <path d="M14 2H7a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7z" />
      <path d="M14 2v5h5" />
      <path d="M9 13h6" />
      <path d="M9 17h6" />
      <path d="M9 9h1" />
    </StrokeIcon>
  );
}

export function CompareIcon({ className }: IconProps) {
  return (
    <StrokeIcon className={className}>
      <path d="M7 7h11l-3-3" />
      <path d="m15 10 3-3-3-3" />
      <path d="M17 17H6l3 3" />
      <path d="m9 14-3 3 3 3" />
    </StrokeIcon>
  );
}

export function ClipboardListIcon({ className }: IconProps) {
  return (
    <StrokeIcon className={className}>
      <rect x="8" y="2" width="8" height="4" rx="1" />
      <path d="M16 4h2a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h2" />
      <path d="M8 11h8" />
      <path d="M8 16h6" />
    </StrokeIcon>
  );
}

export function DownloadIcon({ className }: IconProps) {
  return (
    <StrokeIcon className={className}>
      <path d="M12 3v12" />
      <path d="m7 10 5 5 5-5" />
      <path d="M5 21h14" />
    </StrokeIcon>
  );
}

export function SettingsIcon({ className }: IconProps) {
  return (
    <StrokeIcon className={className}>
      <path d="M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8Z" />
      <path d="M4.9 19.1 6.3 17" />
      <path d="M17.7 7 19.1 4.9" />
      <path d="M2.5 12h2.4" />
      <path d="M19.1 12h2.4" />
      <path d="M4.9 4.9 6.3 7" />
      <path d="M17.7 17l1.4 2.1" />
    </StrokeIcon>
  );
}

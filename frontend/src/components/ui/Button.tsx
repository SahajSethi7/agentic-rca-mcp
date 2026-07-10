import type { ButtonHTMLAttributes } from "react";

type Variant = "primary" | "secondary" | "tint" | "ghost";
type Size = "sm" | "md" | "lg";

const VARIANT: Record<Variant, string> = {
  // #0073a8 fill: >= 4.5:1 with white text (WCAG AA), unlike #009fdb (~3:1).
  primary: "bg-primary-hover font-bold text-white hover:bg-primary-selected",
  secondary: "border border-slate-300 bg-white font-semibold text-ink-soft hover:border-primary-soft hover:text-primary-selected",
  tint: "border border-primary-soft bg-white font-bold text-primary-selected hover:bg-primary-tint",
  ghost: "font-semibold text-ink-soft hover:bg-primary-tint hover:text-primary-selected",
};

const SIZE: Record<Size, string> = {
  sm: "h-9 px-3 text-ui",
  md: "h-10 px-3 text-body-sm",
  lg: "h-11 px-4 text-body",
};

export default function Button({
  variant = "primary",
  size = "md",
  className = "",
  type = "button",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: Variant; size?: Size }) {
  return (
    <button
      type={type}
      className={`inline-flex items-center justify-center gap-2 rounded-md transition active:translate-y-px disabled:cursor-not-allowed disabled:opacity-60 disabled:active:translate-y-0 ${VARIANT[variant]} ${SIZE[size]} ${className}`}
      {...props}
    />
  );
}

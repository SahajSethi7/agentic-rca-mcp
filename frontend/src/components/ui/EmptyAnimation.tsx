import { lazy, Suspense } from "react";
import emptyStateAnimation from "../../assets/empty-state.json";

const LottieFigure = lazy(() => import("./LottieFigure"));

function prefersReducedMotion() {
  return (
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches
  );
}

/** Static SVG shown when the user prefers reduced motion. */
function StaticIllustration() {
  return (
    <svg aria-hidden="true" viewBox="0 0 96 72" className="mx-auto mb-4 h-16 w-20 text-att-300">
      <path d="M16 54h64" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      <rect x="22" y="18" width="52" height="32" rx="5" fill="#eaf8fe" stroke="currentColor" strokeWidth="2" />
      <path d="M32 30h32M32 39h20" fill="none" stroke="#005a8f" strokeWidth="2" strokeLinecap="round" />
      <circle cx="72" cy="18" r="5" fill="#eaf8fe" stroke="currentColor" strokeWidth="2" />
      <path d="M38 14h20M48 14v-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
    </svg>
  );
}

export default function EmptyAnimation() {
  if (prefersReducedMotion()) return <StaticIllustration />;
  return (
    <Suspense fallback={<StaticIllustration />}>
      <LottieFigure animationData={emptyStateAnimation} className="mx-auto mb-4 h-20 w-[100px]" />
    </Suspense>
  );
}

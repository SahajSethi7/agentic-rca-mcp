import LottieImport from "lottie-react";

// lottie-react is published as CommonJS. Depending on the Vite dev/build
// interop path, its default import can arrive either as the component itself
// or as a module object whose `default` is the component.
const Lottie = (
  (LottieImport as unknown as { default?: typeof LottieImport }).default ?? LottieImport
);

/**
 * Small wrapper around lottie-react:
 * - honors prefers-reduced-motion (renders the first frame, no autoplay)
 * - decorative by default (aria-hidden) unless a label is provided
 *
 * The build aliases "lottie-web" to its light player (SVG renderer, no
 * expressions), which avoids the production eval warning entirely.
 */
export default function LottieFigure({
  animationData,
  className = "",
  label,
}: {
  animationData: object;
  className?: string;
  label?: string;
}) {
  const reducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-reduced-motion: reduce)").matches;

  return (
    <div
      className={className}
      role={label ? "img" : undefined}
      aria-label={label}
      aria-hidden={label ? undefined : true}
    >
      <Lottie animationData={animationData} loop autoplay={!reducedMotion} />
    </div>
  );
}

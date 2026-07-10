import type { ReactNode } from "react";
import { LazyMotion, MotionConfig } from "motion/react";

// Async feature loading: keeps motion features out of the initial bundle.
// domMax (not domAnimation) is required for layoutId/layout animations
// used by the sidebar and mobile-nav active pills.
const loadFeatures = () => import("./motionFeatures").then((mod) => mod.default);

export default function MotionProvider({ children }: { children: ReactNode }) {
  return (
    <LazyMotion features={loadFeatures} strict>
      <MotionConfig reducedMotion="user" transition={{ duration: 0.18, ease: [0.22, 1, 0.36, 1] }}>
        {children}
      </MotionConfig>
    </LazyMotion>
  );
}

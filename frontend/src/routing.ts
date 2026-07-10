export type Surface = "recent" | "new" | "reports" | "run" | "report" | "compare" | "audit" | "exports" | "settings";

const KNOWN_SURFACES = new Set<Surface>([
  "recent",
  "new",
  "reports",
  "run",
  "report",
  "compare",
  "audit",
  "exports",
  "settings",
]);

export function parseRouteHash(hash: string): { surface: Surface; runKey?: string | null; matched: boolean } {
  const raw = hash.replace(/^#\/?/, "");
  const [surface, encodedKey] = raw.split("/");
  if (!KNOWN_SURFACES.has(surface as Surface)) {
    return { surface: "new", matched: false };
  }
  if (!encodedKey) {
    return { surface: surface as Surface, runKey: undefined, matched: true };
  }
  try {
    return {
      surface: surface as Surface,
      runKey: decodeURIComponent(encodedKey),
      matched: true,
    };
  } catch {
    return { surface: "new", matched: false };
  }
}

export function routeHash(surface: Surface, key?: string | null) {
  const needsKey = (surface === "run" || surface === "report") && key;
  return needsKey ? `#/${surface}/${encodeURIComponent(key)}` : `#/${surface}`;
}

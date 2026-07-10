export default function KeyValueList({
  items,
  labelWidth = "112px",
  size = "sm",
}: {
  items: [string, string][];
  labelWidth?: string;
  size?: "sm" | "xs";
}) {
  const text = size === "xs" ? "text-ui" : "text-body-sm";
  return (
    <div className="space-y-3">
      {items.map(([label, value]) => (
        <div
          key={label}
          className={`grid gap-3 ${text}`}
          style={{ gridTemplateColumns: `${labelWidth} minmax(0,1fr)` }}
        >
          <span className="font-medium text-ink-muted">{label}</span>
          <span className="min-w-0 break-words font-semibold text-ink">{value}</span>
        </div>
      ))}
    </div>
  );
}

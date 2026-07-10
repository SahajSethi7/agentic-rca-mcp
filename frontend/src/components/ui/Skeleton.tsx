export function SkeletonBar({ className = "h-3 w-full" }: { className?: string }) {
  return <div className={`skeleton-shimmer rounded-full ${className}`} aria-hidden="true" />;
}

export function SkeletonRows({ rows = 3, label = "Loading" }: { rows?: number; label?: string }) {
  return (
    <div className="space-y-3" role="status" aria-label={label}>
      {Array.from({ length: rows }).map((_, index) => (
        <div key={index} className="space-y-2">
          <SkeletonBar className="h-3 w-36" />
          <SkeletonBar className="h-3 w-full" />
        </div>
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 4, label = "Loading runs" }: { rows?: number; label?: string }) {
  return (
    <div className="overflow-hidden rounded-lg border border-slate-200 bg-white shadow-card" role="status" aria-label={label}>
      <div className="border-b border-slate-200 px-4 py-3">
        <SkeletonBar className="h-3 w-48" />
      </div>
      <div className="divide-y divide-slate-100">
        {Array.from({ length: rows }).map((_, index) => (
          <div key={index} className="grid grid-cols-[minmax(0,1fr)_120px_120px_100px] items-center gap-4 px-4 py-4">
            <div className="space-y-2">
              <SkeletonBar className="h-3 w-3/4" />
              <SkeletonBar className="h-2.5 w-24" />
            </div>
            <SkeletonBar className="h-3 w-16" />
            <SkeletonBar className="h-3 w-20" />
            <SkeletonBar className="h-6 w-full rounded-md" />
          </div>
        ))}
      </div>
    </div>
  );
}

export function SkeletonCards({ cards = 4, label = "Loading reports" }: { cards?: number; label?: string }) {
  return (
    <div className="grid gap-4 lg:grid-cols-2" role="status" aria-label={label}>
      {Array.from({ length: cards }).map((_, index) => (
        <div key={index} className="rounded-lg border border-slate-200 bg-white p-4 shadow-card">
          <div className="flex justify-between gap-2">
            <SkeletonBar className="h-5 w-20 rounded-md" />
            <SkeletonBar className="h-5 w-16 rounded-md" />
          </div>
          <SkeletonBar className="mt-4 h-4 w-5/6" />
          <SkeletonBar className="mt-3 h-3 w-full" />
          <SkeletonBar className="mt-2 h-3 w-2/3" />
        </div>
      ))}
    </div>
  );
}

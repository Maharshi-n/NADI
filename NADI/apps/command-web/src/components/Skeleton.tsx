interface SkeletonProps {
  width?: string;
  height?: string;
  borderRadius?: string;
  className?: string;
}

/**
 * Skeleton loader — per CONTEXT.md: "Skeleton loaders, never blank screens"
 */
export function Skeleton({ width = '100%', height = '16px', borderRadius, className = '' }: SkeletonProps) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{ width, height, borderRadius }}
    />
  );
}

export function SkeletonKpiTile() {
  return (
    <div className="kpi-tile">
      <Skeleton width="80px" height="12px" />
      <Skeleton width="60px" height="28px" />
      <Skeleton width="100px" height="14px" />
    </div>
  );
}

export function SkeletonRiskItem() {
  return (
    <div className="risk-queue__item" style={{ opacity: 0.5 }}>
      <Skeleton width="8px" height="8px" borderRadius="50%" />
      <div className="risk-queue__item-info">
        <Skeleton width="120px" height="14px" />
        <Skeleton width="80px" height="12px" />
      </div>
      <div style={{ textAlign: 'right' }}>
        <Skeleton width="30px" height="20px" />
        <Skeleton width="30px" height="10px" />
      </div>
    </div>
  );
}

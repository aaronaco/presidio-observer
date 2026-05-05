import { Column, SkeletonText, Tile } from '@carbon/react'

export function MetricTile({ label, value, loading = false, help = null }) {
  return (
    <Column sm={4} md={2} lg={4}>
      <Tile className="metric-tile">
        {loading ? (
          <>
            <SkeletonText width="7rem" />
            <SkeletonText className="metric-tile-skeleton-value" heading width="8rem" />
          </>
        ) : (
          <>
            <span className="metric-tile-label">
              {label}
              {help}
            </span>
            <strong>{value}</strong>
          </>
        )}
      </Tile>
    </Column>
  )
}

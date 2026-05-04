import { Column, Tile } from '@carbon/react'

export function MetricTile({ label, value }) {
  return (
    <Column sm={4} md={2} lg={4}>
      <Tile className="metric-tile">
        <span>{label}</span>
        <strong>{value}</strong>
      </Tile>
    </Column>
  )
}

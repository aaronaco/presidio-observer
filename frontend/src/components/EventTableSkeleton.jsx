import { DataTableSkeleton } from '@carbon/react'

import { eventHeaders } from '../lib/events'

export function EventTableSkeleton() {
  return (
    <DataTableSkeleton
      className="event-table-container"
      columnCount={eventHeaders.length}
      headers={eventHeaders}
      rowCount={6}
      showHeader={false}
      showToolbar={false}
      size="sm"
    />
  )
}

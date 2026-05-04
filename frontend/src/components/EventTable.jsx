import {
  DataTable,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableHeader,
  TableRow,
  Tag,
} from '@carbon/react'

import { buildEventRows, eventHeaders, flagKind } from '../lib/events'

export function EventTable({ events, selectedEventId, onSelectEvent }) {
  return (
    <DataTable rows={buildEventRows(events)} headers={eventHeaders} size="sm" isSortable>
      {({
        rows,
        headers,
        getCellProps,
        getHeaderProps,
        getRowProps,
        getTableProps,
      }) => (
        <TableContainer className="event-table-container">
          <Table {...getTableProps()} aria-label="Recent Presidio Observer events">
            <TableHead>
              <TableRow>
                {headers.map((header) => (
                  <TableHeader key={header.key} {...getHeaderProps({ header })}>
                    {header.header}
                  </TableHeader>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((row) => {
                const rowProps = getRowProps({ row })
                const isSelected = row.id === selectedEventId

                return (
                  <TableRow
                    key={row.id}
                    {...rowProps}
                    className={`event-table-row${isSelected ? ' event-table-row--selected' : ''}`}
                    tabIndex={0}
                    onClick={() => onSelectEvent(row.id)}
                    onKeyDown={(event) => {
                      if (event.key === 'Enter' || event.key === ' ') {
                        event.preventDefault()
                        onSelectEvent(row.id)
                      }
                    }}
                  >
                    {row.cells.map((cell) => (
                      <TableCell key={cell.id} {...getCellProps({ cell })}>
                        {cell.info.header === 'flag' ? (
                          <Tag type={flagKind(cell.value)}>{cell.value}</Tag>
                        ) : (
                          cell.value
                        )}
                      </TableCell>
                    ))}
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </DataTable>
  )
}

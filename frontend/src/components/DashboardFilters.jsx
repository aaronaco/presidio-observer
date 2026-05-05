import {
  Button,
  Select,
  SelectItem,
  TextInput,
} from '@carbon/react'

import { commonEntityTypes, confidenceFlagOptions } from '../lib/events'

export const defaultDashboardFilters = {
  timeRange: 'all',
  language: '',
  entityType: '',
  flag: '',
}

const timeRangeOptions = [
  { value: 'all', text: 'All time' },
  { value: '15m', text: 'Last 15 minutes' },
  { value: '1h', text: 'Last hour' },
  { value: '24h', text: 'Last 24 hours' },
  { value: '7d', text: 'Last 7 days' },
]

export function dashboardFiltersToQuery(filters) {
  return {
    since: rangeToSince(filters.timeRange),
    language: filters.language.trim(),
    entityType: filters.entityType,
    flag: filters.flag,
  }
}

export function hasActiveDashboardFilters(filters) {
  return Boolean(
    filters.timeRange !== defaultDashboardFilters.timeRange
      || filters.language.trim()
      || filters.entityType
      || filters.flag,
  )
}

export function DashboardFilters({
  filters,
  loading,
  onApply,
  onChange,
  onReset,
}) {
  return (
    <form
      className="dashboard-filters"
      onSubmit={(event) => {
        event.preventDefault()
        onApply()
      }}
    >
      <div className="dashboard-filter-fields">
        <Select
          id="dashboard-filter-time-range"
          size="sm"
          labelText="Time range"
          value={filters.timeRange}
          onChange={(event) => onChange({ timeRange: event.target.value })}
        >
          {timeRangeOptions.map((option) => (
            <SelectItem key={option.value} value={option.value} text={option.text} />
          ))}
        </Select>
        <TextInput
          id="dashboard-filter-language"
          size="sm"
          labelText="Language"
          placeholder="en"
          value={filters.language}
          onChange={(event) => onChange({ language: event.currentTarget.value })}
        />
        <Select
          id="dashboard-filter-entity-type"
          size="sm"
          labelText="Entity type"
          value={filters.entityType}
          onChange={(event) => onChange({ entityType: event.target.value })}
        >
          <SelectItem value="" text="All entities" />
          {commonEntityTypes.map((entityType) => (
            <SelectItem key={entityType} value={entityType} text={entityType} />
          ))}
        </Select>
        <Select
          id="dashboard-filter-flag"
          size="sm"
          labelText="Confidence flag"
          value={filters.flag}
          onChange={(event) => onChange({ flag: event.target.value })}
        >
          <SelectItem value="" text="All flags" />
          {confidenceFlagOptions.map((flag) => (
            <SelectItem key={flag} value={flag} text={flag} />
          ))}
        </Select>
      </div>
      <div className="dashboard-filter-actions">
        <Button type="submit" kind="primary" size="sm" disabled={loading}>
          Apply filters
        </Button>
        <Button type="button" kind="ghost" size="sm" disabled={loading} onClick={onReset}>
          Reset
        </Button>
      </div>
    </form>
  )
}

function rangeToSince(timeRange) {
  const now = Date.now()
  const ranges = {
    '15m': 15 * 60 * 1000,
    '1h': 60 * 60 * 1000,
    '24h': 24 * 60 * 60 * 1000,
    '7d': 7 * 24 * 60 * 60 * 1000,
  }
  const duration = ranges[timeRange]

  if (!duration) {
    return ''
  }

  return new Date(now - duration).toISOString()
}

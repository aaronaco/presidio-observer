import { useEffect, useRef, useState } from 'preact/hooks'
import {
  Button,
  Column,
  Grid,
  InlineNotification,
  Tile,
} from '@carbon/react'

import {
  fetchDashboard,
  fetchEventLabels,
  removeEventLabel,
  submitEventLabel,
} from './api/observer'
import {
  DashboardFilters,
  dashboardFiltersToQuery,
  defaultDashboardFilters,
  hasActiveDashboardFilters,
} from './components/DashboardFilters'
import { EventDetailPanel } from './components/EventDetailPanel'
import { EventTable } from './components/EventTable'
import { EventTableSkeleton } from './components/EventTableSkeleton'
import { MetricTile } from './components/MetricTile'
import { SectionHelp } from './components/SectionHelp'
import { eventEntityTypes } from './lib/events'
import { formatEvaluationPercent, formatNumber, formatPercent } from './lib/formatters'

const emptyDashboard = {
  stats: null,
  events: [],
  evaluation: null,
}

const idleLabelStatus = {
  loading: false,
  error: null,
  success: null,
}

const idleEventLabels = {
  loading: false,
  error: null,
  items: [],
}

export function App() {
  const [dashboard, setDashboard] = useState(emptyDashboard)
  const [status, setStatus] = useState({ loading: true, error: null })
  const [selectedEventId, setSelectedEventId] = useState(null)
  const [labelStatus, setLabelStatus] = useState(idleLabelStatus)
  const [eventLabels, setEventLabels] = useState(idleEventLabels)
  const [dashboardFilters, setDashboardFilters] = useState(defaultDashboardFilters)
  const [appliedDashboardFilters, setAppliedDashboardFilters] = useState(defaultDashboardFilters)
  const labelRequestEventId = useRef(null)

  const selectedEvent = dashboard.events.find((event) => event.id === selectedEventId)
  const filtersActive = hasActiveDashboardFilters(appliedDashboardFilters)
  const isInitialLoading = status.loading
    && !dashboard.stats
    && !dashboard.events.length
    && !dashboard.evaluation

  async function loadDashboard(filters = appliedDashboardFilters) {
    setStatus({ loading: true, error: null })

    try {
      const nextDashboard = await fetchDashboard(dashboardFiltersToQuery(filters))
      setDashboard(nextDashboard)
      setStatus({ loading: false, error: null })
    } catch (error) {
      setStatus({ loading: false, error: error.message })
    }
  }

  function updateDashboardFilters(nextFilters) {
    setDashboardFilters((currentFilters) => ({
      ...currentFilters,
      ...nextFilters,
    }))
  }

  function applyDashboardFilters() {
    setAppliedDashboardFilters(dashboardFilters)
    setSelectedEventId(null)
    setEventLabels(idleEventLabels)
    labelRequestEventId.current = null
    loadDashboard(dashboardFilters)
  }

  function resetDashboardFilters() {
    setDashboardFilters(defaultDashboardFilters)
    setAppliedDashboardFilters(defaultDashboardFilters)
    setSelectedEventId(null)
    setEventLabels(idleEventLabels)
    labelRequestEventId.current = null
    loadDashboard(defaultDashboardFilters)
  }

  async function loadEventLabels(eventId) {
    labelRequestEventId.current = eventId
    setEventLabels({ loading: true, error: null, items: [] })

    try {
      const items = await fetchEventLabels(eventId)
      if (labelRequestEventId.current !== eventId) {
        return
      }
      setEventLabels({ loading: false, error: null, items })
    } catch (error) {
      if (labelRequestEventId.current !== eventId) {
        return
      }
      setEventLabels({ loading: false, error: error.message, items: [] })
    }
  }

  function selectEvent(eventId) {
    setSelectedEventId(eventId)
    setLabelStatus(idleLabelStatus)
    loadEventLabels(eventId)
  }

  async function submitLabel(label, entityType, count = 1, entityStart = null, entityEnd = null) {
    if (!selectedEvent) {
      return
    }

    setLabelStatus({ loading: true, error: null, success: null })

    try {
      await submitEventLabel(selectedEvent.id, {
        entity_type: entityType || eventEntityTypes(selectedEvent)[0] || 'UNKNOWN',
        label,
        count,
        entity_start: entityStart,
        entity_end: entityEnd,
      })

      setLabelStatus({
        loading: false,
        error: null,
        success: `${label.replace('_', ' ')} label saved`,
      })
      loadEventLabels(selectedEvent.id)
      loadDashboard()
    } catch (error) {
      setLabelStatus({ loading: false, error: error.message, success: null })
    }
  }

  async function removeLabel(labelId) {
    if (!selectedEvent) {
      return
    }

    setLabelStatus({ loading: true, error: null, success: null })

    try {
      await removeEventLabel(selectedEvent.id, labelId)
      setLabelStatus({
        loading: false,
        error: null,
        success: 'Label removed',
      })
      loadEventLabels(selectedEvent.id)
      loadDashboard()
    } catch (error) {
      setLabelStatus({ loading: false, error: error.message, success: null })
    }
  }

  useEffect(() => {
    loadDashboard()
  }, [])

  return (
    <main className="observer-shell">
      <section className="observer-hero">
        <div>
          <h1>Presidio Observer</h1>
          <p>
            View analyzer events, entity metadata, latency, and evaluation labels
            from the local backend.
          </p>
        </div>
        <Button kind="primary" onClick={loadDashboard} disabled={status.loading}>
          Refresh dashboard
        </Button>
      </section>

      {status.error && (
        <InlineNotification
          kind="error"
          lowContrast
          title="Backend unavailable"
          subtitle={`Could not load observer data: ${status.error}`}
        />
      )}

      <Grid className="metric-grid" condensed>
        <MetricTile
          label="Analyze calls"
          loading={isInitialLoading}
          value={formatNumber(dashboard.stats?.total_analyzed)}
        />
        <MetricTile
          label="Average latency"
          loading={isInitialLoading}
          value={`${formatNumber(dashboard.stats?.avg_latency_ms, 1)} ms`}
        />
        <MetricTile
          label="Precision"
          loading={isInitialLoading}
          value={formatPercent(dashboard.evaluation?.precision)}
        />
        <MetricTile
          label="Reported F2"
          loading={isInitialLoading}
          value={formatEvaluationPercent(dashboard.evaluation?.f2_score)}
          help={(
            <SectionHelp title="Reported F2">
              This score uses saved correct labels and manually reported missed counts.
              It is useful for local review, but it is not a full ground-truth benchmark.
            </SectionHelp>
          )}
        />
      </Grid>

      <Grid className="dashboard-grid" condensed>
        <Column sm={4} md={8} lg={16}>
          <Tile className="panel dashboard-filter-panel">
            <div className="panel-heading">
              <div>
                <h2>Filters</h2>
                <p>Limit local dashboard data by analyzer metadata.</p>
              </div>
              <span>{filtersActive ? 'Filtered view' : 'All analyzer events'}</span>
            </div>
            <DashboardFilters
              filters={dashboardFilters}
              loading={status.loading}
              onApply={applyDashboardFilters}
              onChange={updateDashboardFilters}
              onReset={resetDashboardFilters}
            />
          </Tile>
        </Column>
      </Grid>

      <Grid className="dashboard-grid" condensed>
        <Column sm={4} md={8} lg={16}>
          <Tile className="panel">
            <div className="panel-heading">
              <div>
                <h2>Event Worklist</h2>
                <p>Click a row to inspect metadata and submit evaluation labels.</p>
              </div>
              <span>{filtersActive ? 'Latest 12 matching events' : 'Latest 12 events'}</span>
            </div>
            {isInitialLoading ? (
              <EventTableSkeleton />
            ) : dashboard.events.length ? (
              <EventTable
                events={dashboard.events}
                selectedEventId={selectedEventId}
                onSelectEvent={selectEvent}
              />
            ) : (
              <p className="empty-state">Run the SDK example to populate events.</p>
            )}
          </Tile>
        </Column>
      </Grid>

      <EventDetailPanel
        event={selectedEvent}
        eventLabels={eventLabels}
        labelStatus={labelStatus}
        onClose={() => {
          setSelectedEventId(null)
          labelRequestEventId.current = null
          setEventLabels(idleEventLabels)
        }}
        onRemoveLabel={removeLabel}
        onSubmitLabel={submitLabel}
      />
    </main>
  )
}

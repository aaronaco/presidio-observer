import { useEffect, useState } from 'preact/hooks'
import {
  Button,
  Column,
  Grid,
  InlineNotification,
  Tile,
} from '@carbon/react'

import { fetchDashboard, fetchEventLabels, submitEventLabel } from './api/observer'
import { EventDetailPanel } from './components/EventDetailPanel'
import { EventTable } from './components/EventTable'
import { EventTableSkeleton } from './components/EventTableSkeleton'
import { MetricTile } from './components/MetricTile'
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

  const selectedEvent = dashboard.events.find((event) => event.id === selectedEventId)
  const isInitialLoading = status.loading
    && !dashboard.stats
    && !dashboard.events.length
    && !dashboard.evaluation

  async function loadDashboard() {
    setStatus({ loading: true, error: null })

    try {
      const nextDashboard = await fetchDashboard()
      setDashboard(nextDashboard)
      setStatus({ loading: false, error: null })
    } catch (error) {
      setStatus({ loading: false, error: error.message })
    }
  }

  async function loadEventLabels(eventId) {
    setEventLabels({ loading: true, error: null, items: [] })

    try {
      const items = await fetchEventLabels(eventId)
      setEventLabels({ loading: false, error: null, items })
    } catch (error) {
      setEventLabels({ loading: false, error: error.message, items: [] })
    }
  }

  function selectEvent(eventId) {
    setSelectedEventId(eventId)
    setLabelStatus(idleLabelStatus)
    loadEventLabels(eventId)
  }

  async function submitLabel(label, entityType, count = 1) {
    if (!selectedEvent) {
      return
    }

    setLabelStatus({ loading: true, error: null, success: null })

    try {
      await submitEventLabel(selectedEvent.id, {
        entity_type: entityType || eventEntityTypes(selectedEvent)[0] || 'UNKNOWN',
        label,
        count,
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
        />
      </Grid>

      <Grid className="dashboard-grid" condensed>
        <Column sm={4} md={8} lg={16}>
          <Tile className="panel">
            <div className="panel-heading">
              <div>
                <h2>Event Worklist</h2>
                <p>Click a row to inspect metadata and submit evaluation labels.</p>
              </div>
              <span>Latest 12 events</span>
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
          setEventLabels(idleEventLabels)
        }}
        onSubmitLabel={submitLabel}
      />
    </main>
  )
}

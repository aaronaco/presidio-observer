import { useEffect, useState } from 'preact/hooks'
import {
  Button,
  Column,
  Grid,
  InlineNotification,
  Tag,
  Tile,
} from '@carbon/react'

import { fetchDashboard, submitEventLabel } from './api/observer'
import { EventDetailPanel } from './components/EventDetailPanel'
import { EventTable } from './components/EventTable'
import { EventTableSkeleton } from './components/EventTableSkeleton'
import { MetricTile } from './components/MetricTile'
import { eventEntityTypes } from './lib/events'
import { formatNumber, formatPercent } from './lib/formatters'

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

export function App() {
  const [dashboard, setDashboard] = useState(emptyDashboard)
  const [status, setStatus] = useState({ loading: true, error: null })
  const [selectedEventId, setSelectedEventId] = useState(null)
  const [labelStatus, setLabelStatus] = useState(idleLabelStatus)

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

  function selectEvent(eventId) {
    setSelectedEventId(eventId)
    setLabelStatus(idleLabelStatus)
  }

  async function submitLabel(label, entityType) {
    if (!selectedEvent) {
      return
    }

    setLabelStatus({ loading: true, error: null, success: null })

    try {
      await submitEventLabel(selectedEvent.id, {
        entity_type: entityType || eventEntityTypes(selectedEvent)[0] || 'UNKNOWN',
        label,
      })

      setLabelStatus({
        loading: false,
        error: null,
        success: `${label.replace('_', ' ')} label saved`,
      })
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
          <Tag type="cyan">Presidio Observer</Tag>
          <h1>Live privacy telemetry without raw text capture.</h1>
          <p>
            Monitor analyzer confidence, entity mix, latency, and evaluation
            quality from the local FastAPI backend.
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
          label="F2 score"
          loading={isInitialLoading}
          value={formatPercent(dashboard.evaluation?.f2_score)}
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
        labelStatus={labelStatus}
        onClose={() => setSelectedEventId(null)}
        onSubmitLabel={submitLabel}
      />
    </main>
  )
}

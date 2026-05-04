import { useState } from 'preact/hooks'
import {
  Accordion,
  AccordionItem,
  Button,
  InlineNotification,
  Select,
  SelectItem,
  Tab,
  TabList,
  TabPanel,
  TabPanels,
  Tabs,
  Tag,
} from '@carbon/react'

import { DetailItem } from './DetailItem'
import { formatDate, formatList, formatNumber } from '../lib/formatters'
import {
  entityName,
  eventEntityCount,
  eventEntityTypes,
  flagKind,
  sortEntities,
} from '../lib/events'

export function EventDetailPanel({ event, labelStatus, onClose, onSubmitLabel }) {
  const entityTypes = event ? eventEntityTypes(event) : []
  const primaryEntityType = entityTypes[0] || 'UNKNOWN'
  const [entitySortMode, setEntitySortMode] = useState('score_desc')
  const visibleEntities = event ? sortEntities(event.entities || [], entitySortMode) : []

  function resetEntityControls() {
    setEntitySortMode('score_desc')
  }

  return (
    <>
      {event && (
        <button
          className="drawer-scrim"
          type="button"
          aria-label="Close event detail"
          onClick={onClose}
        />
      )}
      <aside className={`event-drawer${event ? ' event-drawer--open' : ''}`} aria-hidden={!event}>
        {event && (
          <>
            <div className="event-drawer-header">
              <div>
                <Tag type={flagKind(event.flag)}>{event.flag || 'n/a'}</Tag>
                <h2>{event.type} event</h2>
                <p>{event.id}</p>
              </div>
              <Button kind="ghost" size="sm" onClick={onClose}>
                Close
              </Button>
            </div>

            <Tabs>
              <TabList aria-label="Event detail sections">
                <Tab>Summary</Tab>
                <Tab>Entities</Tab>
                <Tab>Evaluation</Tab>
              </TabList>
              <TabPanels>
                <TabPanel>
                  <EventSummary event={event} />
                </TabPanel>
                <TabPanel>
                  <EntityInspector
                    entities={event.entities || []}
                    sortMode={entitySortMode}
                    visibleEntities={visibleEntities}
                    onReset={resetEntityControls}
                    onSortModeChange={setEntitySortMode}
                  />
                </TabPanel>
                <TabPanel>
                  <EvaluationControls
                    labelStatus={labelStatus}
                    primaryEntityType={primaryEntityType}
                    onSubmitLabel={onSubmitLabel}
                  />
                </TabPanel>
              </TabPanels>
            </Tabs>
          </>
        )}
      </aside>
    </>
  )
}

function EventSummary({ event }) {
  return (
    <div className="detail-list">
      <DetailItem label="Created" value={formatDate(event.created_at)} />
      <DetailItem label="Correlation ID" value={event.correlation_id || 'n/a'} />
      <DetailItem label="Language" value={event.language || 'n/a'} />
      <DetailItem label="Latency" value={`${formatNumber(event.latency_ms, 1)} ms`} />
      <DetailItem label="Has PII" value={event.has_pii ? 'Yes' : 'No'} />
      <DetailItem label="Entity count" value={eventEntityCount(event)} />
      <DetailItem label="Requested entities" value={formatList(event.requested_entities)} />
      <DetailItem label="Score threshold" value={event.score_threshold ?? 'n/a'} />
      <DetailItem label="Allow-list count" value={event.allow_list_count ?? 'n/a'} />
      <DetailItem label="NLP engine" value={event.nlp_engine || 'n/a'} />
      <DetailItem label="Context enhancer" value={event.context_enhancer || 'n/a'} />
      <DetailItem
        label="Operators used"
        value={event.operators_used?.length ? event.operators_used.join(', ') : 'n/a'}
      />
    </div>
  )
}

function EntityInspector({
  entities,
  sortMode,
  visibleEntities,
  onReset,
  onSortModeChange,
}) {
  if (!entities.length) {
    return <p className="empty-state">This event did not include entity details.</p>
  }

  return (
    <>
      <div className="entity-controls">
        <div className="entity-controls-fields">
          <Select
            id="entity-sort"
            size="sm"
            labelText="Sort entities"
            value={sortMode}
            onChange={(event) => onSortModeChange(event.target.value)}
          >
            <SelectItem value="score_desc" text="Score: high to low" />
            <SelectItem value="score_asc" text="Score: low to high" />
            <SelectItem value="name_asc" text="Name: A to Z" />
            <SelectItem value="name_desc" text="Name: Z to A" />
          </Select>
          <Button kind="ghost" size="sm" onClick={onReset}>
            Reset
          </Button>
        </div>
      </div>

      {visibleEntities.length ? (
        <Accordion className="entity-detail-list" align="start">
          {visibleEntities.map((entity, index) => (
            <EntityAccordionItem
              entity={entity}
              key={`${entity.type}-${entity.start}-${entity.end}-${index}`}
            />
          ))}
        </Accordion>
      ) : (
        <p className="empty-state">No entities match the current filters.</p>
      )}
    </>
  )
}

function EntityAccordionItem({ entity }) {
  return (
    <AccordionItem
      className="entity-detail-card"
      title={
        <div className="entity-accordion-title">
          <span>{entityName(entity)}</span>
          <strong>{formatNumber(entity.score, 3)}</strong>
        </div>
      }
    >
      <div className="entity-metadata-grid">
        <DetailItem label="Recognizer" value={entity.recognizer || 'unknown'} />
        <DetailItem label="Start offset" value={entity.start ?? 'n/a'} />
        <DetailItem label="End offset" value={entity.end ?? 'n/a'} />
        <DetailItem label="Span length" value={entity.span_length ?? 'n/a'} />
        <DetailItem label="Pattern name" value={entity.pattern_name || 'n/a'} />
        <DetailItem label="Original score" value={entity.original_score ?? 'n/a'} />
        <DetailItem
          label="Context boost"
          value={entity.score_context_improvement ?? 'n/a'}
        />
        <DetailItem label="Validation" value={entity.validation_result || 'n/a'} />
      </div>
    </AccordionItem>
  )
}

function EvaluationControls({ labelStatus, primaryEntityType, onSubmitLabel }) {
  return (
    <div className="evaluation-panel">
      <p>
        Submit a privacy-safe label against this event. No raw text is stored or displayed.
      </p>
      <div className="evaluation-actions">
        <Button
          kind="primary"
          disabled={labelStatus.loading}
          onClick={() => onSubmitLabel('correct', primaryEntityType)}
        >
          Correct
        </Button>
        <Button
          kind="secondary"
          disabled={labelStatus.loading}
          onClick={() => onSubmitLabel('false_positive', primaryEntityType)}
        >
          False positive
        </Button>
        <Button
          kind="tertiary"
          disabled={labelStatus.loading}
          onClick={() => onSubmitLabel('missed', primaryEntityType)}
        >
          Missed
        </Button>
      </div>
      {labelStatus.error && (
        <InlineNotification
          kind="error"
          lowContrast
          title="Label failed"
          subtitle={labelStatus.error}
        />
      )}
      {labelStatus.success && (
        <InlineNotification
          kind="success"
          lowContrast
          title="Label saved"
          subtitle={labelStatus.success}
        />
      )}
    </div>
  )
}

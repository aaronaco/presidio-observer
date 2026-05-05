import { useState } from 'preact/hooks'
import {
  Accordion,
  AccordionItem,
  Button,
  InlineNotification,
  NumberInput,
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
import { SectionHelp } from './SectionHelp'
import { formatDate, formatList, formatNumber } from '../lib/formatters'
import {
  entityName,
  eventEntityCount,
  eventEntityTypes,
  flagKind,
  missedEntityTypeOptions,
  sortEntities,
} from '../lib/events'

function labelTagKind(label) {
  if (label === 'missed') {
    return 'purple'
  }
  if (label === 'false_positive') {
    return 'orange'
  }

  return 'green'
}

function formatLabel(label) {
  return label.replace('_', ' ')
}

export function EventDetailPanel({
  event,
  eventLabels,
  labelStatus,
  onClose,
  onRemoveLabel,
  onSubmitLabel,
}) {
  const entityTypes = event ? eventEntityTypes(event) : []
  const primaryEntity = event?.entities?.[0] || null
  const primaryEntityType = primaryEntity?.type || entityTypes[0] || 'UNKNOWN'
  const missedOptions = event ? missedEntityTypeOptions(event) : []
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
                    eventLabels={eventLabels}
                    labelStatus={labelStatus}
                    missedOptions={missedOptions}
                    onRemoveLabel={onRemoveLabel}
                    primaryEntity={primaryEntity}
                    primaryEntityType={primaryEntityType}
                    onSubmitLabel={onSubmitLabel}
                    key={event.id}
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
      <DetailItem
        label={(
          <span className="detail-label-with-help">
            Confidence flag
            <SectionHelp align="bottom-start" title="Confidence flag">
              This flag is generated from analyzer metadata to highlight events worth
              reviewing. Human labels are saved separately and do not change it.
            </SectionHelp>
          </span>
        )}
        value={event.flag || 'n/a'}
      />
      <DetailItem label="Language" value={event.language || 'n/a'} />
      <DetailItem label="Latency" value={`${formatNumber(event.latency_ms, 1)} ms`} />
      <DetailItem label="Has PII" value={event.has_pii ? 'Yes' : 'No'} />
      <DetailItem label="Entity count" value={eventEntityCount(event)} />
      <DetailItem label="Requested entities" value={formatList(event.requested_entities)} />
      <DetailItem label="Score threshold" value={event.score_threshold ?? 'n/a'} />
      <DetailItem label="Allow-list count" value={event.allow_list_count ?? 'n/a'} />
      <DetailItem label="NLP engine" value={event.nlp_engine || 'n/a'} />
      <DetailItem label="Context enhancer" value={event.context_enhancer || 'n/a'} />
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

function EvaluationControls({
  eventLabels,
  labelStatus,
  missedOptions,
  onRemoveLabel,
  primaryEntity,
  primaryEntityType,
  onSubmitLabel,
}) {
  const [missedEntityType, setMissedEntityType] = useState(missedOptions[0] || 'EMAIL_ADDRESS')
  const [missedCount, setMissedCount] = useState(1)

  function updateMissedCount(value) {
    const nextCount = Number.parseInt(value, 10)
    setMissedCount(Number.isFinite(nextCount) && nextCount > 0 ? nextCount : 1)
  }

  return (
    <div className="evaluation-panel">
      <p>
        Label the primary detected entity for this event. When offsets are available,
        the label is saved against that entity span for evaluation metrics.
      </p>
      <p>
        Labels do not change the analyzer confidence flag. Missed entities use a
        separate type-and-count report because they are not present in analyzer results.
      </p>
      <div className="evaluation-actions">
        <Button
          kind="primary"
          disabled={labelStatus.loading}
          onClick={() => onSubmitLabel(
            'correct',
            primaryEntityType,
            1,
            primaryEntity?.start ?? null,
            primaryEntity?.end ?? null,
          )}
        >
          Correct
        </Button>
        <Button
          kind="secondary"
          disabled={labelStatus.loading}
          onClick={() => onSubmitLabel(
            'false_positive',
            primaryEntityType,
            1,
            primaryEntity?.start ?? null,
            primaryEntity?.end ?? null,
          )}
        >
          False positive
        </Button>
      </div>
      <div className="missed-entity-form">
        <h3>
          Report missed entity
          <SectionHelp align="bottom-start" title="Reported misses">
            Missed entities are not returned by the analyzer, so Observer only records
            the entity type and count. It does not store the missed text, value, or span.
          </SectionHelp>
        </h3>
        <p>No raw text, missed value, or span is stored.</p>
        <div className="missed-entity-fields">
          <Select
            id="missed-entity-type"
            size="sm"
            labelText="Entity type"
            value={missedEntityType}
            onChange={(event) => setMissedEntityType(event.target.value)}
          >
            {missedOptions.map((entityType) => (
              <SelectItem key={entityType} value={entityType} text={entityType} />
            ))}
          </Select>
          <NumberInput
            id="missed-entity-count"
            size="sm"
            label="Count"
            min={1}
            step={1}
            value={missedCount}
            onChange={(_, { value }) => updateMissedCount(value)}
          />
          <Button
            kind="tertiary"
            size="sm"
            disabled={labelStatus.loading}
            onClick={() => onSubmitLabel('missed', missedEntityType, missedCount, null, null)}
          >
            Report missed
          </Button>
        </div>
      </div>
      <EventLabelHistory
        eventLabels={eventLabels}
        labelStatus={labelStatus}
        onRemoveLabel={onRemoveLabel}
      />
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

function EventLabelHistory({ eventLabels, labelStatus, onRemoveLabel }) {
  if (eventLabels.loading) {
    return <p className="empty-state">Loading saved labels...</p>
  }

  if (eventLabels.error) {
    return (
      <InlineNotification
        kind="error"
        lowContrast
        title="Could not load labels"
        subtitle={eventLabels.error}
      />
    )
  }

  if (!eventLabels.items.length) {
    return <p className="empty-state">No labels saved for this event yet.</p>
  }

  return (
    <div className="label-history">
      <h3>Saved labels</h3>
      <div className="label-history-list">
        {eventLabels.items.map((item) => (
          <div className="label-history-row" key={item.id}>
            <Tag type={labelTagKind(item.label)}>{formatLabel(item.label)}</Tag>
            <span>{item.entity_type || 'UNKNOWN'}</span>
            <span>{formatLabelSpan(item)}</span>
            <span>Count {item.count || 1}</span>
            <time dateTime={item.created_at}>{formatDate(item.created_at)}</time>
            <Button
              kind="danger--ghost"
              size="sm"
              disabled={labelStatus.loading}
              onClick={() => onRemoveLabel(item.id)}
            >
              Remove label
            </Button>
          </div>
        ))}
      </div>
    </div>
  )
}

function formatLabelSpan(item) {
  if (item.entity_start === null || item.entity_start === undefined) {
    return 'No span'
  }
  if (item.entity_end === null || item.entity_end === undefined) {
    return 'No span'
  }

  return `Span ${item.entity_start}-${item.entity_end}`
}

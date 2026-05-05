const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

export async function fetchJson(path, options) {
  const response = await fetch(`${API_BASE}${path}`, options)
  if (!response.ok) {
    throw new Error(`${path} returned ${response.status}`)
  }
  return response.json()
}

function buildDashboardQuery(filters = {}) {
  const params = new URLSearchParams()

  if (filters.since) {
    params.set('since', filters.since)
  }
  if (filters.language) {
    params.set('language', filters.language)
  }
  if (filters.entityType) {
    params.set('entity_type', filters.entityType)
  }
  if (filters.flag) {
    params.set('flag', filters.flag)
  }

  const query = params.toString()
  return query
}

export async function fetchDashboard(filters = {}) {
  const query = buildDashboardQuery(filters)
  const statsPath = query ? `/stats?${query}` : '/stats'
  const eventsPath = query ? `/events/recent?limit=12&${query}` : '/events/recent?limit=12'
  const evaluationPath = query ? `/evaluation/summary?${query}` : '/evaluation/summary'

  const [stats, events, evaluation] = await Promise.all([
    fetchJson(statsPath),
    fetchJson(eventsPath),
    fetchJson(evaluationPath),
  ])

  return { stats, events, evaluation }
}

export function fetchEventLabels(eventId) {
  return fetchJson(`/events/${eventId}/labels`)
}

export function submitEventLabel(eventId, payload) {
  return fetchJson(`/events/${eventId}/label`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })
}

export function removeEventLabel(eventId, labelId) {
  return fetchJson(`/events/${eventId}/labels/${labelId}`, {
    method: 'DELETE',
  })
}

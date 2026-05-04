const API_BASE = import.meta.env.VITE_API_BASE_URL || '/api'

export async function fetchJson(path, options) {
  const response = await fetch(`${API_BASE}${path}`, options)
  if (!response.ok) {
    throw new Error(`${path} returned ${response.status}`)
  }
  return response.json()
}

export async function fetchDashboard() {
  const [stats, events, evaluation] = await Promise.all([
    fetchJson('/stats'),
    fetchJson('/events/recent?limit=12'),
    fetchJson('/evaluation/summary'),
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

import type {
  AssistantRequest,
  AssistantResponse,
  Incident,
  Service,
  TimelineEvent,
} from './types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? ''

export class ApiError extends Error {
  readonly status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

async function request<T>(
  path: string,
  signal?: AbortSignal,
  init?: RequestInit,
): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, signal })

  if (!response.ok) {
    let message = `Request failed with status ${response.status}`

    try {
      const body = (await response.json()) as { detail?: string }
      if (body.detail) message = body.detail
    } catch {
      // Keep the status-based fallback for non-JSON errors.
    }

    throw new ApiError(message, response.status)
  }

  return response.json() as Promise<T>
}

export const incidentApi = {
  list(signal?: AbortSignal): Promise<Incident[]> {
    return request('/api/incidents', signal)
  },

  get(incidentId: string, signal?: AbortSignal): Promise<Incident> {
    return request(`/api/incidents/${encodeURIComponent(incidentId)}`, signal)
  },

  services(incidentId: string, signal?: AbortSignal): Promise<Service[]> {
    return request(`/api/incidents/${encodeURIComponent(incidentId)}/services`, signal)
  },

  timeline(incidentId: string, signal?: AbortSignal): Promise<TimelineEvent[]> {
    return request(`/api/incidents/${encodeURIComponent(incidentId)}/timeline`, signal)
  },

  askAssistant(
    incidentId: string,
    body: AssistantRequest,
    signal?: AbortSignal,
  ): Promise<AssistantResponse> {
    return request(`/api/incidents/${encodeURIComponent(incidentId)}/assistant`, signal, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    })
  },
}
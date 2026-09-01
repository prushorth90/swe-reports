export type IncidentSeverity = 'SEV1' | 'SEV2' | 'SEV3'
export type IncidentStatus = 'investigating' | 'identified' | 'monitoring' | 'resolved'
export type ServiceHealth = 'healthy' | 'degraded' | 'outage'
export type TimelineEventType = 'detected' | 'update' | 'mitigation' | 'resolved'

export interface Incident {
  id: string
  title: string
  severity: IncidentSeverity
  status: IncidentStatus
  start_time: string
  affected_services: string[]
  summary: string
}

export interface Service {
  name: string
  health_status: ServiceHealth
  p95_latency_ms: number
  error_rate_percent: number
  cpu_percent: number
}

export interface TimelineEvent {
  timestamp: string
  event_type: TimelineEventType
  message: string
}

export type AssistantRole = 'user' | 'assistant'

export interface AssistantSource {
  title: string
  excerpt: string
  url?: string
  service?: string
  timestamp?: string
}

export interface AssistantMessageMetadata {
  model?: string
  total_latency_ms?: number
  retrieval_latency_ms?: number
  cache_hit?: boolean
  route?: string
  sources?: AssistantSource[]
}

export interface AssistantMessage {
  id: string
  role: AssistantRole
  content: string
  created_at: string
  metadata?: AssistantMessageMetadata
}

export interface AssistantRequest {
  message: string
  history: Array<Pick<AssistantMessage, 'role' | 'content'>>
}

export interface AssistantResponse {
  message: string
  metadata?: AssistantMessageMetadata
}
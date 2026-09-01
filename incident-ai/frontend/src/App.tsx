import { useEffect, useState } from 'react'
import { incidentApi } from './api'
import type { Incident, Service, TimelineEvent } from './types'
import './App.css'

const dateTimeFormatter = new Intl.DateTimeFormat('en-US', {
  month: 'short', day: 'numeric', year: 'numeric', hour: 'numeric',
  minute: '2-digit', timeZoneName: 'short',
})

const shortTimeFormatter = new Intl.DateTimeFormat('en-US', {
  month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit',
})

function formatDate(value: string, short = false) {
  return (short ? shortTimeFormatter : dateTimeFormatter).format(new Date(value))
}

function formatLabel(value: string) {
  return value.replaceAll('_', ' ')
}

function LoadingPanel({ label }: { label: string }) {
  return <div className="loading-panel" role="status"><span className="loading-indicator" aria-hidden="true" />{label}</div>
}

function ErrorPanel({ message, onRetry }: { message: string; onRetry: () => void }) {
  return (
    <div className="error-panel" role="alert">
      <div><strong>Unable to load incident data</strong><p>{message}</p></div>
      <button type="button" onClick={onRetry}>Retry</button>
    </div>
  )
}

function IncidentNavItem({ incident, selected, onSelect }: {
  incident: Incident
  selected: boolean
  onSelect: () => void
}) {
  return (
    <li>
      <button type="button" className={`incident-nav-item${selected ? ' is-selected' : ''}`} onClick={onSelect} aria-current={selected ? 'page' : undefined}>
        <span className={`severity severity-${incident.severity.toLowerCase()}`}>{incident.severity}</span>
        <strong>{incident.title}</strong>
        <span className={`status status-${incident.status}`}>{formatLabel(incident.status)}</span>
      </button>
    </li>
  )
}

function ServiceCard({ service }: { service: Service }) {
  return (
    <article className={`service-card service-${service.health_status}`}>
      <header>
        <div><span className="eyebrow">Service</span><h3>{service.name}</h3></div>
        <span className={`health health-${service.health_status}`}><span aria-hidden="true" />{service.health_status}</span>
      </header>
      <dl className="metrics">
        <div><dt>P95 latency</dt><dd>{service.p95_latency_ms.toLocaleString()} <small>ms</small></dd></div>
        <div><dt>Error rate</dt><dd>{service.error_rate_percent.toFixed(1)}<small>%</small></dd></div>
        <div><dt>CPU</dt><dd>{service.cpu_percent.toFixed(1)}<small>%</small></dd></div>
      </dl>
    </article>
  )
}

function IncidentTimeline({ events }: { events: TimelineEvent[] }) {
  return (
    <ol className="timeline">
      {events.map((event) => (
        <li key={`${event.timestamp}-${event.event_type}`}>
          <span className={`timeline-marker marker-${event.event_type}`} aria-hidden="true" />
          <div className="timeline-event">
            <div><span className="event-type">{event.event_type}</span><time dateTime={event.timestamp}>{formatDate(event.timestamp, true)}</time></div>
            <p>{event.message}</p>
          </div>
        </li>
      ))}
    </ol>
  )
}

function IncidentDetail({ incident, services, timeline }: {
  incident: Incident
  services: Service[]
  timeline: TimelineEvent[]
}) {
  return (
    <>
      <header className="incident-header">
        <div className="incident-heading">
          <div className="incident-badges">
            <span className={`severity severity-${incident.severity.toLowerCase()}`}>{incident.severity}</span>
            <span className={`status status-${incident.status}`}>{formatLabel(incident.status)}</span>
          </div>
          <h1>{incident.title}</h1>
          <p>{incident.summary}</p>
        </div>
        <dl className="incident-meta">
          <div><dt>Started</dt><dd><time dateTime={incident.start_time}>{formatDate(incident.start_time)}</time></dd></div>
          <div><dt>Incident ID</dt><dd><code>{incident.id}</code></dd></div>
        </dl>
      </header>

      <section className="affected-services" aria-labelledby="affected-heading">
        <h2 id="affected-heading">Affected services</h2>
        <div>{incident.affected_services.map((service) => <span key={service}>{service}</span>)}</div>
      </section>

      <section className="dashboard-section" aria-labelledby="health-heading">
        <div className="section-heading">
          <div><span className="section-index">01</span><h2 id="health-heading">Service health</h2></div>
          <span>{services.length} services reporting</span>
        </div>
        <div className="service-grid">{services.map((service) => <ServiceCard key={service.name} service={service} />)}</div>
      </section>

      <section className="dashboard-section timeline-section" aria-labelledby="timeline-heading">
        <div className="section-heading">
          <div><span className="section-index">02</span><h2 id="timeline-heading">Incident timeline</h2></div>
          <span>{timeline.length} recorded events</span>
        </div>
        {timeline.length ? <IncidentTimeline events={timeline} /> : <p className="empty-inline">No timeline events have been recorded.</p>}
      </section>
    </>
  )
}

function App() {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [incident, setIncident] = useState<Incident | null>(null)
  const [services, setServices] = useState<Service[]>([])
  const [timeline, setTimeline] = useState<TimelineEvent[]>([])
  const [listLoading, setListLoading] = useState(true)
  const [detailLoading, setDetailLoading] = useState(false)
  const [listError, setListError] = useState<string | null>(null)
  const [detailError, setDetailError] = useState<string | null>(null)
  const [listRequest, setListRequest] = useState(0)
  const [detailRequest, setDetailRequest] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    setListLoading(true)
    setListError(null)
    incidentApi.list(controller.signal)
      .then((data) => {
        setIncidents(data)
        setSelectedId((current) => current ?? data[0]?.id ?? null)
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setListError(error instanceof Error ? error.message : 'An unexpected error occurred.')
      })
      .finally(() => { if (!controller.signal.aborted) setListLoading(false) })
    return () => controller.abort()
  }, [listRequest])

  useEffect(() => {
    if (!selectedId) {
      setIncident(null)
      setServices([])
      setTimeline([])
      return
    }

    const controller = new AbortController()
    setDetailLoading(true)
    setDetailError(null)
    Promise.all([
      incidentApi.get(selectedId, controller.signal),
      incidentApi.services(selectedId, controller.signal),
      incidentApi.timeline(selectedId, controller.signal),
    ])
      .then(([nextIncident, nextServices, nextTimeline]) => {
        setIncident(nextIncident)
        setServices(nextServices)
        setTimeline(nextTimeline)
      })
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === 'AbortError') return
        setDetailError(error instanceof Error ? error.message : 'An unexpected error occurred.')
      })
      .finally(() => { if (!controller.signal.aborted) setDetailLoading(false) })
    return () => controller.abort()
  }, [selectedId, detailRequest])

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <header className="brand">
          <span className="brand-mark" aria-hidden="true"><i /><i /><i /></span>
          <div><strong>Incident AI</strong><span>Response console</span></div>
        </header>
        <div className="sidebar-heading"><h2>Active incidents</h2><span>{incidents.length}</span></div>
        <nav aria-label="Incidents">
          {listLoading ? <LoadingPanel label="Loading incidents" /> : null}
          {listError ? <ErrorPanel message={listError} onRetry={() => setListRequest((value) => value + 1)} /> : null}
          {!listLoading && !listError && !incidents.length ? <p className="sidebar-empty">No incidents reported.</p> : null}
          <ul className="incident-list">
            {incidents.map((item) => (
              <IncidentNavItem key={item.id} incident={item} selected={item.id === selectedId} onSelect={() => setSelectedId(item.id)} />
            ))}
          </ul>
        </nav>
        <footer className="sidebar-footer"><span className="live-dot" aria-hidden="true" /><span>Live backend connection</span></footer>
      </aside>

      <main className="main-content">
        {detailLoading ? <LoadingPanel label="Loading incident details" /> : null}
        {!detailLoading && detailError ? <ErrorPanel message={detailError} onRetry={() => setDetailRequest((value) => value + 1)} /> : null}
        {!detailLoading && !detailError && incident ? <IncidentDetail incident={incident} services={services} timeline={timeline} /> : null}
        {!detailLoading && !detailError && !incident ? (
          <div className="empty-state">
            <span aria-hidden="true">--</span>
            <h1>No incident selected</h1>
            <p>Select an incident from the sidebar to inspect its service health and response timeline.</p>
          </div>
        ) : null}
      </main>
    </div>
  )
}

export default App

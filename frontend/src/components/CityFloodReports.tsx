import { useEffect, useState } from 'react'

type Report = {
  location: string
  reported_impact: string
  reported_period: string
  reported_event_date?: string | null
  source_url: string
}

const reportedDateFormat = new Intl.DateTimeFormat('en-GB', {
  day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC',
})

function isIsoDate(value: unknown): value is string {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false
  const date = new Date(value)
  return Number.isFinite(date.getTime()) && date.toISOString().slice(0, 10) === value
}

function valid(value: unknown): value is { records: Report[] } {
  if (!value || typeof value !== 'object') return false
  const records = (value as { records?: unknown }).records
  return Array.isArray(records) && records.every((item: unknown) => {
    if (!item || typeof item !== 'object') return false
    const row = item as Record<string, unknown>
    return ['location', 'reported_impact', 'reported_period', 'source_url']
      .every((key) => typeof row[key] === 'string') &&
      typeof row.source_url === 'string' &&
      row.source_url.startsWith('https://www.deccanherald.com/') &&
      row.approved_for_training === false &&
      (row.reported_event_date == null || isIsoDate(row.reported_event_date))
  })
}

export default function CityFloodReports() {
  const [reports, setReports] = useState<Report[] | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      try {
        const response = await fetch(
          `${import.meta.env.BASE_URL}data/ballari_city_flood_candidates.json`,
          { signal: controller.signal },
        )
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const result: unknown = await response.json()
        if (!valid(result)) throw new Error('Unexpected evidence data.')
        if (!controller.signal.aborted) setReports(result.records)
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : 'Unable to load reports.')
        }
      }
    }
    void load()
    return () => controller.abort()
  }, [])

  return (
    <section className="section-block" id="city-flood-reports">
      <div className="section-heading">
        <div>
          <div className="eyebrow">REPORTED CITY FLOOD EVIDENCE</div>
          <h2>Reported waterlogging locations</h2>
        </div>
      </div>
      <div className="panel-card">
        <p>
          The source reports three affected locations in Ballari during the
          7 June 2026 rainfall event. Exact timing and coordinates for each
          location still require verification.
        </p>
        <p className="small-note">
          These records are not approved training labels or predicted flood locations.
        </p>
        {error && <p role="alert">Could not load reports: {error}</p>}
        {!reports && !error && <p role="status">Loading reports…</p>}
        {reports && (
          <div style={{ overflowX: 'auto' }}>
            <table style={{
              width: '100%', minWidth: 600,
              borderCollapse: 'collapse', textAlign: 'left',
            }}>
              <caption style={{ textAlign: 'left', padding: '12px 0' }}>
                {reports.length} reported locations awaiting verification
              </caption>
              <thead>
                <tr>
                  {['Location', 'Reported impact', 'Reported event date', 'Source'].map((label) =>
                    <th key={label} scope="col" style={{ padding: 12 }}>{label}</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {reports.map((report) => (
                  <tr key={report.location} style={{ borderTop: '1px solid #e2e8f0' }}>
                    <th scope="row" style={{ padding: 12 }}>{report.location}</th>
                    <td style={{ padding: 12 }}>{report.reported_impact}</td>
                    <td style={{ padding: 12 }}>
                      {report.reported_event_date ? (
                        <time dateTime={report.reported_event_date}>
                          {reportedDateFormat.format(new Date(report.reported_event_date))}
                        </time>
                      ) : report.reported_period}
                    </td>
                    <td style={{ padding: 12 }}>
                      <a href={report.source_url} target="_blank" rel="noopener noreferrer">
                        Read report
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </section>
  )
}

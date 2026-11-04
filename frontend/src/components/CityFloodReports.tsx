import { useEffect, useState } from 'react'

type Report = {
  location: string
  reported_impact: string
  reported_period: string
  source_url: string
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
      row.approved_for_training === false
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
          News reports identify these locations for further investigation.
          Exact incident dates and coordinates require verification.
          Multiple locations may describe the same rainfall event.
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
                  {['Location', 'Reported impact', 'Period', 'Source'].map((label) =>
                    <th key={label} scope="col" style={{ padding: 12 }}>{label}</th>
                  )}
                </tr>
              </thead>
              <tbody>
                {reports.map((report) => (
                  <tr key={report.location} style={{ borderTop: '1px solid #e2e8f0' }}>
                    <th scope="row" style={{ padding: 12 }}>{report.location}</th>
                    <td style={{ padding: 12 }}>{report.reported_impact}</td>
                    <td style={{ padding: 12 }}>{report.reported_period}</td>
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

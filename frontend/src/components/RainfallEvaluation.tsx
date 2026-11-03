import { useEffect, useState } from 'react'
import {
  CartesianGrid, Legend, Line, LineChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'

type Metric = {
  method: string
  days: number
  mae: number
  rmse: number
  bias: number
  upper_tail_days: number
  upper_tail_mae: number | null
}

type DailyRecord = {
  date: string
  precipitation_mm_per_day: number
  random_forest: number
  training_monthly_mean: number
}

type Period = {
  year: number
  split: string
  days: number
  start_date: string
  end_date: string
  metrics: Metric[]
  records: DailyRecord[]
}

type Evaluation = {
  schema_version: number
  status: string
  unit: string
  decision: string
  note: string
  upper_tail_threshold_mm_day: number
  periods: Period[]
}

const labels: Record<string, string> = {
  zero: 'Zero rainfall',
  training_monthly_mean: 'Training monthly mean',
  persistence: 'Previous day',
  previous_7day_mean: 'Previous 7-day mean',
  random_forest: 'Random Forest',
}

const periods: Record<number, string> = {
  2003: '2003 — Validation',
  2004: '2004 — Test',
  2024: '2024 — Later-period evaluation',
}

function format(value: number | null) {
  return value !== null && Number.isFinite(value)
    ? value.toFixed(4)
    : '—'
}

export default function RainfallEvaluation({ api }: { api: string }) {
  const [data, setData] = useState<Evaluation | null>(null)
  const [year, setYear] = useState(2003)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()

    async function load() {
      try {
        const response = await fetch(
          `${api}/api/v1/rainfall/model-evaluation`,
          { signal: controller.signal },
        )
        if (!response.ok) {
          throw new Error(`Evaluation API returned HTTP ${response.status}.`)
        }
        const result: Evaluation = await response.json()
        if (
          result.schema_version !== 1 ||
          result.status !== 'experimental_retrospective_only' ||
          !Array.isArray(result.periods) ||
          result.periods.length !== 3 ||
          !result.periods.every((period) =>
            Array.isArray(period.metrics) &&
            Array.isArray(period.records) &&
            period.records.length === period.days
          )
        ) {
          throw new Error('Unexpected evaluation response.')
        }
        if (!controller.signal.aborted) setData(result)
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : 'Unable to load evaluation.')
        }
      }
    }

    void load()
    return () => controller.abort()
  }, [api, attempt])

  const selected = data?.periods.find((period) => period.year === year)
  const metrics = selected
    ? [...selected.metrics].sort((a, b) => a.mae - b.mae)
    : []

  return (
    <section className="section-block" id="rainfall-evaluation">
      <div className="section-heading">
        <div>
          <div className="eyebrow">HISTORICAL MODEL EVALUATION</div>
          <h2>Rainfall experiment</h2>
        </div>
        {data && (
          <label>
            Evaluation period{' '}
            <select
              value={year}
              onChange={(event) => setYear(Number(event.target.value))}
              style={{ padding: '8px', borderRadius: '6px' }}
            >
              {data.periods.map((period) => (
                <option key={period.year} value={period.year}>
                  {periods[period.year] ?? period.year}
                </option>
              ))}
            </select>
          </label>
        )}
      </div>

      <div className="panel-card">
        <strong>Experimental retrospective results</strong>
        <p>Not a live weather forecast or a flood prediction.</p>

        {error ? (
          <div role="alert">
            <p>{error}</p>
            <button
              type="button"
              className="map-control-button"
              onClick={() => {
                setError('')
                setData(null)
                setAttempt((value) => value + 1)
              }}
            >
              Retry evaluation
            </button>
          </div>
        ) : !data ? (
          <p role="status">Loading evaluation results…</p>
        ) : selected ? (
          <>
            <p><strong>{data.decision}</strong></p>
            <p>
              {selected.start_date} to {selected.end_date}
              {' · '}{selected.days} evaluated days
              {' · '}Model trained on 2001–2002.
            </p>
            {year === 2024 && (
              <p>
                January 1–7 are excluded because preceding observations
                are unavailable. The dataset has no observations for 2005–2023.
              </p>
            )}

            <div
              style={{ overflowX: 'auto' }}
              role="region"
              aria-label="Rainfall evaluation metrics"
              tabIndex={0}
            >
              <table style={{
                width: '100%', minWidth: '650px',
                borderCollapse: 'collapse', textAlign: 'left',
              }}>
                <caption style={{ textAlign: 'left', padding: '12px 0' }}>
                  Errors in {data.unit}; lower MAE and RMSE are better.
                  Positive bias means overprediction.
                </caption>
                <thead>
                  <tr>
                    {['Method', 'MAE', 'RMSE', 'Bias', 'Upper-tail MAE'].map((title) => (
                      <th key={title} scope="col" style={{ padding: '10px' }}>
                        {title}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {metrics.map((metric) => (
                    <tr key={metric.method} style={{
                      borderTop: '1px solid #cbd5e1',
                      fontWeight: metric.method === 'random_forest' ? 700 : 400,
                    }}>
                      <th scope="row" style={{ padding: '10px' }}>
                        {labels[metric.method] ?? metric.method}
                      </th>
                      <td style={{ padding: '10px' }}>{format(metric.mae)}</td>
                      <td style={{ padding: '10px' }}>{format(metric.rmse)}</td>
                      <td style={{ padding: '10px' }}>{format(metric.bias)}</td>
                      <td style={{ padding: '10px' }}>{format(metric.upper_tail_mae)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <p className="small-note">
              Upper-tail diagnostic: observations ≥{' '}
              {format(data.upper_tail_threshold_mm_day)} mm/day
              {' '}({metrics[0]?.upper_tail_days ?? 0} days).
              This training-derived threshold is not an official warning category.
            </p>

            <h3>Observed rainfall and historical estimates</h3>
            <p className="small-note">
              Chart compares satellite observations, Random Forest estimates
              and the training monthly mean baseline.
            </p>
            <div style={{ width: '100%', height: 340, minWidth: 0 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart
                  data={selected.records}
                  margin={{ top: 12, right: 20, left: 0, bottom: 12 }}
                  accessibilityLayer
                >
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="date"
                    minTickGap={45}
                    tickFormatter={(value: string) => value.slice(5)}
                  />
                  <YAxis width={55} />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="linear"
                    dataKey="precipitation_mm_per_day"
                    name="Observed (mm/day)"
                    stroke="#0284c7"
                    dot={false}
                    isAnimationActive={false}
                  />
                  <Line
                    type="linear"
                    dataKey="random_forest"
                    name="Random Forest (mm/day)"
                    stroke="#9333ea"
                    dot={false}
                    isAnimationActive={false}
                  />
                  <Line
                    type="linear"
                    dataKey="training_monthly_mean"
                    name="Training monthly mean (mm/day)"
                    stroke="#b45309"
                    strokeDasharray="5 4"
                    dot={false}
                    isAnimationActive={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="small-note">{data.note}</p>
            <p className="small-note">
              Each estimate uses actual preceding observations.
              These are not whole-year forecasts made at the start of the year.
            </p>
          </>
        ) : (
          <p role="alert">The selected evaluation period is unavailable.</p>
        )}
      </div>
    </section>
  )
}

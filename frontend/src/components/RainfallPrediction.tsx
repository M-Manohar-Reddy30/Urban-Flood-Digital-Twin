import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'

type Result = {
  status: string
  target_date: string
  prediction_mm_per_day: number
  inputs: {
    target_date: string
    previous_7_days_mm_per_day: number[]
  }
  limitations: string[]
}

function valid(value: unknown): value is Result {
  if (!value || typeof value !== 'object') return false
  const result = value as Result
  return (
    result.status === 'experimental_user_supplied_rainfall_estimate' &&
    typeof result.target_date === 'string' &&
    typeof result.prediction_mm_per_day === 'number' &&
    Number.isFinite(result.prediction_mm_per_day) &&
    result.prediction_mm_per_day >= 0 &&
    !!result.inputs &&
    result.inputs.target_date === result.target_date &&
    Array.isArray(result.inputs.previous_7_days_mm_per_day) &&
    result.inputs.previous_7_days_mm_per_day.length === 7 &&
    result.inputs.previous_7_days_mm_per_day.every(
      (item) => typeof item === 'number' && Number.isFinite(item) &&
        item >= 0 && item <= 1000,
    ) &&
    Array.isArray(result.limitations) &&
    result.limitations.every((item) => typeof item === 'string')
  )
}

function precedingDate(target: string, days: number) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(target)) return `D-${days}`
  const date = new Date(`${target}T00:00:00Z`)
  if (!Number.isFinite(date.getTime())) return `D-${days}`
  date.setUTCDate(date.getUTCDate() - days)
  return date.toISOString().slice(0, 10)
}

export default function RainfallPrediction({ api }: { api: string }) {
  const [target, setTarget] = useState('')
  const [days, setDays] = useState<string[]>(Array(7).fill(''))
  const [result, setResult] = useState<Result | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const active = useRef<AbortController | null>(null)

  useEffect(() => () => active.current?.abort(), [])

  async function estimate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const rainfall = days.map(Number)
    if (
      !/^\d{4}-\d{2}-\d{2}$/.test(target) ||
      days.some((item) => item.trim() === '') ||
      rainfall.some((item) => !Number.isFinite(item) || item < 0 || item > 1000)
    ) {
      setError('Choose a target date and enter all seven rainfall values.')
      return
    }

    active.current?.abort()
    const controller = new AbortController()
    active.current = controller
    setLoading(true)
    setError('')
    setResult(null)

    try {
      const response = await fetch(`${api}/api/v1/rainfall/predict`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        signal: controller.signal,
        body: JSON.stringify({
          target_date: target,
          previous_7_days_mm_per_day: rainfall,
        }),
      })
      if (!response.ok) {
        throw new Error(`Rainfall request failed (HTTP ${response.status}).`)
      }
      const payload: unknown = await response.json()
      if (!valid(payload)) throw new Error('Unexpected rainfall response.')
      if (
        payload.target_date !== target ||
        payload.inputs.previous_7_days_mm_per_day.some(
          (item, index) => item !== rainfall[index],
        )
      ) throw new Error('Response inputs do not match the request.')

      if (!controller.signal.aborted) setResult(payload)
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(err instanceof Error ? err.message : 'Unable to estimate rainfall.')
      }
    } finally {
      if (!controller.signal.aborted) setLoading(false)
    }
  }

  return (
    <section className="section-block" id="rainfall-prediction">
      <div className="section-heading">
        <div>
          <div className="eyebrow">EXPERIMENTAL AI ESTIMATE</div>
          <h2>Estimate one day of rainfall</h2>
        </div>
      </div>
      <div className="panel-card">
        <p>
          Enter a target date and the preceding seven daily rainfall values,
          oldest first. The saved Random Forest uses these inputs to estimate
          the target day’s rainfall rate.
        </p>
        <p className="small-note">
          Use municipal daily-mean rainfall rates in mm/day consistent with
          the training data. Accumulated storm depth is a different input.
          No live weather data are fetched.
        </p>
        <p>
          <strong>
            Experimental model: it did not beat the zero-rainfall baseline
            on MAE in any evaluated period.
          </strong>
          {' '}This feature does not predict flooding.
        </p>

        <form onSubmit={estimate}>
          <fieldset disabled={loading} style={{ border: 0, padding: 0, margin: 0 }}>
            <legend>Rainfall history</legend>
            <label style={{ display: 'block', margin: '12px 0' }}>
              Target date
              <input
                type="date" required value={target}
                min="1900-01-08" max="2100-12-31"
                onChange={(event) => {
                  setTarget(event.target.value)
                  setResult(null)
                  setError('')
                }}
                style={{ display: 'block', padding: 10, marginTop: 6 }}
              />
            </label>
            <div style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))',
              gap: 12, margin: '16px 0',
            }}>
              {days.map((value, index) => (
                <label key={index}>
                  {precedingDate(target, 7 - index)}
                  {' '}(D-{7 - index})
                  <input
                    type="number" min="0" max="1000" step="any" required
                    aria-label={`Rainfall ${7 - index} days before target, mm/day`}
                    placeholder="mm/day"
                    value={value}
                    onChange={(event) => {
                      setDays((current) => current.map(
                        (item, i) => i === index ? event.target.value : item,
                      ))
                      setResult(null)
                      setError('')
                    }}
                    style={{
                      display: 'block', width: '100%', boxSizing: 'border-box',
                      padding: 10, marginTop: 6,
                    }}
                  />
                </label>
              ))}
            </div>
            <button type="submit" className="map-control-button">
              {loading ? 'Estimating…' : 'Estimate rainfall'}
            </button>
          </fieldset>
        </form>

        {loading && <p role="status">Running the saved rainfall model…</p>}
        {error && <p role="alert">{error}</p>}
        {result && (
          <div role="status" style={{ marginTop: 20 }}>
            <p>
              Experimental estimate for <strong>{result.target_date}</strong>:
              {' '}<strong>{result.prediction_mm_per_day.toFixed(4)} mm/day</strong>
            </p>
            <p className="small-note">
              Submitted history, oldest first:
              {' '}{result.inputs.previous_7_days_mm_per_day.join(', ')} mm/day.
            </p>
            <details>
              <summary>Model assumptions and limitations</summary>
              <ul>
                {result.limitations.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </details>
          </div>
        )}
      </div>
    </section>
  )
}

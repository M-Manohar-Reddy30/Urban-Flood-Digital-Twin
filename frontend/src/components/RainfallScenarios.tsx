import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'

type Inputs = {
  rainfall_depth_mm: number
  duration_hours: number
  runoff_fraction: number
}

type Result = {
  status: string
  inputs: Inputs
  coverage: {
    sampled_area_km2: number
    sampled_cell_count: number
  }
  results: {
    average_rainfall_intensity_mm_per_hour: number
    rainfall_volume_m3: number
    estimated_runoff_volume_m3: number
    remaining_water_volume_m3: number
  }
}

const fields: {
  key: keyof Inputs
  label: string
  min: number
  max: number
  step: string
}[] = [
  {
    key: 'rainfall_depth_mm',
    label: 'Total rainfall depth (mm)',
    min: 0, max: 1000, step: 'any',
  },
  {
    key: 'duration_hours',
    label: 'Duration (hours)',
    min: 0.01, max: 168, step: 'any',
  },
  {
    key: 'runoff_fraction',
    label: 'Assumed runoff fraction (0–1)',
    min: 0, max: 1, step: 'any',
  },
]

const format = (value: number) =>
  value.toLocaleString('en-IN', { maximumFractionDigits: 2 })

function validResult(value: unknown): value is Result {
  if (!value || typeof value !== 'object') return false
  const result = value as Result
  return (
    result.status === 'exploratory_uncalibrated_scenario' &&
    !!result.inputs &&
    !!result.coverage &&
    !!result.results &&
    [
      result.inputs.rainfall_depth_mm,
      result.inputs.duration_hours,
      result.inputs.runoff_fraction,
      result.coverage.sampled_area_km2,
      result.coverage.sampled_cell_count,
      result.results.average_rainfall_intensity_mm_per_hour,
      result.results.rainfall_volume_m3,
      result.results.estimated_runoff_volume_m3,
      result.results.remaining_water_volume_m3,
    ].every((number) =>
      typeof number === 'number' && Number.isFinite(number) && number >= 0
    )
  )
}

export default function RainfallScenarios({ api }: { api: string }) {
  const [drafts, setDrafts] = useState([
    { rainfall_depth_mm: '50', duration_hours: '2', runoff_fraction: '0.5' },
    { rainfall_depth_mm: '100', duration_hours: '2', runoff_fraction: '0.5' },
  ])
  const [results, setResults] = useState<Result[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const active = useRef<AbortController | null>(null)

  useEffect(() => () => active.current?.abort(), [])

  function update(index: number, key: keyof Inputs, value: string) {
    setDrafts((current) =>
      current.map((draft, item) =>
        item === index ? { ...draft, [key]: value } : draft
      )
    )
    setResults(null)
    setError('')
  }

  async function compare(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    active.current?.abort()
    const controller = new AbortController()
    active.current = controller
    setLoading(true)
    setError('')
    setResults(null)

    try {
      const inputs = drafts.map((draft) => {
        for (const field of fields) {
          const value = Number(draft[field.key])
          if (
            draft[field.key].trim() === '' ||
            !Number.isFinite(value) ||
            value < field.min ||
            value > field.max
          ) {
            throw new Error(`Enter a valid value for ${field.label}.`)
          }
        }
        return {
          rainfall_depth_mm: Number(draft.rainfall_depth_mm),
          duration_hours: Number(draft.duration_hours),
          runoff_fraction: Number(draft.runoff_fraction),
        }
      })

      const compared = await Promise.all(inputs.map(async (input) => {
        const response = await fetch(`${api}/api/v1/scenarios/rainfall`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(input),
          signal: controller.signal,
        })
        if (!response.ok) {
          throw new Error(`Scenario request failed (HTTP ${response.status}).`)
        }
        const result: unknown = await response.json()
        if (!validResult(result)) {
          throw new Error('Unexpected scenario response.')
        }
        return result
      }))

      if (
        compared[0].coverage.sampled_area_km2 !==
        compared[1].coverage.sampled_area_km2
      ) {
        throw new Error('Scenarios have different area coverage.')
      }
      if (!controller.signal.aborted) setResults(compared)
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(err instanceof Error ? err.message : 'Unable to compare scenarios.')
      }
    } finally {
      if (!controller.signal.aborted) setLoading(false)
    }
  }

  const comparisonRows = results ? [
    ['Rainfall depth (mm)', ...results.map((item) => item.inputs.rainfall_depth_mm)],
    ['Duration (hours)', ...results.map((item) => item.inputs.duration_hours)],
    ['Assumed runoff fraction', ...results.map((item) => item.inputs.runoff_fraction)],
    ['Average intensity (mm/hour)', ...results.map((item) =>
      item.results.average_rainfall_intensity_mm_per_hour)],
    ['Rainfall volume (m³)', ...results.map((item) =>
      item.results.rainfall_volume_m3)],
    ['Estimated runoff volume (m³)', ...results.map((item) =>
      item.results.estimated_runoff_volume_m3)],
    ['Remaining water volume (m³)', ...results.map((item) =>
      item.results.remaining_water_volume_m3)],
  ] : []

  const difference = results
    ? results[1].results.estimated_runoff_volume_m3 -
      results[0].results.estimated_runoff_volume_m3
    : 0

  return (
    <section className="section-block" id="rainfall-scenarios">
      <div className="section-heading">
        <div>
          <div className="eyebrow">WHAT-IF EXPLORATION</div>
          <h2>Compare rainfall scenarios</h2>
        </div>
      </div>
      <div className="panel-card">
        <p>
          Explore how assumed rainfall and runoff fraction change water volumes
          over the sampled GIS area.
        </p>
        <p>
          <strong>Exploratory calculation — not a flood prediction.</strong>
          {' '}A runoff fraction of 0.5 assumes half the rainfall becomes runoff.
          The example values are hypothetical.
        </p>

        <form onSubmit={compare}>
          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
            gap: 20,
          }}>
            {drafts.map((draft, index) => (
              <fieldset
                key={index}
                disabled={loading}
                style={{
                  minWidth: 0, padding: 16,
                  border: '1px solid #cbd5e1', borderRadius: 10,
                }}
              >
                <legend>Scenario {index === 0 ? 'A' : 'B'}</legend>
                {fields.map((field) => (
                  <label
                    key={field.key}
                    style={{ display: 'block', marginBottom: 14 }}
                  >
                    {field.label}
                    <input
                      type="number"
                      required
                      min={field.min}
                      max={field.max}
                      step={field.step}
                      value={draft[field.key]}
                      onChange={(event) =>
                        update(index, field.key, event.target.value)}
                      style={{
                        display: 'block', width: '100%',
                        boxSizing: 'border-box', padding: 10,
                        marginTop: 6, borderRadius: 6,
                        border: '1px solid #94a3b8',
                      }}
                    />
                  </label>
                ))}
              </fieldset>
            ))}
          </div>
          <button
            type="submit"
            className="map-control-button"
            disabled={loading}
            style={{ marginTop: 16 }}
          >
            {loading ? 'Calculating…' : 'Compare scenarios'}
          </button>
        </form>

        {loading && <p role="status">Calculating both scenarios…</p>}
        {error && <p role="alert">{error} Please retry.</p>}

        {results && (
          <div aria-live="polite">
            <p>
              Coverage: <strong>{format(results[0].coverage.sampled_area_km2)} km²</strong>
              {' '}across {format(results[0].coverage.sampled_cell_count)} sampled cells.
              This is the sum of full GIS cells, not the exact municipal polygon area.
            </p>
            <div style={{ overflowX: 'auto' }}>
              <table style={{
                width: '100%', minWidth: 460,
                borderCollapse: 'collapse', textAlign: 'left',
              }}>
                <caption style={{ textAlign: 'left', padding: '12px 0' }}>
                  Calculated scenario comparison
                </caption>
                <thead>
                  <tr>
                    <th scope="col" style={{ padding: 10 }}>Measurement</th>
                    <th scope="col" style={{ padding: 10 }}>Scenario A</th>
                    <th scope="col" style={{ padding: 10 }}>Scenario B</th>
                  </tr>
                </thead>
                <tbody>
                  {comparisonRows.map(([label, a, b]) => (
                    <tr key={String(label)} style={{ borderTop: '1px solid #e2e8f0' }}>
                      <th scope="row" style={{ padding: 10 }}>{label}</th>
                      <td style={{ padding: 10 }}>{format(Number(a))}</td>
                      <td style={{ padding: 10 }}>{format(Number(b))}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p>
              <strong>
                Scenario B produces {format(Math.abs(difference))} m³
                {' '}{difference < 0 ? 'less' : 'more'} estimated runoff than A
                under these assumptions.
              </strong>
            </p>
          </div>
        )}

        <details style={{ marginTop: 16 }}>
          <summary>How this calculation works and its limitations</summary>
          <p>Rainfall volume = rainfall depth ÷ 1,000 × sampled area in m².</p>
          <p>Estimated runoff volume = rainfall volume × assumed runoff fraction.</p>
          <p>
            Rainfall and runoff fraction are uniform across the sampled area.
            Duration changes average intensity, but not total runoff volume
            when depth and runoff fraction remain fixed.
          </p>
          <p>
            Remaining water is not separately modelled as infiltration,
            storage or evaporation. No flow routing, drainage capacity,
            flood depth or inundation extent is calculated.
          </p>
        </details>
      </div>
    </section>
  )
}

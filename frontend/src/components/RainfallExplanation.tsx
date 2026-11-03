import { useEffect, useState } from 'react'

type Feature = {
  feature: string
  label: string
  importance: number
  importance_percent: number
}

type Explanation = {
  schema_version: number
  status: string
  method: string
  features: Feature[]
  limitations: string[]
}

function valid(value: unknown): value is Explanation {
  if (!value || typeof value !== 'object') return false
  const data = value as Explanation
  if (
    data.schema_version !== 1 ||
    data.status !== 'experimental_rainfall_model_explanation' ||
    data.method !== 'mean_decrease_in_impurity' ||
    !Array.isArray(data.features) ||
    data.features.length !== 11 ||
    !Array.isArray(data.limitations) ||
    !data.limitations.every((item) => typeof item === 'string')
  ) return false

  if (!data.features.every((item) =>
    item && typeof item.feature === 'string' &&
    typeof item.label === 'string' &&
    typeof item.importance === 'number' &&
    Number.isFinite(item.importance) &&
    item.importance >= 0 && item.importance <= 1 &&
    typeof item.importance_percent === 'number' &&
    Number.isFinite(item.importance_percent) &&
    Math.abs(item.importance_percent - item.importance * 100) < 0.000001
  )) return false

  return (
    new Set(data.features.map((item) => item.feature)).size === 11 &&
    Math.abs(data.features.reduce((sum, item) => sum + item.importance, 0) - 1)
      < 0.000001
  )
}

export default function RainfallExplanation() {
  const [data, setData] = useState<Explanation | null>(null)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      try {
        const response = await fetch(
          `${import.meta.env.BASE_URL}data/model_explanation_v1.json`,
          { signal: controller.signal },
        )
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const result: unknown = await response.json()
        if (!valid(result)) throw new Error('Unexpected explanation data.')
        if (!controller.signal.aborted) setData(result)
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : 'Unable to load explanation.')
        }
      }
    }
    void load()
    return () => controller.abort()
  }, [attempt])

  return (
    <section className="section-block" id="rainfall-explanation">
      <div className="section-heading">
        <div>
          <div className="eyebrow">MODEL INTERPRETABILITY</div>
          <h2>What inputs did the rainfall model use most?</h2>
        </div>
      </div>
      <div className="panel-card">
        <p>
          Global feature importance for the experimental Random Forest trained
          on 2001–2002. Larger values indicate a larger share of the
          improvement in the trees’ training splitting criterion.
        </p>
        <p>
          <strong>These percentages are not accuracy or flood probability.</strong>
          {' '}They describe the model overall, not an individual prediction.
        </p>

        {error ? (
          <div role="alert">
            <p>Could not load the explanation: {error}</p>
            <button
              type="button"
              className="map-control-button"
              onClick={() => {
                setError('')
                setAttempt((value) => value + 1)
              }}
            >
              Retry explanation
            </button>
          </div>
        ) : !data ? (
          <p role="status">Loading model explanation…</p>
        ) : (
          <>
            <p className="small-note">
              Method: mean decrease in impurity. Every bar uses the same
              0–100% scale.
            </p>
            <ol style={{ listStyle: 'none', margin: 0, padding: 0 }}>
              {[...data.features]
                .sort((a, b) => b.importance - a.importance)
                .map((item) => (
                  <li key={item.feature} style={{ marginBottom: 16 }}>
                    <div style={{
                      display: 'flex', justifyContent: 'space-between',
                      gap: 16, marginBottom: 6,
                    }}>
                      <span>{item.label}</span>
                      <strong>{item.importance_percent.toFixed(2)}%</strong>
                    </div>
                    <div
                      aria-hidden="true"
                      style={{
                        height: 12, background: '#e2e8f0',
                        borderRadius: 6, overflow: 'hidden',
                      }}
                    >
                      <div style={{
                        width: `${item.importance_percent}%`,
                        height: '100%', background: '#0284c7',
                      }} />
                    </div>
                  </li>
                ))}
            </ol>

            <details>
              <summary>Interpretation and limitations</summary>
              <ul>
                {data.limitations.map((note) => <li key={note}>{note}</li>)}
              </ul>
            </details>
            <p className="small-note">
              The rainfall model did not outperform the zero-rainfall baseline
              on MAE in any evaluated period. Feature importance does not
              change that evaluation result.
            </p>
          </>
        )}
      </div>
    </section>
  )
}

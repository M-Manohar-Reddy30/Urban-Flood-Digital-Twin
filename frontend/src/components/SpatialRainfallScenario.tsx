import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet'

type Inputs = {
  rainfall_depth_mm: number
  duration_hours: number
  runoff_fraction: number
}

type Sample = {
  type: 'Feature'
  id: number
  geometry: { type: 'Point'; coordinates: [number, number] }
  properties: {
    upstream_contributing_area_km2: number
    estimated_upstream_runoff_volume_m3: number
  }
}

type SpatialResult = {
  type: 'FeatureCollection'
  features: Sample[]
  metadata: {
    status: string
    sample_count: number
    inputs: Inputs
    limitations: string[]
  }
}

const bands = [
  { label: '0 m³', colour: '#64748b' },
  { label: '>0–<100,000 m³', colour: '#bae6fd' },
  { label: '100,000–<500,000 m³', colour: '#38bdf8' },
  { label: '500,000–<1,000,000 m³', colour: '#0284c7' },
  { label: '≥1,000,000 m³', colour: '#08306b' },
]

function colour(volume: number) {
  if (volume === 0) return bands[0].colour
  if (volume < 100000) return bands[1].colour
  if (volume < 500000) return bands[2].colour
  if (volume < 1000000) return bands[3].colour
  return bands[4].colour
}

function valid(value: unknown): value is SpatialResult {
  if (!value || typeof value !== 'object') return false
  const result = value as SpatialResult
  const metadata = result.metadata
  if (
    result.type !== 'FeatureCollection' ||
    !Array.isArray(result.features) ||
    result.features.length === 0 ||
    !metadata ||
    metadata.status !== 'exploratory_uncalibrated_spatial_scenario' ||
    metadata.sample_count !== result.features.length ||
    !metadata.inputs ||
    !Array.isArray(metadata.limitations) ||
    !metadata.limitations.every((item) => typeof item === 'string')
  ) return false

  const inputs = metadata.inputs
  if (![
    inputs.rainfall_depth_mm,
    inputs.duration_hours,
    inputs.runoff_fraction,
  ].every((item) => typeof item === 'number' && Number.isFinite(item))) {
    return false
  }

  return result.features.every((feature) => {
    if (
      !feature || feature.type !== 'Feature' ||
      !Number.isInteger(feature.id) ||
      feature.geometry?.type !== 'Point' ||
      !Array.isArray(feature.geometry.coordinates) ||
      feature.geometry.coordinates.length !== 2 ||
      !feature.properties
    ) return false

    const [longitude, latitude] = feature.geometry.coordinates
    const area = feature.properties.upstream_contributing_area_km2
    const volume = feature.properties.estimated_upstream_runoff_volume_m3
    return (
      [longitude, latitude, area, volume].every(
        (item) => typeof item === 'number' && Number.isFinite(item),
      ) &&
      Math.abs(longitude) <= 180 && Math.abs(latitude) <= 90 &&
      area >= 1 && volume >= 0
    )
  }) && new Set(result.features.map((item) => item.id)).size === result.features.length
}

const format = (value: number) =>
  value.toLocaleString('en-IN', { maximumFractionDigits: 2 })

export default function SpatialRainfallScenario({ api }: { api: string }) {
  const [depth, setDepth] = useState('50')
  const [duration, setDuration] = useState('2')
  const [fraction, setFraction] = useState('0.5')
  const [data, setData] = useState<SpatialResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const active = useRef<AbortController | null>(null)

  useEffect(() => () => active.current?.abort(), [])

  async function calculate(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const inputs: Inputs = {
      rainfall_depth_mm: Number(depth),
      duration_hours: Number(duration),
      runoff_fraction: Number(fraction),
    }
    if (
      [depth, duration, fraction].some((item) => item.trim() === '') ||
      !Object.values(inputs).every(Number.isFinite) ||
      inputs.rainfall_depth_mm < 0 || inputs.rainfall_depth_mm > 1000 ||
      inputs.duration_hours <= 0 || inputs.duration_hours > 168 ||
      inputs.runoff_fraction < 0 || inputs.runoff_fraction > 1
    ) {
      setError('Enter valid rainfall, duration and runoff fraction values.')
      return
    }

    active.current?.abort()
    const controller = new AbortController()
    active.current = controller
    setLoading(true)
    setError('')
    setData(null)

    try {
      const response = await fetch(`${api}/api/v1/scenarios/rainfall/spatial`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(inputs),
        signal: controller.signal,
      })
      if (!response.ok) throw new Error(`Spatial request failed (HTTP ${response.status}).`)
      const result: unknown = await response.json()
      if (!valid(result)) throw new Error('Unexpected spatial scenario response.')
      if (!controller.signal.aborted) setData(result)
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(err instanceof Error ? err.message : 'Unable to calculate scenario.')
      }
    } finally {
      if (!controller.signal.aborted) setLoading(false)
    }
  }

  return (
    <section className="section-block" id="spatial-scenario">
      <div className="section-heading">
        <div>
          <div className="eyebrow">SPATIAL WHAT-IF EXPLORATION</div>
          <h2>Upstream runoff-volume scenario</h2>
        </div>
      </div>
      <div className="panel-card">
        <p>
          Explore estimated upstream runoff volumes at GIS samples with at least
          1 km² contributing area. Click a point to inspect its values.
        </p>
        <p className="small-note">
          Uniform rainfall is assumed across the modelled upstream area,
          including land outside Ballari. This calculation does not estimate
          flood depth, inundation or drainage overflow.
        </p>

        <form onSubmit={calculate}>
          <fieldset disabled={loading} style={{ border: 0, padding: 0, margin: 0 }}>
            <legend>Scenario assumptions</legend>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 16, margin: '12px 0' }}>
              <label>
                Rainfall depth (mm)
                <input
                  type="number" min="0" max="1000" step="any" required
                  value={depth}
                  onChange={(event) => setDepth(event.target.value)}
                  style={{ display: 'block', padding: 10, maxWidth: '100%' }}
                />
              </label>
              <label>
                Duration (hours)
                <input
                  type="number" min="0.01" max="168" step="any" required
                  value={duration}
                  onChange={(event) => setDuration(event.target.value)}
                  style={{ display: 'block', padding: 10, maxWidth: '100%' }}
                />
              </label>
              <label>
                Assumed runoff fraction (0–1)
                <input
                  type="number" min="0" max="1" step="any" required
                  value={fraction}
                  onChange={(event) => setFraction(event.target.value)}
                  style={{ display: 'block', padding: 10, maxWidth: '100%' }}
                />
              </label>
            </div>
            <button type="submit" className="map-control-button">
              {loading ? 'Calculating…' : 'Calculate spatial scenario'}
            </button>
          </fieldset>
        </form>

        {loading && <p role="status">Loading spatial results…</p>}
        {error && <p role="alert">{error}</p>}

        {data && (
          <>
            <p role="status">
              Displayed result: {format(data.metadata.inputs.rainfall_depth_mm)} mm,
              {' '}{format(data.metadata.inputs.duration_hours)} hours,
              {' '}runoff fraction {format(data.metadata.inputs.runoff_fraction)}.
              {' '}{format(data.metadata.sample_count)} sample locations.
            </p>
            <p className="small-note">
              After editing assumptions, calculate again to update the map.
              Duration changes average rainfall intensity, but not the total
              volume at fixed rainfall depth and runoff fraction.
            </p>

            <MapContainer
              center={[15.12, 76.92]}
              zoom={12}
              preferCanvas
              scrollWheelZoom={false}
              style={{ height: 480, width: '100%', borderRadius: 10 }}
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              />
              {data.features.map((feature) => {
                const [longitude, latitude] = feature.geometry.coordinates
                const properties = feature.properties
                const volume = properties.estimated_upstream_runoff_volume_m3
                return (
                  <CircleMarker
                    key={feature.id}
                    center={[latitude, longitude]}
                    radius={4}
                    pathOptions={{
                      color: colour(volume),
                      fillColor: colour(volume),
                      fillOpacity: 0.85,
                      weight: 1,
                    }}
                  >
                    <Popup>
                      <strong>Exploratory upstream volume</strong>
                      <p>GIS sample: {latitude.toFixed(5)}° N, {longitude.toFixed(5)}° E</p>
                      <p>
                        Contributing area: <strong>
                          {format(properties.upstream_contributing_area_km2)} km²
                        </strong>
                      </p>
                      <p>
                        Estimated upstream runoff: <strong>{format(volume)} m³</strong>
                      </p>
                      <p>Volumes overlap between locations. Do not add them together.</p>
                    </Popup>
                  </CircleMarker>
                )
              })}
            </MapContainer>

            <p><strong>Estimated upstream runoff volume — fixed scale</strong></p>
            <ul style={{
              display: 'flex', flexWrap: 'wrap', gap: 16,
              listStyle: 'none', padding: 0,
            }}>
              {bands.map((band) => (
                <li key={band.label}>
                  <span aria-hidden="true" style={{
                    display: 'inline-block', width: 14, height: 14,
                    background: band.colour, marginRight: 6,
                    border: '1px solid #475569',
                  }} />
                  {band.label}
                </li>
              ))}
            </ul>
            <p className="small-note">
              Colours represent volume ranges, not flood-risk categories.
              Points represent samples, not channel widths or flooded areas.
            </p>
            <details>
              <summary>Method assumptions and limitations</summary>
              <ul>
                {data.metadata.limitations.map((item) => <li key={item}>{item}</li>)}
              </ul>
            </details>
          </>
        )}
      </div>
    </section>
  )
}

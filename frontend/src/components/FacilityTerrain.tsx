import { useEffect, useRef, useState } from 'react'

type Terrain = {
  status: string
  cell_centre_distance_m: number
  values: {
    elevation_m: number
    slope_degrees: number
    distance_to_mapped_drain_m: number
    distance_to_mapped_stream_m: number
  }
}

export default function FacilityTerrain({
  api, latitude, longitude,
}: {
  api: string; latitude: number; longitude: number
}) {
  const [data, setData] = useState<Terrain | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const active = useRef<AbortController | null>(null)

  useEffect(() => () => active.current?.abort(), [])

  async function inspect() {
    active.current?.abort()
    const controller = new AbortController()
    active.current = controller
    setLoading(true)
    setError('')
    setData(null)
    try {
      const query = new URLSearchParams({
        latitude: String(latitude), longitude: String(longitude),
      })
      const response = await fetch(
        `${api}/api/v1/gis/terrain-inspection?${query}`,
        { signal: controller.signal },
      )
      if (response.status === 404) {
        throw new Error('No available terrain cell at this mapped location.')
      }
      if (!response.ok) throw new Error(`Terrain request failed (HTTP ${response.status}).`)
      const result: Terrain = await response.json()
      if (
        !result ||
        result.status !== 'provisional_environmental_features' ||
        !result.values ||
        ![
          result.values.elevation_m,
          result.values.slope_degrees,
          result.values.distance_to_mapped_drain_m,
          result.values.distance_to_mapped_stream_m,
          result.cell_centre_distance_m,
        ].every((value) => typeof value === 'number' && Number.isFinite(value))
      ) throw new Error('Unexpected terrain response.')

      if (!controller.signal.aborted) setData(result)
    } catch (err) {
      if (!controller.signal.aborted) {
        setError(err instanceof Error ? err.message : 'Unable to inspect terrain.')
      }
    } finally {
      if (!controller.signal.aborted) setLoading(false)
    }
  }

  return (
    <div>
      <button
        type="button"
        className="map-control-button"
        disabled={loading}
        onClick={() => void inspect()}
      >
        {loading ? 'Loading terrain…' : 'Inspect terrain here'}
      </button>
      {error && <p role="alert">{error}</p>}
      {data && (
        <div role="status" style={{ maxHeight: 180, overflowY: 'auto' }}>
          <p>Elevation: <strong>{data.values.elevation_m.toFixed(1)} m</strong></p>
          <p>Slope: <strong>{data.values.slope_degrees.toFixed(2)}°</strong></p>
          <p>Mapped drain distance: <strong>
            {data.values.distance_to_mapped_drain_m.toFixed(1)} m
          </strong></p>
          <p>Mapped stream distance: <strong>
            {data.values.distance_to_mapped_stream_m.toFixed(1)} m
          </strong></p>
          <p>Sample centre distance: {data.cell_centre_distance_m.toFixed(1)} m</p>
          <p>
            Values describe the GIS cell at this display point,
            not the entire facility. They do not establish flood risk.
          </p>
        </div>
      )}
    </div>
  )
}

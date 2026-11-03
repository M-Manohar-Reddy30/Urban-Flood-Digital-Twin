import { useEffect, useRef, useState } from 'react'
import { Popup, useMapEvents } from 'react-leaflet'

type Inspection = {
  status: string
  cell_centre_distance_m: number
  values: {
    elevation_m: number
    slope_degrees: number
    landcover_class: number
    distance_to_mapped_drain_m: number
    distance_to_mapped_stream_m: number
    upstream_contributing_area_km2: number
  }
  note: string
}

export default function TerrainInspector({ api }: { api: string }) {
  const [position, setPosition] = useState<[number, number] | null>(null)
  const [data, setData] = useState<Inspection | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const request = useRef<AbortController | null>(null)

  useEffect(() => {
    return () => request.current?.abort()
  }, [])

  useMapEvents({
    click(event) {
      request.current?.abort()
      const controller = new AbortController()
      request.current = controller

      const { lat, lng } = event.latlng
      setPosition([lat, lng])
      setData(null)
      setError('')
      setLoading(true)

      async function inspect() {
        try {
          const query = new URLSearchParams({
            latitude: String(lat),
            longitude: String(lng),
          })
          const response = await fetch(
            `${api}/api/v1/gis/terrain-inspection?${query}`,
            { signal: controller.signal },
          )

          if (!response.ok) {
            if (response.status === 404) {
              throw new Error(
                'No data here: the location is outside Ballari or in a data gap.',
              )
            }
            throw new Error(`Terrain inspection failed (HTTP ${response.status}).`)
          }

          const result: Inspection = await response.json()
          const values = result.values
          if (
            result.status !== 'provisional_environmental_features' ||
            !values ||
            ![
              values.elevation_m,
              values.slope_degrees,
              values.landcover_class,
              values.distance_to_mapped_drain_m,
              values.distance_to_mapped_stream_m,
              values.upstream_contributing_area_km2,
              result.cell_centre_distance_m,
            ].every((value) =>
              typeof value === 'number' && Number.isFinite(value)
            )
          ) {
            throw new Error('Unexpected terrain response.')
          }

          if (!controller.signal.aborted) setData(result)
        } catch (err) {
          if (!controller.signal.aborted) {
            setError(
              err instanceof Error ? err.message : 'Unable to inspect this location.',
            )
          }
        } finally {
          if (!controller.signal.aborted) setLoading(false)
        }
      }

      void inspect()
    },
  })

  if (!position) return null

  const rows = data ? [
    ['Elevation', `${data.values.elevation_m.toFixed(1)} m`],
    ['Slope', `${data.values.slope_degrees.toFixed(2)}°`],
    ['Land-cover code', String(data.values.landcover_class)],
    ['Distance to mapped drain', `${data.values.distance_to_mapped_drain_m.toFixed(1)} m`],
    ['Distance to mapped stream', `${data.values.distance_to_mapped_stream_m.toFixed(1)} m`],
    ['Upstream contributing area', `${data.values.upstream_contributing_area_km2.toFixed(4)} km²`],
    ['Distance to sampled cell centre', `${data.cell_centre_distance_m.toFixed(1)} m`],
  ] : []

  return (
    <Popup
      key={position.join(',')}
      position={position}
      maxWidth={340}
      minWidth={240}
    >
      <div
        role="region"
        aria-label="Terrain inspection details"
        tabIndex={0}
        style={{
          maxHeight: 'min(320px, 45vh)',
          overflowY: 'auto',
          paddingRight: 8,
          fontSize: 12,
          lineHeight: 1.45,
        }}
      >
        <strong>Terrain inspection — provisional</strong>
        <p style={{ margin: '8px 0 12px' }}>
          {position[0].toFixed(5)}° N, {position[1].toFixed(5)}° E
        </p>

        {loading && <p role="status">Loading location values…</p>}
        {error && <p role="alert">{error}</p>}

        {data && (
          <>
            <dl style={{ margin: 0 }}>
              {rows.map(([label, value]) => (
                <div
                  key={label}
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'minmax(0, 1fr) auto',
                    gap: 12,
                    padding: '7px 0',
                    borderBottom: '1px solid #e2e8f0',
                  }}
                >
                  <dt>{label}</dt>
                  <dd style={{
                    margin: 0,
                    fontWeight: 700,
                    textAlign: 'right',
                    whiteSpace: 'nowrap',
                  }}>
                    {value}
                  </dd>
                </div>
              ))}
            </dl>
            <p style={{ fontSize: 11, margin: '12px 0 0' }}>
              {data.note}
            </p>
          </>
        )}
      </div>
    </Popup>
  )
}

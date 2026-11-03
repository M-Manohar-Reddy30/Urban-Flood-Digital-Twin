import FacilityTerrain from './FacilityTerrain'
import { useEffect, useState } from 'react'
import { CircleMarker, MapContainer, Popup, TileLayer } from 'react-leaflet'

type Facility = {
  id: string
  geometry: { type: 'Point'; coordinates: [number, number] }
  properties: {
    name: string
    group: 'Healthcare' | 'Education'
    category: string
    coordinate_method: string
  }
}

type Dataset = {
  type: 'FeatureCollection'
  features: Facility[]
  metadata: {
    retained_point_count: number
    retrieved_at_utc: string
    limitations: string[]
  }
}

function valid(value: unknown): value is Dataset {
  if (!value || typeof value !== 'object') return false
  const data = value as Dataset
  if (
    data.type !== 'FeatureCollection' ||
    !Array.isArray(data.features) ||
    !data.metadata ||
    data.metadata.retained_point_count !== data.features.length ||
    typeof data.metadata.retrieved_at_utc !== 'string' ||
    !Array.isArray(data.metadata.limitations) ||
    !data.metadata.limitations.every((item) => typeof item === 'string')
  ) return false

  return data.features.every((item) => {
    if (
      !item || typeof item.id !== 'string' ||
      !/^(node|way|relation)\/\d+$/.test(item.id) ||
      item.geometry?.type !== 'Point' ||
      !Array.isArray(item.geometry.coordinates) ||
      item.geometry.coordinates.length !== 2 ||
      !item.properties
    ) return false
    const [lon, lat] = item.geometry.coordinates
    const p = item.properties
    return (
      typeof lon === 'number' && Number.isFinite(lon) && Math.abs(lon) <= 180 &&
      typeof lat === 'number' && Number.isFinite(lat) && Math.abs(lat) <= 90 &&
      typeof p.name === 'string' && typeof p.category === 'string' &&
      (p.group === 'Healthcare' || p.group === 'Education') &&
      ['mapped_node', 'osm_object_bounding_box_centre'].includes(p.coordinate_method)
    )
  }) && new Set(data.features.map((item) => item.id)).size === data.features.length
}

export default function FacilitiesMap({ api }: { api: string }) {
  const [data, setData] = useState<Dataset | null>(null)
  const [category, setCategory] = useState('all')
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    const controller = new AbortController()
    async function load() {
      try {
        const response = await fetch(
          `${import.meta.env.BASE_URL}data/ballari_facilities.json`,
          { signal: controller.signal },
        )
        if (!response.ok) throw new Error(`HTTP ${response.status}`)
        const result: unknown = await response.json()
        if (!valid(result)) throw new Error('Unexpected facilities data.')
        if (!controller.signal.aborted) setData(result)
      } catch (err) {
        if (!controller.signal.aborted) {
          setError(err instanceof Error ? err.message : 'Unable to load facilities.')
        }
      }
    }
    void load()
    return () => controller.abort()
  }, [attempt])

  const categories = data
    ? [...new Set(data.features.map((item) => item.properties.category))].sort()
    : []
  const visible = data?.features.filter(
    (item) => category === 'all' || item.properties.category === category,
  ) ?? []

  return (
    <section className="section-block" id="facilities">
      <div className="section-heading">
        <div>
          <div className="eyebrow">MAPPED INFRASTRUCTURE</div>
          <h2>Education and healthcare facilities</h2>
        </div>
      </div>
      <div className="panel-card">
        <p>
          Explore source-mapped facility locations inside Ballari.
          Counts describe OSM objects; separate objects can represent the same facility.
        </p>
        <p className="small-note">
          Locations and current operation have not been field verified.
          These markers do not identify flooded or flood-exposed facilities.
        </p>

        {error ? (
          <div role="alert">
            <p>Could not load facilities: {error}</p>
            <button
              type="button" className="map-control-button"
              onClick={() => { setError(''); setAttempt((value) => value + 1) }}
            >
              Retry
            </button>
          </div>
        ) : !data ? (
          <p role="status">Loading mapped facilities…</p>
        ) : (
          <>
            <p>
              <strong>{data.features.length} mapped objects</strong>
              {' · '}{data.features.filter((item) => item.properties.group === 'Healthcare').length}
              {' healthcare · '}
              {data.features.filter((item) => item.properties.group === 'Education').length}
              {' education'}
            </p>
            <label>
              Facility category
              <select
                value={category}
                onChange={(event) => setCategory(event.target.value)}
                style={{ padding: 10, margin: '0 0 12px 12px', maxWidth: '100%' }}
              >
                <option value="all">All categories</option>
                {categories.map((item) => (
                  <option key={item} value={item}>
                    {item} ({data.features.filter((f) => f.properties.category === item).length})
                  </option>
                ))}
              </select>
            </label>
            <p role="status">Showing {visible.length} mapped objects.</p>
            <p>Teal: healthcare. Purple: education.</p>

            <MapContainer
              center={[15.12, 76.92]} zoom={12}
              scrollWheelZoom={false}
              style={{ height: 480, width: '100%', borderRadius: 10 }}
            >
              <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
              />
              {visible.map((item) => {
                const [lon, lat] = item.geometry.coordinates
                const p = item.properties
                const colour = p.group === 'Healthcare' ? '#0f766e' : '#7c3aed'
                return (
                  <CircleMarker
                    key={item.id} center={[lat, lon]} radius={7}
                    pathOptions={{
                      color: colour, fillColor: colour,
                      fillOpacity: 0.85, weight: 2,
                    }}
                  >
                    <Popup>
                      <strong>{p.name}</strong>
                      <p>{p.group} · {p.category}</p>
                      <p>
                        {p.coordinate_method === 'mapped_node'
                          ? 'Location: mapped OSM point.'
                          : 'Location: mapped object bounding-box centre; not an entrance.'}
                      </p>
                      <a
                        href={`https://www.openstreetmap.org/${item.id}`}
                        target="_blank" rel="noopener noreferrer"
                      >
                        View original OpenStreetMap record
                      </a>
                      <p>Source-mapped location; not field verified.</p>
                      <FacilityTerrain
                        api={api} latitude={lat} longitude={lon}
                      />
                    </Popup>
                  </CircleMarker>
                )
              })}
            </MapContainer>

            <p className="small-note">
              Data downloaded: {data.metadata.retrieved_at_utc.slice(0, 10)}.
              {' '}© OpenStreetMap contributors.{' '}
              <a
                href="https://www.openstreetmap.org/copyright"
                target="_blank" rel="noopener noreferrer"
              >
                Attribution and ODbL licence
              </a>
            </p>
            <details>
              <summary>Coverage and location limitations</summary>
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

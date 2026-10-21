import { lazy, Suspense, useEffect, useState } from 'react'
import {
  Activity, AlertTriangle, ArrowDownRight, CloudRain,
  Database, Layers3, MapPin, RefreshCw, ShieldCheck,
  Waves, Droplets, Mountain, ExternalLink, Eye, EyeOff,
  Maximize2,
} from 'lucide-react'
import {
  MapContainer, TileLayer, GeoJSON, useMap,
} from 'react-leaflet'
import type { GeoJSON as GeoJSONType } from 'geojson'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import './App.css'

const API = 'http://127.0.0.1:8000'

const RainfallChart = lazy(() => import('./components/RainfallChart'))

type GisSummary = {
  city?: string
  dataset?: string
  feature_count?: number
  coordinate_reference_system?: string
  elevation_m?: { min?: number; max?: number; mean?: number }
  slope_degrees?: { min?: number; max?: number; mean?: number }
  landcover_class_counts?: Record<string, number>
  note?: string
  [key: string]: unknown
}


type RainfallResponse = {
  source?: string
  dataset?: string
  unit?: string
  measurement_note?: string
  grid_point?: { latitude?: number; longitude?: number }
  record_count?: number
  start_date?: string
  end_date?: string
  statistics?: {
    mean?: number
    maximum?: number
    minimum?: number
    days_above_zero?: number
    days_at_zero?: number
  }
  records?: {
    date: string
    precipitation_mm_per_day: number
    valid_half_hourly_retrievals?: number
    status?: string
  }[]
}

type Evidence = {
  event_date?: string
  date?: string
  location?: string
  place?: string
  description?: string
  incident?: string
  source_document?: string
  evidence_type?: string
  inside_city_boundary?: string
  spatial_verification_status?: string
  latitude?: string | number
  longitude?: string | number
  [key: string]: unknown
}

type EvidenceResponse = {
  total_records?: number
  records?: Evidence[]
  note?: string
  [key: string]: unknown
}


type DrainageProperties = {
  source_id?: string | number
  category?: string
  dr_code?: string
  status?: string
  clipped_length_km?: number
  [key: string]: unknown
}


function FitBoundary({
  boundary,
  resetKey,
}: {
  boundary: GeoJSONType | null
  resetKey: number
}) {
  const map = useMap()

  useEffect(() => {
    if (!boundary) return
    const layer = L.geoJSON(boundary)
    const bounds = layer.getBounds()
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [28, 28] })
  }, [boundary, map, resetKey])

  return null
}

function StatCard({
  label, value, unit, icon: Icon, detail,
}: {
  label: string
  value: string
  unit?: string
  icon: typeof Activity
  detail: string
}) {
  return (
    <article className="stat-card">
      <div className="stat-top">
        <span>{label}</span>
        <span className="stat-icon"><Icon size={18} /></span>
      </div>
      <div className="stat-value">
        {value}
        {unit && <span className="stat-unit">{unit}</span>}
      </div>
      <div className="stat-detail">{detail}</div>
    </article>
  )
}

function formatNumber(value: unknown, digits = 1): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—'
  return value.toLocaleString('en-IN', { maximumFractionDigits: digits })
}

function evidenceTitle(item: Evidence): string {
  return String(
    item.location ?? item.place ?? item.incident ?? item.description ?? 'Reported flood incident',
  )
}

function evidenceDate(item: Evidence): string {
  return String(item.event_date ?? item.date ?? 'Date not specified')
}

function App() {
  const [gis, setGis] = useState<GisSummary | null>(null)
  const [evidence, setEvidence] = useState<EvidenceResponse | null>(null)
  const [boundary, setBoundary] = useState<GeoJSONType | null>(null)

  const [drainage, setDrainage] = useState<GeoJSONType | null>(null)
  const [drainageError, setDrainageError] = useState('')
  const [visibleDrainage, setVisibleDrainage] = useState({
    Drain: true,
    Stream: true,
    River: true,
  })
  const [selectedDrainage, setSelectedDrainage] =
    useState<DrainageProperties | null>(null)

  const [showDrainage, setShowDrainage] = useState(true)
  const [mapResetKey, setMapResetKey] = useState(0)

  const drainageFeatures =
  drainage?.type === 'FeatureCollection'
    ? drainage.features
    : []

  const drainageFeatureCount = drainageFeatures.length

  const drainageTotalLengthKm = drainageFeatures.reduce(
    (total, feature) => {
      const length = feature.properties?.clipped_length_km

      return (
        total +
        (typeof length === 'number' &&
        Number.isFinite(length) &&
        length >= 0
          ? length
          : 0)
      )
    },
    0,
  )

  const [rainfall, setRainfall] = useState<RainfallResponse | null>(null)
  const [rainfallError, setRainfallError] = useState('')
  const [apiStatus, setApiStatus] = useState<'loading' | 'online' | 'offline'>('loading')
  const [error, setError] = useState('')
  const [lastUpdated, setLastUpdated] = useState('Not yet refreshed')
  const [activeLayer, setActiveLayer] = useState<'street' | 'terrain'>('street')

  async function loadDashboard() {
    setApiStatus('loading')
    setError('')
    try {
      const [healthRes, gisRes, evidenceRes, boundaryRes] = await Promise.all([
        fetch(`${API}/health`),
        fetch(`${API}/api/v1/gis/summary`),
        fetch(`${API}/api/v1/evidence/summary`),
        fetch(`${API}/api/v1/gis/boundary`),
      ])

      if (!healthRes.ok) throw new Error('The backend health check failed.')
      if (!gisRes.ok) throw new Error('Could not load GIS summary.')
      if (!evidenceRes.ok) throw new Error('Could not load flood evidence.')
      if (!boundaryRes.ok) throw new Error('Could not load the municipal boundary.')

      const [gisData, evidenceData, boundaryData] = await Promise.all([
        gisRes.json() as Promise<GisSummary>,
        evidenceRes.json() as Promise<EvidenceResponse>,
        boundaryRes.json() as Promise<GeoJSONType>,
      ])

      setGis(gisData)
      setEvidence(evidenceData)
      setBoundary(boundaryData)
      setApiStatus('online')
      setLastUpdated(new Date().toLocaleTimeString('en-IN'))
    } catch (err) {
      setApiStatus('offline')
      setError(
        err instanceof Error
          ? `${err.message} Make sure the FastAPI server is running on port 8000.`
          : 'Unable to connect to the backend.',
      )
    }
  }

  useEffect(() => {
    let cancelled = false

    async function loadInitialDashboard() {
      try {
        const [healthRes, gisRes, evidenceRes, boundaryRes] = await Promise.all([
          fetch(`${API}/health`),
          fetch(`${API}/api/v1/gis/summary`),
          fetch(`${API}/api/v1/evidence/summary`),
          fetch(`${API}/api/v1/gis/boundary`),
        ])

        if (!healthRes.ok) throw new Error('The backend health check failed.')
        if (!gisRes.ok) throw new Error('Could not load GIS summary.')
        if (!evidenceRes.ok) throw new Error('Could not load flood evidence.')
        if (!boundaryRes.ok) throw new Error('Could not load the municipal boundary.')

        const [gisData, evidenceData, boundaryData] = await Promise.all([
          gisRes.json() as Promise<GisSummary>,
          evidenceRes.json() as Promise<EvidenceResponse>,
          boundaryRes.json() as Promise<GeoJSONType>,
        ])

        if (cancelled) return

        setGis(gisData)
        setEvidence(evidenceData)
        setBoundary(boundaryData)
        setApiStatus('online')
        setLastUpdated(new Date().toLocaleTimeString('en-IN'))
      } catch (err) {
        if (cancelled) return

        setApiStatus('offline')
        setError(
          err instanceof Error
            ? `${err.message} Make sure the FastAPI server is running on port 8000.`
            : 'Unable to connect to the backend.',
        )
      }
    }

    void loadInitialDashboard()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false

    async function loadDrainage() {
      try {
        const response = await fetch(`${API}/api/v1/gis/drainage`)

        if (!response.ok) {
          throw new Error(`Drainage API returned HTTP ${response.status}`)
        }

        const data = await response.json() as GeoJSONType

        if (cancelled) return

        if (data.type !== 'FeatureCollection') {
          throw new Error('The drainage response is not a FeatureCollection.')
        }

        setDrainage(data)
        setDrainageError('')
      } catch (err) {
        if (cancelled) return

        setDrainageError(
          err instanceof Error ? err.message : 'Unable to load drainage data.',
        )
      }
    }

    void loadDrainage()

    return () => {
      cancelled = true
    }
  }, [])

  useEffect(() => {
    let cancelled = false

    async function loadRainfall() {
      try {
        const response = await fetch(`${API}/api/v1/rainfall/summary`)
        if (!response.ok) throw new Error('Rainfall API request failed.')
        const data = await response.json() as RainfallResponse
        if (!cancelled) {
          setRainfall(data)
          setRainfallError('')
        }
      } catch {
        if (!cancelled) {
          setRainfallError('Rainfall data could not be loaded. Check that the backend is running.')
        }
      }
    }

    void loadRainfall()
    return () => { cancelled = true }
  }, [])

  const records = Array.isArray(evidence?.records) ? evidence.records : []
  const elevation = (gis?.elevation_m ?? {}) as Record<string, unknown>
  const slope = (gis?.slope_degrees ?? {}) as Record<string, unknown>
  const landcover = gis?.landcover_class_counts ?? {}

  const boundaryStyle = {
    color: '#38bdf8',
    weight: 3,
    opacity: 0.95,
    fillColor: '#0ea5e9',
    fillOpacity: 0.08,
    dashArray: '7 5',
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="#overview">
          <span className="brand-mark"><Waves size={25} /></span>
          <span>
            <strong>FLOODTWIN</strong>
            <small>URBAN INTELLIGENCE</small>
          </span>
        </a>

        <div className="side-label">WORKSPACE</div>
        <a className="nav-item selected" href="#overview"><Activity size={18} /> Overview</a>
        <a className="nav-item" href="#map-section"><MapPin size={18} /> GIS Explorer</a>
        <a className="nav-item" href="#rainfall"><CloudRain size={18} /> Rainfall Data</a>
        <a className="nav-item" href="#evidence"><Database size={18} /> Flood Evidence</a>

        <div className="sidebar-bottom">
          <div className="side-label">STUDY AREA</div>
          <div className="study-card">
            <span className="study-dot" />
            <div>
              <strong>Ballari, Karnataka</strong>
              <small>Municipal study boundary</small>
            </div>
          </div>
          <div className="sidebar-note">
            <ShieldCheck size={16} />
            Research prototype
          </div>
          <p className="sidebar-foot">URBAN RESILIENCE · RESEARCH BUILD</p>
        </div>
      </aside>

      <main className="main-content" id="overview">
        <header className="topbar">
          <div className="breadcrumb">Workspace <span>/</span> <strong>Overview</strong></div>
          <div className="top-actions">
            <span className={`status-pill ${apiStatus}`}>
              <span className="status-dot" />
              {apiStatus === 'online' ? 'API CONNECTED' : apiStatus === 'loading' ? 'CONNECTING' : 'API OFFLINE'}
            </span>
            <button className="refresh-btn" onClick={() => void loadDashboard()} aria-label="Refresh dashboard">
              <RefreshCw size={16} /> <span>Refresh</span>
            </button>
          </div>
        </header>

        <section className="hero">
          <div className="hero-copy">
            <div className="eyebrow"><span className="eyebrow-line" /> GEOSPATIAL MONITORING PLATFORM</div>
            <h1>Urban Flood <span>Digital Twin</span></h1>
            <p>
              A data-driven view of Ballari’s terrain, land cover and documented flood events.
              Built to support transparent urban flood research and planning.
            </p>
            <div className="hero-meta">
              <span><MapPin size={15} /> BALLARI, INDIA</span>
              <span><Layers3 size={15} /> GIS DATA LAYERS</span>
              <span><Activity size={15} /> {apiStatus === 'online' ? 'SYSTEM CONNECTED' : 'SYSTEM STATUS'}</span>
            </div>
          </div>
          <div className="hero-art" aria-hidden="true">
            <div className="art-ring ring-one" />
            <div className="art-ring ring-two" />
            <div className="art-core"><Waves size={50} /></div>
            <span className="art-tag tag-one">TERRAIN</span>
            <span className="art-tag tag-two">HYDROLOGY</span>
            <span className="art-tag tag-three">GEO DATA</span>
          </div>
        </section>

        {error && (
          <div className="error-banner">
            <AlertTriangle size={18} />
            <span>{error}</span>
            <button onClick={() => void loadDashboard()}>Retry</button>
          </div>
        )}

        <section className="section-block">
          <div className="section-heading">
            <div>
              <div className="eyebrow">DATA OVERVIEW</div>
              <h2>Study area at a glance</h2>
            </div>
            <span className="updated-label">Last refreshed: {lastUpdated}</span>
          </div>

          <div className="stats-grid">
            <StatCard label="GIS GRID CELLS" value={formatNumber(gis?.feature_count, 0)} icon={Layers3} detail="Environmental feature records" />
            <StatCard label="MEAN ELEVATION" value={formatNumber(elevation.mean)} unit="m" icon={Mountain} detail="Above sea level · DEM/DSM" />
            <StatCard label="MEAN SLOPE" value={formatNumber(slope.mean)} unit="°" icon={ArrowDownRight} detail="Terrain gradient" />
            <StatCard label="FLOOD EVIDENCE" value={formatNumber(evidence?.total_records, 0)} icon={Database} detail="Documented records · not model labels" />
          </div>
        </section>

        <section className="section-block" id="map-section">
          <div className="section-heading">
            <div>
              <div className="eyebrow">SPATIAL INTELLIGENCE</div>
              <h2>Municipal boundary explorer</h2>
            </div>
            <div className="map-switch">
              <button className={activeLayer === 'street' ? 'active' : ''} onClick={() => setActiveLayer('street')}>Street</button>
              <button className={activeLayer === 'terrain' ? 'active' : ''} onClick={() => setActiveLayer('terrain')}>Terrain</button>
            </div>
            <div className="drainage-toolbar">
              <button
                type="button"
                className="map-control-button"
                onClick={() => setShowDrainage((current) => !current)}
                aria-pressed={showDrainage}
              >
                {showDrainage ? <Eye size={15} /> : <EyeOff size={15} />}
                {showDrainage ? 'Hide drainage' : 'Show drainage'}
              </button>

              <button
                type="button"
                className="map-control-button"
                onClick={() => setMapResetKey((current) => current + 1)}
              >
                <Maximize2 size={15} />
                Reset map
              </button>

              <div className="drainage-filters">
                <strong>Drainage layers</strong>

                {(['Drain', 'Stream', 'River'] as const).map((category) => (
                  <label key={category}>
                    <input
                      type="checkbox"
                      checked={visibleDrainage[category]}
                      onChange={(event) =>
                        setVisibleDrainage((current) => ({
                          ...current,
                          [category]: event.target.checked,
                        }))
                      }
                    />
                    {category}
                  </label>
                ))}
              </div>
            </div>
          </div>

          {drainage && (
              <div
                className="drainage-summary"
                aria-label="Drainage dataset summary"
              >
                <div className="drainage-stat">
                  <span>Mapped features</span>
                  <strong>{drainageFeatureCount.toLocaleString()}</strong>
                </div>

                <div className="drainage-stat">
                  <span>Total mapped length</span>
                  <strong>
                    {drainageTotalLengthKm.toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: 2,
                    })}{' '}
                    km
                  </strong>
                </div>

                <p>
                  Dataset totals remain unchanged when category filters are used.
                  Length represents mapped geometry, not drainage capacity.
                </p>
              </div>
            )}

          <div className="map-layout">
            <div className="map-frame">
              {boundary ? (
                <MapContainer
                  center={[15.12, 76.92]}
                  zoom={12}
                  scrollWheelZoom
                  className="leaflet-map"
                >
                  <TileLayer
                    key={activeLayer}
                    attribution={activeLayer === 'street'
                      ? '&copy; OpenStreetMap contributors'
                      : '&copy; OpenTopoMap contributors'}
                    url={activeLayer === 'street'
                      ? 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
                      : 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png'}
                  />

                <GeoJSON data={boundary} style={() => boundaryStyle} />

                {drainage && showDrainage && (
                  <GeoJSON
                    key="ballari-drainage"
                    data={drainage}
                    filter={(feature) => {
                      const category = String(feature.properties?.category ?? '')
                      return Boolean(
                        visibleDrainage[category as keyof typeof visibleDrainage],
                      )
                    }}
                    style={(feature) => {
                      const category = String(feature?.properties?.category ?? '')

                      const colors: Record<string, string> = {
                        Drain: '#38bdf8',
                        Stream: '#34d399',
                        River: '#f59e0b',
                      }

                      const selectedSourceId = selectedDrainage?.source_id
                      const featureSourceId = feature?.properties?.source_id

                      const isSelected =
                        selectedSourceId !== undefined &&
                        selectedSourceId !== null &&
                        featureSourceId !== undefined &&
                        featureSourceId !== null &&
                        String(featureSourceId) === String(selectedSourceId)

                      if (isSelected) {
                        return {
                          color: '#ff4dff',
                          weight: 5,
                          opacity: 1,
                        }
                      }
                      return {
                        color: colors[category] ?? '#e879f9',
                        weight: category === 'River' ? 3 : category === 'Stream' ? 2 : 1.5,
                        opacity: 0.9,
                      }
                    }}

                    onEachFeature={(feature, layer) => {
                      layer.on('click', () => {
                        setSelectedDrainage(
                          feature.properties as DrainageProperties,
                        )
                      })
                    }}
                  />
                )}

                <FitBoundary boundary={boundary} resetKey={mapResetKey} />

                </MapContainer>
              ) : (
                <div className="map-placeholder">
                  <MapPin size={34} />
                  <strong>{apiStatus === 'loading' ? 'Loading municipal boundary…' : 'Map unavailable'}</strong>
                  <span>Connect the backend to display the study area.</span>
                </div>
              )}
                <div className="map-legend">
                  <div className="legend-item">
                    <span className="legend-line legend-boundary" />
                    Boundary
                  </div>
                  <div className="legend-item">
                    <span className="legend-line legend-drain" />
                    Drain
                  </div>
                  <div className="legend-item">
                    <span className="legend-line legend-stream" />
                    Stream
                  </div>
                  <div className="legend-item">
                    <span className="legend-line legend-river" />
                    River
                  </div>
                </div>
              <div className="map-coordinates">15.12° N&nbsp; · &nbsp;76.92° E</div>
            </div>

            <div className="map-side">
              <div className="panel-card">
                <div className="panel-title"><MapPin size={17} /> Study boundary</div>
                <div className="panel-value">{gis?.city ?? 'Ballari'}</div>
                <p>Municipal area used for the current GIS analysis.</p>
                <div className="mini-divider" />
                <div className="data-row"><span>Coordinate system</span><strong>{gis?.coordinate_reference_system ?? '—'}</strong></div>
                <div className="data-row"><span>Boundary status</span><strong className="blue-text">{boundary ? 'Loaded' : 'Unavailable'}</strong></div>
              </div>
              <div className="panel-card">
                <div className="panel-title"><Mountain size={17} /> Terrain range</div>
                <div className="range-item">
                  <div><span>Elevation</span><strong>{formatNumber(elevation.min)}–{formatNumber(elevation.max)} m</strong></div>
                  <div className="range-track"><span style={{ width: '72%' }} /></div>
                </div>
                <div className="range-item">
                  <div><span>Slope</span><strong>{formatNumber(slope.min)}–{formatNumber(slope.max)}°</strong></div>
                  <div className="range-track slope-track"><span style={{ width: '34%' }} /></div>
                </div>
                <p className="small-note">Terrain values describe topography; they are not flood-risk scores.</p>
              </div>
              <div className="panel-card">
                <div className="panel-title">
                  <Waves size={17} /> Drainage feature details
                </div>

                {drainageError ? (
                  <p>{drainageError}</p>
                ) : selectedDrainage ? (
                  <>
                    <div className="panel-value">
                      {String(selectedDrainage.category ?? 'Unclassified')}
                    </div>
                    <div className="data-row">
                      <span>Source ID</span>
                      <strong>{String(selectedDrainage.source_id ?? '—')}</strong>
                    </div>
                    <div className="data-row">
                      <span>Source code</span>
                      <strong>{String(selectedDrainage.dr_code ?? '—')}</strong>
                    </div>
                    <div className="data-row">
                      <span>Clipped length</span>
                      <strong>
                        {typeof selectedDrainage.clipped_length_km === 'number'
                          ? `${selectedDrainage.clipped_length_km.toFixed(3)} km`
                          : '—'}
                      </strong>
                    </div>
                  </>
                ) : (
                  <p>
                    {drainage
                      ? `${drainage.type === 'FeatureCollection' ? drainage.features.length : 0} drainage features loaded. Click a line on the map to inspect it.`
                      : 'Loading drainage features…'}
                  </p>
                )}

                <p className="small-note">
                  Source-mapped drainage features clipped to the municipal boundary;
                  these are not flood-risk predictions.
                </p>
              </div>
            </div>
          </div>
        </section>

        <section className="lower-grid">
          <div className="section-block" id="rainfall">
            <div className="section-heading">
              <div>
                <div className="eyebrow">CLIMATE INPUTS</div>
                <h2>Rainfall intelligence</h2>
              </div>
              <CloudRain size={20} className="heading-icon" />
            </div>
            <div className="rainfall-card rainfall-chart-card">
              <div className="rainfall-summary">
                <div className="rainfall-metric">
                  <span>Daily mean rate</span>
                  <strong>{formatNumber(rainfall?.statistics?.mean, 3)} mm/day</strong>
                </div>
                <div className="rainfall-metric">
                  <span>Maximum daily mean</span>
                  <strong>{formatNumber(rainfall?.statistics?.maximum, 3)} mm/day</strong>
                </div>
                <div className="rainfall-metric">
                  <span>Observations</span>
                  <strong>{rainfall?.record_count ?? '—'}</strong>
                </div>
              </div>

              <Suspense fallback={<p className="rainfall-empty">Loading rainfall chart…</p>}>
                <RainfallChart
                  rainfall={rainfall}
                  rainfallError={rainfallError}
                />
              </Suspense>
            </div>
            <div className="notice-row">
              <AlertTriangle size={15} />
              Historical satellite-derived observations only. No live feed or validated flood forecast is connected.
            </div>
          </div>

          <div className="section-block landcover-block">
            <div className="section-heading">
              <div>
                <div className="eyebrow">LAND SURFACE</div>
                <h2>Land-cover classes</h2>
              </div>
              <Layers3 size={20} className="heading-icon" />
            </div>
            <div className="landcover-card">
              {Object.keys(landcover).length ? (
                Object.entries(landcover)
                  .sort((a, b) => Number(b[1]) - Number(a[1]))
                  .slice(0, 6)
                  .map(([code, count]) => {
                    const names: Record<string, string> = {
                      '10': 'Tree cover', '20': 'Shrubland', '30': 'Grassland',
                      '40': 'Cropland', '50': 'Built-up', '60': 'Bare / sparse',
                      '80': 'Water bodies',
                    }
                    const total = Object.values(landcover).reduce((sum, n) => sum + Number(n), 0)
                    const percentage = total ? Number(count) / total * 100 : 0
                    return (
                      <div className="cover-row" key={code}>
                        <div className="cover-label"><span>{names[code] ?? `Class ${code}`}</span><strong>{percentage.toFixed(1)}%</strong></div>
                        <div className="cover-track"><span style={{ width: `${percentage}%` }} /></div>
                      </div>
                    )
                  })
              ) : (
                <div className="empty-inline"><Droplets size={20} /> Land-cover statistics will appear when the GIS API is available.</div>
              )}
              <p className="small-note">ESA WorldCover class counts from the processed GIS grid.</p>
            </div>
          </div>
        </section>

        <section className="section-block" id="evidence">
          <div className="section-heading">
            <div>
              <div className="eyebrow">DOCUMENTED INCIDENTS</div>
              <h2>Flood evidence register</h2>
              <p className="section-subtitle">Reported events collected from available disaster-management and news sources.</p>
            </div>
            <span className="evidence-count">{records.length} records loaded</span>
          </div>

          <div className="evidence-panel">
            <div className="evidence-header">
              <span>REPORTED EVENT / SOURCE</span>
              <span>DATE</span>
              <span>LOCATION STATUS</span>
            </div>
            {records.length ? records.slice(0, 10).map((item, index) => {
              const spatialStatus = String(item.spatial_verification_status ?? '')
              const verified = spatialStatus.toLowerCase().includes('verified')
              return (
                <div className="evidence-row" key={`${evidenceTitle(item)}-${index}`}>
                  <div className="evidence-event">
                    <span className="event-icon"><Waves size={17} /></span>
                    <div>
                      <strong>{evidenceTitle(item)}</strong>
                      <small>{String(item.source_document ?? item.evidence_type ?? 'Documented report')}</small>
                    </div>
                  </div>
                  <span className="event-date">{evidenceDate(item)}</span>
                  <span className={`verification-tag ${verified ? 'verified' : 'unverified'}`}>
                    {verified ? 'Verified' : 'Coordinates pending'}
                  </span>
                </div>
              )
            }) : (
              <div className="empty-state">
                <Database size={27} />
                <strong>{apiStatus === 'loading' ? 'Loading evidence…' : 'Evidence unavailable'}</strong>
                <span>Evidence records will appear when the API is connected.</span>
              </div>
            )}
            <div className="evidence-foot">
              <AlertTriangle size={15} />
              Reported incidents are not spatially verified flood labels. Do not interpret this register as a validated training dataset.
            </div>
          </div>
        </section>

        <footer className="footer">
          <div className="footer-brand"><Waves size={17} /> FLOODTWIN <span>·</span> BALLARI</div>
          <span>Research prototype · Data quality and spatial validation remain ongoing.</span>
          <a href={`${API}/docs`} target="_blank" rel="noreferrer">API documentation <ExternalLink size={13} /></a>
        </footer>
      </main>
    </div>
  )
}

export default App

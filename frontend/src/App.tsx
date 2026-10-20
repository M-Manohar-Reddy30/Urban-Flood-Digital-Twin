import { useEffect, useState } from 'react'
import {
  Activity, AlertTriangle, ArrowDownRight, CloudRain,
  Database, Layers3, MapPin, RefreshCw, ShieldCheck,
  Waves, Droplets, Mountain, ExternalLink,
} from 'lucide-react'
import {
  MapContainer, TileLayer, GeoJSON, useMap,
} from 'react-leaflet'
import type { GeoJSON as GeoJSONType } from 'geojson'
import L from 'leaflet'
import 'leaflet/dist/leaflet.css'
import './App.css'

const API = 'http://127.0.0.1:8000'

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

function FitBoundary({ boundary }: { boundary: GeoJSONType | null }) {
  const map = useMap()

  useEffect(() => {
    if (!boundary) return
    const layer = L.geoJSON(boundary)
    const bounds = layer.getBounds()
    if (bounds.isValid()) map.fitBounds(bounds, { padding: [28, 28] })
  }, [boundary, map])

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
    void loadDashboard()
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
          </div>

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
                  <FitBoundary boundary={boundary} />
                </MapContainer>
              ) : (
                <div className="map-placeholder">
                  <MapPin size={34} />
                  <strong>{apiStatus === 'loading' ? 'Loading municipal boundary…' : 'Map unavailable'}</strong>
                  <span>Connect the backend to display the study area.</span>
                </div>
              )}
              <div className="map-legend">
                <span className="legend-line" /> Municipal boundary
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
            <div className="rainfall-card">
              <div className="rainfall-symbol"><CloudRain size={27} /></div>
              <div className="rainfall-content">
                <strong>Rainfall dataset identified</strong>
                <p>NASA IMERG daily rainfall data for 2024 has been prepared locally. A backend time-series endpoint is still needed before the observations can be plotted here.</p>
                <span className="data-tag">HISTORICAL DATA · 2024</span>
              </div>
              <div className="rainfall-metric">
                <span>Series API</span>
                <strong>Pending</strong>
              </div>
            </div>
            <div className="notice-row"><AlertTriangle size={15} /> No live rainfall feed or rainfall forecast is currently connected.</div>
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

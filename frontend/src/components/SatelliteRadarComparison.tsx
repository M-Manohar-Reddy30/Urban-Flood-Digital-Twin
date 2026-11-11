import { useState } from 'react'
import './SatelliteRadarComparison.css'

const landCoverRows = [
  ['Tree cover', '6,447', '+0.979', '+0.825'],
  ['Shrubland', '10,721', '+1.657', '+1.529'],
  ['Grassland', '9,646', '+1.855', '+1.660'],
  ['Cropland', '36,753', '+2.160', '+2.497'],
  ['Built-up', '31,206', '+1.035', '+0.706'],
  ['Bare/sparse vegetation', '2,471', '+1.276', '+1.159'],
  ['Permanent water', '70', '+1.147', '+0.983'],
]

export default function SatelliteRadarComparison() {
  const [imageFailed, setImageFailed] = useState(false)
  const imageUrl = `${import.meta.env.BASE_URL}maps/ballari_radar_comparison.png`
  const manifestUrl = `${import.meta.env.BASE_URL}data/sentinel1_source_manifest.json`

  return (
    <section
      className="section-block radar-comparison"
      id="satellite-radar"
      aria-labelledby="satellite-radar-heading"
    >
      <div className="section-heading">
        <div>
          <div className="eyebrow">HISTORICAL SATELLITE ANALYSIS</div>
          <h2 id="satellite-radar-heading">Satellite radar comparison</h2>
        </div>
      </div>

      <div className="panel-card">
        <p>
          Sentinel-1A observations of Ballari on 28 May and 9 June 2026.
          This saved analysis compares radar return across the municipal area.
        </p>
        <p className="radar-notice">
          <strong>Exploratory radar changes — not a flood map.</strong>{' '}
          These results do not establish flood locations, water depth or
          flood-prediction accuracy. They are excluded from model training.
        </p>

        <dl className="radar-metrics">
          <div>
            <dt>Common usable city pixels</dt>
            <dd>97,385 / 97,459</dd>
            <small>99.92% coverage; not accuracy</small>
          </div>
          <div>
            <dt>Median VV change</dt>
            <dd>+1.573 dB</dd>
            <small>Radar return increased in 83.24% of usable pixels</small>
          </div>
          <div>
            <dt>Median VH change</dt>
            <dd>+1.450 dB</dd>
            <small>Radar return increased in 80.33% of usable pixels</small>
          </div>
        </dl>

        <p>
          Changes are June 9 minus May 28. VV and VH are two radar
          polarization channels. Positive values indicate increased radar
          return; negative values indicate decreased return.
        </p>

        <figure className="radar-figure">
          {imageFailed ? (
            <p role="alert">
              The comparison image could not be loaded. Refresh the page to retry.
            </p>
          ) : (
            <a href={imageUrl} target="_blank" rel="noopener noreferrer">
              <img
                src={imageUrl}
                alt="Six maps comparing Ballari VV and VH radar return on May 28 and June 9, with predominantly positive changes in the difference maps."
                loading="lazy"
                onError={() => setImageFailed(true)}
              />
            </a>
          )}
          <figcaption>
            Left: May 28. Middle: June 9. Right: change, with blue showing
            lower and red showing higher radar return. Neither colour
            independently establishes flooding. Click the image to enlarge it.
          </figcaption>
        </figure>

        <details>
          <summary>Changes by historical land-cover class</summary>
          <p>
            Categories come from the 2021 land-cover raster, sampled directly
            onto the radar grid using nearest-neighbour sampling. They do not
            confirm land use in June 2026.
          </p>
          <div
            className="radar-table-scroll"
            role="region"
            aria-label="Radar changes by land-cover class"
            tabIndex={0}
          >
            <table>
              <caption>Median changes within common usable pixels</caption>
              <thead>
                <tr>
                  <th scope="col">2021 land cover</th>
                  <th scope="col">Pixels</th>
                  <th scope="col">VV change (dB)</th>
                  <th scope="col">VH change (dB)</th>
                </tr>
              </thead>
              <tbody>
                {landCoverRows.map(([label, count, vv, vh]) => (
                  <tr key={label}>
                    <th scope="row">{label}</th>
                    <td>{count}</td>
                    <td>{vv}</td>
                    <td>{vh}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="small-note">
            71 usable radar pixels had no land-cover category and are excluded
            from this table. The permanent-water class contains only 70 pixels.
            Pixel counts are not independent event observations.
          </p>
        </details>

        <details>
          <summary>Method, sources and limitations</summary>
          <ul>
            <li>
              ASF HyP3 RTC GAMMA products; gamma-0 linear power converted to
              decibels for comparison; 30-metre pixel spacing.
            </li>
            <li>
              Both dates use the same city grid. Usable pixels require positive,
              finite VV and VH values and layover/shadow code 1 on both dates.
              This mask does not exclude every urban radar distortion.
            </li>
            <li>
              No additional smoothing was applied. Grid matching alone does
              not prove precise feature alignment.
            </li>
            <li>
              May 28 has not been independently verified as a dry reference.
              June 9 is after the reported June 7 event; temporary waterlogging
              may already have receded.
            </li>
            <li>
              Rebuilding reproduced the saved raster values. That establishes
              computational reproducibility, not flood validation.
            </li>
          </ul>
          <p>
            <a href={manifestUrl} download>Download source manifest (JSON)</a>
            {' · '}
            <a
              href="https://hyp3-docs.asf.alaska.edu/guides/rtc_product_guide/"
              target="_blank"
              rel="noopener noreferrer"
            >
              ASF RTC product guide
            </a>
          </p>
        </details>

        <p className="small-note">
          RTC product processed by ASF DAAC HyP3 2026 using GAMMA software.
          Contains modified Copernicus Sentinel data 2026, processed by ESA.
        </p>
      </div>
    </section>
  )
}

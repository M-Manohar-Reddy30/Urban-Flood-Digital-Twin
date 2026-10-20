import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from 'recharts'

type RainfallRecord = {
  date: string
  precipitation_mm_per_day: number
  valid_half_hourly_retrievals?: number
  status?: string
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
  records?: RainfallRecord[]
}

type Props = {
  rainfall: RainfallResponse | null
  rainfallError: string
}

function formatNumber(value: unknown, digits = 1): string {
  if (typeof value !== 'number' || !Number.isFinite(value)) return '—'
  return value.toLocaleString('en-IN', { maximumFractionDigits: digits })
}

export default function RainfallChart({ rainfall, rainfallError }: Props) {
  return (
    <>
      {rainfall?.records?.length ? (
        <div className="rainfall-chart">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={rainfall.records}
              margin={{ top: 12, right: 12, left: 0, bottom: 4 }}
            >
              <defs>
                <linearGradient id="rainfallFill" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="0%" stopColor="#2583d8" stopOpacity={0.3} />
                  <stop offset="95%" stopColor="#2583d8" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#dce5ef" />
              <XAxis
                dataKey="date"
                tickFormatter={(value: string) => value.slice(5)}
                minTickGap={35}
                tick={{ fontSize: 10 }}
              />
              <YAxis
                width={48}
                tick={{ fontSize: 10 }}
                label={{
                  value: 'mm/day',
                  angle: -90,
                  position: 'insideLeft',
                  style: { fontSize: 10 },
                }}
              />
              <Tooltip
                labelFormatter={(value) => `Date: ${value}`}
                formatter={(value) => [
                  `${formatNumber(value, 3)} mm/day`,
                  'Daily mean rate',
                ]}
              />
              <Area
                type="monotone"
                dataKey="precipitation_mm_per_day"
                name="Daily mean rate"
                stroke="#2583d8"
                strokeWidth={1.8}
                fill="url(#rainfallFill)"
                dot={false}
                activeDot={{ r: 4 }}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="rainfall-empty">
          {rainfallError || 'Loading historical rainfall observations…'}
        </p>
      )}

      <p className="rainfall-source">
        Source: NASA GPM IMERG · {rainfall?.start_date ?? '2024'} to {rainfall?.end_date ?? '2024'}
        {rainfall?.grid_point &&
          ` · Grid cell ${rainfall.grid_point.latitude}°N, ${rainfall.grid_point.longitude}°E`}
      </p>
      <p className="rainfall-source">
        {rainfall?.measurement_note ??
          'Values are daily mean precipitation rates in mm/day, not necessarily accumulated daily rainfall totals.'}
      </p>
    </>
  )
}

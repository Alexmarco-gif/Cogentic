'use client'

import { useEffect, useRef } from 'react'
import { Crosshair } from 'lucide-react'
import 'leaflet/dist/leaflet.css'
import type { MapRegion, DomainLayers } from '@/lib/hooks/useDomainMap'
import type { SignalSeverity } from '@/lib/hooks/useSignals'
import { getDomainFill } from '@/lib/domain-colors'

// ── Marker colors ─────────────────────────────────────────────────────────────

const SEVERITY_FILL: Record<SignalSeverity, string> = {
  critical: '#EF4444',
  high:     '#F97316',
  medium:   '#F59E0B',
  low:      '#64748B',
}

// ── Country outline & bounds — passed as props (default: auto-fit to markers) ─

// ── Props ─────────────────────────────────────────────────────────────────────

interface MapCanvasProps {
  regions: MapRegion[]
  activeRegionId: string | null
  layers: DomainLayers
  onRegionClick: (region: MapRegion) => void
  /** Optional GeoJSON feature for country outline */
  countryOutline?: GeoJSON.Feature | null
  /** Optional lat/lng bounds to fit the map to */
  mapBounds?: [[number, number], [number, number]] | null
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function MapCanvas({
  regions,
  activeRegionId,
  layers,
  onRegionClick,
  countryOutline = null,
  mapBounds = null,
}: MapCanvasProps) {
  const containerRef = useRef<HTMLDivElement>(null)
  const mapRef       = useRef<ReturnType<typeof import('leaflet')['map']> | null>(null)
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const markersRef   = useRef<any[]>([])
  const roRef        = useRef<ResizeObserver | null>(null)

  // ── Initialize map once ───────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return

    import('leaflet').then((L) => {
      if (!containerRef.current || mapRef.current) return

      const map = L.map(containerRef.current, {
        // ── Completely static — user cannot pan or zoom ──
        dragging:          false,
        scrollWheelZoom:   false,
        doubleClickZoom:   false,
        touchZoom:         false,
        boxZoom:           false,
        keyboard:          false,
        zoomControl:       false,
        attributionControl: false,
      })

      // Fit to provided bounds, or auto-fit to region markers
      if (mapBounds) {
        map.fitBounds(mapBounds, { padding: [24, 24] })
      } else if (regions.length > 0) {
        const lats = regions.map(r => r.lat)
        const lngs = regions.map(r => r.lng)
        map.fitBounds([[Math.min(...lats), Math.min(...lngs)], [Math.max(...lats), Math.max(...lngs)]], { padding: [24, 24] })
      } else {
        map.setView([9.08, 8.68], 6) // default world-ish view
      }

      // ── CartoDB Positron — clean white/light tiles ─────────────────────
      L.tileLayer(
        'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png',
        { subdomains: 'abcd', maxZoom: 19 },
      ).addTo(map)

      // ── Country boundary overlay (if provided) ─────────────────────────
      if (countryOutline) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        L.geoJSON(countryOutline as any, {
        style: {
          color:       '#6366F1',  // indigo border
          weight:      2.5,
          opacity:     0.85,
          fillColor:   '#6366F1',
          fillOpacity: 0.04,       // near-transparent fill just inside the border
          dashArray:   undefined,
          lineCap:     'round',
          lineJoin:    'round',
        },
        interactive: false,
      }).addTo(map)
      }

      // ── Attribution ────────────────────────────────────────────────────
      L.control
        .attribution({ position: 'bottomright', prefix: false })
        .addAttribution('© <a href="https://carto.com">CARTO</a>')
        .addTo(map)

      mapRef.current = map

      // Fix "half map" on first paint: Leaflet doesn't know the container
      // size until after the CSS layout pass, so force a size recalculation.
      setTimeout(() => { map.invalidateSize() }, 100)
      setTimeout(() => { map.invalidateSize() }, 400)

      // Keep map correct on any container resize (sidebar open/close, etc.)
      const ro = new ResizeObserver(() => map.invalidateSize({ debounceMoveend: true }))
      if (containerRef.current) ro.observe(containerRef.current)
      roRef.current = ro
    })

    return () => {
      roRef.current?.disconnect()
      roRef.current = null
      mapRef.current?.remove()
      mapRef.current = null
    }
  }, [])

  // ── Update markers when regions / layers / selection change ──────────────
  useEffect(() => {
    const map = mapRef.current
    if (!map) return

    import('leaflet').then((L) => {
      // Clear previous markers
      markersRef.current.forEach((m) => m.remove())
      markersRef.current = []

      regions.forEach((region) => {
        const isActive = region.id === activeRegionId

        const fillColor = layers.riskHeatmap
          ? SEVERITY_FILL[region.severity]
          : getDomainFill(region.domains[0]) ?? '#6366F1'

        const radius = layers.signalDensity
          ? region.signalCount * 9 + 10
          : 13

        // ── Opportunity outer ring ──────────────────────────────────────
        if (layers.opportunities && region.opportunityScore >= 70) {
          const outerRing = L.circleMarker([region.lat, region.lng], {
            radius:       radius + 8,
            fillColor:    '#10B981',
            color:        '#10B981',
            weight:       1.5,
            opacity:      0.45,
            fillOpacity:  0.07,
            interactive:  false,
          }).addTo(map)
          markersRef.current.push(outerRing)
        }

        // ── Active pulsing ring (drawn via DivIcon) ─────────────────────
        if (isActive) {
          const pulseSize = (radius + 10) * 2
          const pulseIcon = L.divIcon({
            className:  '',
            iconSize:   [pulseSize, pulseSize],
            iconAnchor: [pulseSize / 2, pulseSize / 2],
            html: `<div class="cogent-pulse-ring" style="width:${pulseSize}px;height:${pulseSize}px;border-color:${fillColor}"></div>`,
          })
          const pulseMarker = L.marker([region.lat, region.lng], {
            icon:        pulseIcon,
            interactive: false,
            zIndexOffset: -10,
          }).addTo(map)
          markersRef.current.push(pulseMarker)
        }

        // ── Main circle marker ──────────────────────────────────────────
        const marker = L.circleMarker([region.lat, region.lng], {
          radius,
          fillColor,
          color:       isActive ? '#1e293b' : '#ffffff',
          weight:      isActive ? 3 : 1.5,
          opacity:     1,
          fillOpacity: isActive ? 1 : 0.85,
        })
          .addTo(map)
          .on('click', () => onRegionClick(region))

        // Tooltip (dark pill, visible on light map)
        marker.bindTooltip(
          `<div class="cogent-tip-inner">${region.name}</div>`,
          {
            permanent:  false,
            direction:  'top',
            offset:     [0, -radius - 4],
            className:  'cogent-map-tooltip',
          },
        )

        markersRef.current.push(marker)
      })
    })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [regions, activeRegionId, layers])

  return (
    <>
      {/* ── CSS overrides for Leaflet elements ───────────────────────────── */}
      <style>{`
        /* Tooltip pill */
        .cogent-map-tooltip {
          background: transparent !important;
          border: none !important;
          box-shadow: none !important;
          padding: 0 !important;
        }
        .cogent-map-tooltip .leaflet-tooltip-content,
        .cogent-map-tooltip::before { display: none !important; }
        .cogent-tip-inner {
          background: #1e293b;
          border: 1px solid #334155;
          border-radius: 5px;
          color: #f1f5f9;
          font-size: 11px;
          font-weight: 600;
          padding: 3px 8px;
          white-space: nowrap;
          box-shadow: 0 4px 12px rgba(0,0,0,0.35);
        }
        /* Attribution */
        .leaflet-control-attribution {
          background: rgba(255,255,255,0.75) !important;
          color: #94a3b8 !important;
          font-size: 9px !important;
          backdrop-filter: blur(4px);
        }
        .leaflet-control-attribution a { color: #64748b !important; }
        /* ── Active marker pulse ring animation ─────────────── */
        .cogent-pulse-ring {
          border-radius: 50%;
          border: 2.5px solid;
          animation: cogent-pulse 1.6s ease-out infinite;
          box-sizing: border-box;
        }
        @keyframes cogent-pulse {
          0%   { transform: scale(0.6); opacity: 0.9; }
          100% { transform: scale(1.4); opacity: 0; }
        }
      `}</style>

      {/* ── Map container ─────────────────────────────────────────────────── */}
      <div className="relative h-full w-full">
        <div ref={containerRef} className="h-full w-full" />

        {/* Reset view button */}
        <button
          onClick={() => {
            if (mapRef.current && mapBounds) {
              mapRef.current.fitBounds(mapBounds, { padding: [24, 24], animate: false })
            } else if (mapRef.current && regions.length > 0) {
              const lats = regions.map(r => r.lat)
              const lngs = regions.map(r => r.lng)
              mapRef.current.fitBounds(
                [[Math.min(...lats), Math.min(...lngs)], [Math.max(...lats), Math.max(...lngs)]],
                { padding: [24, 24], animate: false }
              )
            }
          }}
          title="Reset map view"
          className="absolute bottom-3 right-3 z-[1000] flex h-8 w-8 items-center justify-center rounded-lg border border-slate-200 bg-white shadow-md transition-colors hover:bg-slate-50"
        >
          <Crosshair className="h-3.5 w-3.5 text-slate-600" />
        </button>
      </div>
    </>
  )
}

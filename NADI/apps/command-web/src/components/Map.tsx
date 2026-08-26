import { useRef, useEffect } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { FacilityItem } from '../api/client';
import { getStatusColor } from '../constants/status';

interface MapViewProps {
  facilities: FacilityItem[];
  selectedFacilityId: number | null;
  onSelectFacility: (id: number) => void;
}

// Dhar district, MP center coordinates
const DHAR_CENTER: [number, number] = [75.3, 22.6];
const DHAR_ZOOM = 9.5;

/**
 * MapLibre GL map with facility pins coloured by worst days-of-cover.
 * Free OSM tiles — no API key.
 */
export function MapView({ facilities, selectedFacilityId, onSelectFacility }: MapViewProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<Map<number, maplibregl.Marker>>(new Map());

  // Initialize map
  useEffect(() => {
    if (!containerRef.current || mapRef.current) return;

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: {
        version: 8,
        sources: {
          'carto-dark': {
            type: 'raster',
            tiles: [
              'https://tile.openstreetmap.org/{z}/{x}/{y}.png'
            ],
            tileSize: 256,
            attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
          },
        },
        layers: [
          {
            id: 'carto-dark-layer',
            type: 'raster',
            source: 'carto-dark',
            minzoom: 0,
            maxzoom: 19,
          },
        ],
      },
      center: DHAR_CENTER,
      zoom: DHAR_ZOOM,
    });

    map.addControl(new maplibregl.NavigationControl(), 'top-right');

    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Add/update markers when facilities change
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // Clear old markers
    markersRef.current.forEach((marker) => marker.remove());
    markersRef.current.clear();

    facilities.forEach((facility) => {
      const color = getStatusColor(facility.status);

      // Create custom marker element
      const el = document.createElement('div');
      el.style.width = '14px';
      el.style.height = '14px';
      el.style.cursor = 'pointer';
      // Store the facility ID so we can identify it later
      el.dataset.facilityId = String(facility.id);

      const dot = document.createElement('div');
      dot.className = 'marker-dot';
      dot.style.width = '100%';
      dot.style.height = '100%';
      dot.style.borderRadius = '50%';
      dot.style.background = color;
      dot.style.border = '2px solid rgba(255,255,255,0.9)';
      dot.style.boxShadow = `0 0 8px ${color}, 0 2px 4px rgba(0,0,0,0.3)`;
      dot.style.transition = 'transform 150ms ease, box-shadow 150ms ease';
      el.appendChild(dot);

      el.addEventListener('mouseenter', () => {
        dot.style.transform = 'scale(1.5)';
        dot.style.boxShadow = `0 0 16px ${color}, 0 4px 8px rgba(0,0,0,0.4)`;
      });
      el.addEventListener('mouseleave', () => {
        if (selectedFacilityId !== facility.id) {
          dot.style.transform = 'scale(1)';
          dot.style.boxShadow = `0 0 8px ${color}, 0 2px 4px rgba(0,0,0,0.3)`;
        }
      });

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([facility.lng, facility.lat])
        .addTo(map);

      // Click handler
      el.addEventListener('click', (e) => {
        e.stopPropagation();
        onSelectFacility(facility.id);
      });

      // Popup on hover
      const cbiText = facility.cbi != null
        ? `<span style="color:${color}; font-weight:700;">${Math.round(facility.cbi * 100)}%</span><span style="color:#94a3b8;"> CBI</span>`
        : `<span style="color:${color}; font-weight:700;">${facility.worstDaysOfCover != null ? Math.round(facility.worstDaysOfCover) + ' days' : '—'}</span><span style="color:#94a3b8;"> cover</span>`;

      const popup = new maplibregl.Popup({
        closeButton: false,
        closeOnClick: false,
        offset: 14,
      }).setHTML(`
        <div class="map-popup">
          <div class="map-popup__name">${facility.name}</div>
          <div class="map-popup__type">${facility.type.toUpperCase()}</div>
          <div style="margin-top:6px; font-size:0.8rem;">
            ${cbiText}
          </div>
        </div>
      `);

      el.addEventListener('mouseenter', () => {
        marker.setPopup(popup);
        marker.togglePopup();
      });
      el.addEventListener('mouseleave', () => {
        marker.togglePopup();
      });

      markersRef.current.set(facility.id, marker);
    });
  }, [facilities, onSelectFacility]);

  // Highlight selected facility
  useEffect(() => {
    markersRef.current.forEach((marker, id) => {
      const el = marker.getElement();
      const dot = el.querySelector('.marker-dot') as HTMLDivElement;
      if (!dot) return;
      
      if (id === selectedFacilityId) {
        dot.style.transform = 'scale(1.8)';
        el.style.zIndex = '100';
        dot.style.border = '3px solid #fff';

        // Pan to selected facility
        const lngLat = marker.getLngLat();
        mapRef.current?.flyTo({
          center: [lngLat.lng, lngLat.lat],
          zoom: Math.max(mapRef.current.getZoom(), 11),
          duration: 600,
        });
      } else {
        dot.style.transform = 'scale(1)';
        el.style.zIndex = '1';
        dot.style.border = '2px solid rgba(255,255,255,0.9)';
      }
    });
  }, [selectedFacilityId]);

  return (
    <div
      ref={containerRef}
      id="map-container"
      style={{ width: '100%', height: '100%' }}
    />
  );
}

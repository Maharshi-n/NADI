import { useRef, useEffect, useState } from 'react';
import * as maplibregl from 'maplibre-gl';
import 'maplibre-gl/dist/maplibre-gl.css';
import type { FacilityItem, TransferProposalItem } from '../api/client';
import { getStatusColor } from '../constants/status';

interface TransferMapProps {
  facilities: FacilityItem[];
  transfers: TransferProposalItem[];
}

const DHAR_CENTER: [number, number] = [75.3, 22.6];
const DHAR_ZOOM = 9.5;

export function TransferMap({ facilities, transfers }: TransferMapProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<Map<number, maplibregl.Marker>>(new Map());
  const [mapLoaded, setMapLoaded] = useState(false);

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
            attribution: '&copy; OpenStreetMap contributors',
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

    map.on('load', () => {
      // Add empty source and layer for transfer lines
      map.addSource('transfers-source', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] }
      });

      map.addLayer({
        id: 'transfers-layer',
        type: 'line',
        source: 'transfers-source',
        layout: {
          'line-join': 'round',
          'line-cap': 'round'
        },
        paint: {
          'line-color': 'var(--accent)',
          'line-width': 2,
          'line-opacity': 0.6,
          'line-dasharray': [2, 4]
        }
      });
      
      setMapLoaded(true);
    });

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Update facilities markers
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    markersRef.current.forEach(m => m.remove());
    markersRef.current.clear();

    facilities.forEach(fac => {
      const el = document.createElement('div');
      el.style.width = '12px';
      el.style.height = '12px';
      el.style.borderRadius = '50%';
      const color = getStatusColor(fac.status);
      el.style.background = color;
      el.style.border = '2px solid rgba(255,255,255,0.8)';
      
      const popup = new maplibregl.Popup({ offset: 12, closeButton: false })
        .setHTML(`<div class="map-popup"><div class="map-popup__name">${fac.name}</div></div>`);

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([fac.lng, fac.lat])
        .setPopup(popup)
        .addTo(map);

      el.addEventListener('mouseenter', () => marker.togglePopup());
      el.addEventListener('mouseleave', () => marker.togglePopup());

      markersRef.current.set(fac.id, marker);
    });
  }, [facilities]);

  // Update transfer lines
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapLoaded) return;

    const source = map.getSource('transfers-source') as maplibregl.GeoJSONSource;
    if (!source) return;

    const features = transfers.map(t => {
      const fromFac = facilities.find(f => f.id === t.fromFacilityId);
      const toFac = facilities.find(f => f.id === t.toFacilityId);
      
      if (!fromFac || !toFac) return null;

      return {
        type: 'Feature',
        geometry: {
          type: 'LineString',
          coordinates: [
            [fromFac.lng, fromFac.lat],
            [toFac.lng, toFac.lat]
          ]
        },
        properties: {
          drugName: t.drugName,
          quantity: t.quantity
        }
      };
    }).filter(Boolean) as any[];

    source.setData({
      type: 'FeatureCollection',
      features
    });

  }, [transfers, facilities]);

  return <div ref={containerRef} style={{ width: '100%', height: '100%' }} />;
}

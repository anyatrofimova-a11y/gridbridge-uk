/**
 * GridBridge UK - Real Map Grid Simulator
 */
import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline, Tooltip } from 'react-leaflet';
import {
  Zap, Wind, Sun, Flame, Atom, Leaf, Battery, Droplet, Factory,
  Activity, RefreshCw, Layers, Play, Pause, Clock, MapPin, Wifi, WifiOff,
} from 'lucide-react';

// =============================================================================
// Constants
// =============================================================================

const UK_CENTER = [54.5, -2.5];

const FUEL_CONFIG = {
  wind: { color: '#10b981', label: 'Wind' },
  solar: { color: '#fbbf24', label: 'Solar' },
  gas: { color: '#ef4444', label: 'Gas' },
  nuclear: { color: '#f59e0b', label: 'Nuclear' },
  biomass: { color: '#84cc16', label: 'Biomass' },
  battery: { color: '#8b5cf6', label: 'Battery' },
  hydro: { color: '#3b82f6', label: 'Hydro' },
  coal: { color: '#374151', label: 'Coal' },
  other: { color: '#6b7280', label: 'Other' },
};

// Default UK GSPs
const DEFAULT_GSPS = [
  { id: 'didcot', name: 'Didcot 400kV', coords: { lat: 51.62, lng: -1.27 }, voltage_kv: 400, headroom_mw: 120, load_mw: 850 },
  { id: 'london', name: 'London GSP', coords: { lat: 51.51, lng: -0.13 }, voltage_kv: 400, headroom_mw: 45, load_mw: 2100 },
  { id: 'manchester', name: 'Manchester GSP', coords: { lat: 53.48, lng: -2.24 }, voltage_kv: 400, headroom_mw: 85, load_mw: 1200 },
  { id: 'birmingham', name: 'Birmingham GSP', coords: { lat: 52.49, lng: -1.90 }, voltage_kv: 400, headroom_mw: 72, load_mw: 980 },
  { id: 'edinburgh', name: 'Edinburgh GSP', coords: { lat: 55.95, lng: -3.19 }, voltage_kv: 275, headroom_mw: 95, load_mw: 650 },
  { id: 'glasgow', name: 'Glasgow GSP', coords: { lat: 55.86, lng: -4.25 }, voltage_kv: 400, headroom_mw: 110, load_mw: 720 },
  { id: 'cardiff', name: 'Cardiff GSP', coords: { lat: 51.48, lng: -3.18 }, voltage_kv: 275, headroom_mw: 88, load_mw: 420 },
  { id: 'bristol', name: 'Bristol GSP', coords: { lat: 51.45, lng: -2.58 }, voltage_kv: 275, headroom_mw: 65, load_mw: 580 },
  { id: 'newcastle', name: 'Newcastle GSP', coords: { lat: 54.98, lng: -1.61 }, voltage_kv: 275, headroom_mw: 92, load_mw: 490 },
  { id: 'leeds', name: 'Leeds GSP', coords: { lat: 53.80, lng: -1.55 }, voltage_kv: 275, headroom_mw: 78, load_mw: 620 },
  { id: 'liverpool', name: 'Liverpool GSP', coords: { lat: 53.41, lng: -2.98 }, voltage_kv: 275, headroom_mw: 82, load_mw: 540 },
  { id: 'sheffield', name: 'Sheffield GSP', coords: { lat: 53.38, lng: -1.47 }, voltage_kv: 275, headroom_mw: 68, load_mw: 480 },
  { id: 'cambridge', name: 'Cambridge GSP', coords: { lat: 52.21, lng: 0.12 }, voltage_kv: 132, headroom_mw: 105, load_mw: 320 },
  { id: 'oxford', name: 'Oxford GSP', coords: { lat: 51.75, lng: -1.26 }, voltage_kv: 132, headroom_mw: 98, load_mw: 280 },
  { id: 'reading', name: 'Reading GSP', coords: { lat: 51.45, lng: -0.97 }, voltage_kv: 275, headroom_mw: 55, load_mw: 410 },
  { id: 'southampton', name: 'Southampton GSP', coords: { lat: 50.91, lng: -1.40 }, voltage_kv: 275, headroom_mw: 73, load_mw: 380 },
  { id: 'norwich', name: 'Norwich GSP', coords: { lat: 52.63, lng: 1.30 }, voltage_kv: 132, headroom_mw: 115, load_mw: 260 },
  { id: 'nottingham', name: 'Nottingham GSP', coords: { lat: 52.95, lng: -1.15 }, voltage_kv: 275, headroom_mw: 62, load_mw: 450 },
  { id: 'leicester', name: 'Leicester GSP', coords: { lat: 52.64, lng: -1.13 }, voltage_kv: 275, headroom_mw: 58, load_mw: 390 },
  { id: 'aberdeen', name: 'Aberdeen GSP', coords: { lat: 57.15, lng: -2.09 }, voltage_kv: 275, headroom_mw: 125, load_mw: 280 },
  { id: 'inverness', name: 'Inverness GSP', coords: { lat: 57.48, lng: -4.22 }, voltage_kv: 132, headroom_mw: 140, load_mw: 180 },
  { id: 'dundee', name: 'Dundee GSP', coords: { lat: 56.46, lng: -2.97 }, voltage_kv: 132, headroom_mw: 95, load_mw: 220 },
  { id: 'swansea', name: 'Swansea GSP', coords: { lat: 51.62, lng: -3.94 }, voltage_kv: 275, headroom_mw: 85, load_mw: 290 },
  { id: 'plymouth', name: 'Plymouth GSP', coords: { lat: 50.38, lng: -4.14 }, voltage_kv: 132, headroom_mw: 92, load_mw: 240 },
  { id: 'exeter', name: 'Exeter GSP', coords: { lat: 50.72, lng: -3.53 }, voltage_kv: 132, headroom_mw: 102, load_mw: 210 },
];

const DEFAULT_GENERATORS = [
  { id: 'drax', name: 'Drax Power Station', fuel_type: 'biomass', coords: { lat: 53.74, lng: -0.99 }, capacity_mw: 2595, output_mw: 1800 },
  { id: 'sizewell', name: 'Sizewell B', fuel_type: 'nuclear', coords: { lat: 52.21, lng: 1.62 }, capacity_mw: 1198, output_mw: 1150 },
  { id: 'hinkley', name: 'Hinkley Point B', fuel_type: 'nuclear', coords: { lat: 51.21, lng: -3.13 }, capacity_mw: 965, output_mw: 920 },
  { id: 'hornsea', name: 'Hornsea Wind Farm', fuel_type: 'wind', coords: { lat: 53.88, lng: 1.80 }, capacity_mw: 1218, output_mw: 850 },
  { id: 'dogger', name: 'Dogger Bank Wind', fuel_type: 'wind', coords: { lat: 54.75, lng: 2.20 }, capacity_mw: 1200, output_mw: 780 },
  { id: 'dinorwig', name: 'Dinorwig Hydro', fuel_type: 'hydro', coords: { lat: 53.12, lng: -4.11 }, capacity_mw: 1728, output_mw: 0 },
  { id: 'pembroke', name: 'Pembroke CCGT', fuel_type: 'gas', coords: { lat: 51.68, lng: -4.99 }, capacity_mw: 2180, output_mw: 1450 },
  { id: 'carrington', name: 'Carrington CCGT', fuel_type: 'gas', coords: { lat: 53.43, lng: -2.41 }, capacity_mw: 884, output_mw: 620 },
];

// =============================================================================
// Utility Functions
// =============================================================================

const formatMW = (mw) => {
  if (!mw && mw !== 0) return '—';
  if (Math.abs(mw) >= 1000) return `${(mw / 1000).toFixed(1)} GW`;
  return `${mw.toFixed(0)} MW`;
};

const getHeadroomColor = (headroom) => {
  if (headroom > 100) return '#22c55e';
  if (headroom > 50) return '#f59e0b';
  return '#ef4444';
};

// =============================================================================
// Main Component
// =============================================================================

const GridSimulatorMap = () => {
  const [isPlaying, setIsPlaying] = useState(true);
  const [layers, setLayers] = useState({
    generators: true,
    gridNodes: true,
  });

  const toggleLayer = (key) => {
    setLayers(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div style={{ height: '100vh', width: '100vw', display: 'flex', flexDirection: 'column', background: '#0f172a' }}>
      {/* Header */}
      <header style={{
        background: '#1e293b',
        borderBottom: '1px solid #334155',
        padding: '12px 16px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        zIndex: 1000
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <h1 style={{ fontSize: '20px', fontWeight: 'bold', color: 'white', display: 'flex', alignItems: 'center', gap: '8px', margin: 0 }}>
            <Zap style={{ color: '#38bdf8' }} size={24} />
            GridBridge Simulator
          </h1>
          <span style={{ color: '#94a3b8', fontSize: '14px' }}>UK Real-Time Grid</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            style={{
              padding: '8px',
              borderRadius: '4px',
              background: isPlaying ? '#16a34a' : '#475569',
              color: 'white',
              border: 'none',
              cursor: 'pointer'
            }}
          >
            {isPlaying ? <Pause size={16} /> : <Play size={16} />}
          </button>
        </div>
      </header>

      {/* Map Container */}
      <div style={{ flex: 1, position: 'relative' }}>
        <MapContainer
          center={UK_CENTER}
          zoom={6}
          style={{ height: '100%', width: '100%' }}
          scrollWheelZoom={true}
        >
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          />

          {/* Grid Nodes (GSPs) */}
          {layers.gridNodes && DEFAULT_GSPS.map((node) => (
            <CircleMarker
              key={node.id}
              center={[node.coords.lat, node.coords.lng]}
              radius={8}
              pathOptions={{
                color: '#fff',
                fillColor: getHeadroomColor(node.headroom_mw),
                fillOpacity: 0.9,
                weight: 2,
              }}
            >
              <Tooltip direction="top" offset={[0, -10]}>
                <div style={{ fontSize: '12px' }}>
                  <div style={{ fontWeight: 'bold' }}>{node.name}</div>
                  <div>Headroom: {node.headroom_mw} MW</div>
                  <div>Load: {node.load_mw} MW</div>
                  <div>{node.voltage_kv} kV</div>
                </div>
              </Tooltip>
            </CircleMarker>
          ))}

          {/* Generators */}
          {layers.generators && DEFAULT_GENERATORS.map((gen) => {
            const config = FUEL_CONFIG[gen.fuel_type] || FUEL_CONFIG.other;
            const radius = Math.max(6, Math.sqrt(gen.capacity_mw) / 5);
            return (
              <CircleMarker
                key={gen.id}
                center={[gen.coords.lat, gen.coords.lng]}
                radius={radius}
                pathOptions={{
                  color: config.color,
                  fillColor: config.color,
                  fillOpacity: 0.7,
                  weight: 2,
                }}
              >
                <Tooltip direction="top" offset={[0, -10]}>
                  <div style={{ fontSize: '12px' }}>
                    <div style={{ fontWeight: 'bold' }}>{gen.name}</div>
                    <div>{formatMW(gen.output_mw)} / {formatMW(gen.capacity_mw)}</div>
                    <div style={{ textTransform: 'capitalize' }}>{gen.fuel_type}</div>
                  </div>
                </Tooltip>
              </CircleMarker>
            );
          })}
        </MapContainer>

        {/* Layer Controls Panel */}
        <div style={{
          position: 'absolute',
          top: '16px',
          left: '16px',
          zIndex: 1000,
          background: 'rgba(30, 41, 59, 0.95)',
          borderRadius: '8px',
          padding: '16px',
          width: '200px',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)'
        }}>
          <h3 style={{ color: 'white', fontSize: '14px', fontWeight: '600', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Layers size={16} style={{ color: '#38bdf8' }} />
            Layers
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <label style={{ color: '#e2e8f0', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={layers.gridNodes}
                onChange={() => toggleLayer('gridNodes')}
                style={{ accentColor: '#38bdf8' }}
              />
              Grid Nodes (GSPs)
            </label>
            <label style={{ color: '#e2e8f0', fontSize: '13px', display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
              <input
                type="checkbox"
                checked={layers.generators}
                onChange={() => toggleLayer('generators')}
                style={{ accentColor: '#38bdf8' }}
              />
              Generators
            </label>
          </div>
        </div>

        {/* Stats Panel */}
        <div style={{
          position: 'absolute',
          top: '16px',
          right: '16px',
          zIndex: 1000,
          background: 'rgba(30, 41, 59, 0.95)',
          borderRadius: '8px',
          padding: '16px',
          width: '220px',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)'
        }}>
          <h3 style={{ color: 'white', fontSize: '14px', fontWeight: '600', marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Activity size={16} style={{ color: '#38bdf8' }} />
            Grid Status
          </h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#e2e8f0', fontSize: '13px' }}>
              <span>GSP Nodes:</span>
              <span style={{ fontWeight: '600' }}>{DEFAULT_GSPS.length}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#e2e8f0', fontSize: '13px' }}>
              <span>Generators:</span>
              <span style={{ fontWeight: '600' }}>{DEFAULT_GENERATORS.length}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#e2e8f0', fontSize: '13px' }}>
              <span>Total Capacity:</span>
              <span style={{ fontWeight: '600' }}>{formatMW(DEFAULT_GENERATORS.reduce((sum, g) => sum + g.capacity_mw, 0))}</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', color: '#e2e8f0', fontSize: '13px' }}>
              <span>Current Output:</span>
              <span style={{ fontWeight: '600', color: '#22c55e' }}>{formatMW(DEFAULT_GENERATORS.reduce((sum, g) => sum + g.output_mw, 0))}</span>
            </div>
          </div>
        </div>

        {/* Legend */}
        <div style={{
          position: 'absolute',
          bottom: '16px',
          left: '16px',
          zIndex: 1000,
          background: 'rgba(30, 41, 59, 0.95)',
          borderRadius: '8px',
          padding: '12px 16px',
          boxShadow: '0 4px 6px rgba(0, 0, 0, 0.3)'
        }}>
          <div style={{ color: '#94a3b8', fontSize: '11px', marginBottom: '8px' }}>HEADROOM</div>
          <div style={{ display: 'flex', gap: '12px' }}>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#e2e8f0', fontSize: '12px' }}>
              <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#22c55e' }}></span>
              High (&gt;100MW)
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#e2e8f0', fontSize: '12px' }}>
              <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#f59e0b' }}></span>
              Medium
            </span>
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#e2e8f0', fontSize: '12px' }}>
              <span style={{ width: '10px', height: '10px', borderRadius: '50%', background: '#ef4444' }}></span>
              Low
            </span>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GridSimulatorMap;

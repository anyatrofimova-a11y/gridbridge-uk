/**
 * GridBridge UK - Grid Simulator Map
 * Built on the same pattern as SimpleMap (proven working)
 */
import React, { useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline } from 'react-leaflet';

// UK GSPs with coordinates
const GSPS = [
  { id: 'didcot', name: 'Didcot 400kV', lat: 51.62, lng: -1.27, kv: 400, headroom: 120, load: 850 },
  { id: 'london', name: 'London GSP', lat: 51.51, lng: -0.13, kv: 400, headroom: 45, load: 2100 },
  { id: 'manchester', name: 'Manchester GSP', lat: 53.48, lng: -2.24, kv: 400, headroom: 85, load: 1200 },
  { id: 'birmingham', name: 'Birmingham GSP', lat: 52.49, lng: -1.90, kv: 400, headroom: 72, load: 980 },
  { id: 'edinburgh', name: 'Edinburgh GSP', lat: 55.95, lng: -3.19, kv: 275, headroom: 95, load: 650 },
  { id: 'glasgow', name: 'Glasgow GSP', lat: 55.86, lng: -4.25, kv: 400, headroom: 110, load: 720 },
  { id: 'cardiff', name: 'Cardiff GSP', lat: 51.48, lng: -3.18, kv: 275, headroom: 88, load: 420 },
  { id: 'bristol', name: 'Bristol GSP', lat: 51.45, lng: -2.58, kv: 275, headroom: 65, load: 580 },
  { id: 'newcastle', name: 'Newcastle GSP', lat: 54.98, lng: -1.61, kv: 275, headroom: 92, load: 490 },
  { id: 'leeds', name: 'Leeds GSP', lat: 53.80, lng: -1.55, kv: 275, headroom: 78, load: 620 },
  { id: 'liverpool', name: 'Liverpool GSP', lat: 53.41, lng: -2.98, kv: 275, headroom: 82, load: 540 },
  { id: 'sheffield', name: 'Sheffield GSP', lat: 53.38, lng: -1.47, kv: 275, headroom: 68, load: 480 },
  { id: 'cambridge', name: 'Cambridge GSP', lat: 52.21, lng: 0.12, kv: 132, headroom: 105, load: 320 },
  { id: 'oxford', name: 'Oxford GSP', lat: 51.75, lng: -1.26, kv: 132, headroom: 98, load: 280 },
  { id: 'reading', name: 'Reading GSP', lat: 51.45, lng: -0.97, kv: 275, headroom: 55, load: 410 },
  { id: 'southampton', name: 'Southampton GSP', lat: 50.91, lng: -1.40, kv: 275, headroom: 73, load: 380 },
  { id: 'norwich', name: 'Norwich GSP', lat: 52.63, lng: 1.30, kv: 132, headroom: 115, load: 260 },
  { id: 'nottingham', name: 'Nottingham GSP', lat: 52.95, lng: -1.15, kv: 275, headroom: 62, load: 450 },
  { id: 'leicester', name: 'Leicester GSP', lat: 52.64, lng: -1.13, kv: 275, headroom: 58, load: 390 },
  { id: 'aberdeen', name: 'Aberdeen GSP', lat: 57.15, lng: -2.09, kv: 275, headroom: 125, load: 280 },
  { id: 'inverness', name: 'Inverness GSP', lat: 57.48, lng: -4.22, kv: 132, headroom: 140, load: 180 },
  { id: 'dundee', name: 'Dundee GSP', lat: 56.46, lng: -2.97, kv: 132, headroom: 95, load: 220 },
  { id: 'swansea', name: 'Swansea GSP', lat: 51.62, lng: -3.94, kv: 275, headroom: 85, load: 290 },
  { id: 'plymouth', name: 'Plymouth GSP', lat: 50.38, lng: -4.14, kv: 132, headroom: 92, load: 240 },
  { id: 'exeter', name: 'Exeter GSP', lat: 50.72, lng: -3.53, kv: 132, headroom: 102, load: 210 },
];

// UK generators
const GENERATORS = [
  { id: 'drax', name: 'Drax Power Station', fuel: 'biomass', lat: 53.74, lng: -0.99, cap: 2595, out: 1800, color: '#84cc16' },
  { id: 'sizewell', name: 'Sizewell B', fuel: 'nuclear', lat: 52.21, lng: 1.62, cap: 1198, out: 1150, color: '#f59e0b' },
  { id: 'hinkley', name: 'Hinkley Point B', fuel: 'nuclear', lat: 51.21, lng: -3.13, cap: 965, out: 920, color: '#f59e0b' },
  { id: 'hornsea', name: 'Hornsea Wind Farm', fuel: 'wind', lat: 53.88, lng: 1.80, cap: 1218, out: 850, color: '#10b981' },
  { id: 'dogger', name: 'Dogger Bank Wind', fuel: 'wind', lat: 54.75, lng: 2.20, cap: 1200, out: 780, color: '#10b981' },
  { id: 'dinorwig', name: 'Dinorwig Hydro', fuel: 'hydro', lat: 53.12, lng: -4.11, cap: 1728, out: 0, color: '#3b82f6' },
  { id: 'pembroke', name: 'Pembroke CCGT', fuel: 'gas', lat: 51.68, lng: -4.99, cap: 2180, out: 1450, color: '#ef4444' },
  { id: 'carrington', name: 'Carrington CCGT', fuel: 'gas', lat: 53.43, lng: -2.41, cap: 884, out: 620, color: '#ef4444' },
  { id: 'walney', name: 'Walney Wind Farm', fuel: 'wind', lat: 54.04, lng: -3.55, cap: 659, out: 420, color: '#10b981' },
  { id: 'london_array', name: 'London Array', fuel: 'wind', lat: 51.63, lng: 1.35, cap: 630, out: 380, color: '#10b981' },
  { id: 'torness', name: 'Torness Nuclear', fuel: 'nuclear', lat: 55.97, lng: -2.40, cap: 1185, out: 1100, color: '#f59e0b' },
  { id: 'hunterston', name: 'Hunterston B', fuel: 'nuclear', lat: 55.72, lng: -4.90, cap: 965, out: 890, color: '#f59e0b' },
  { id: 'cottam', name: 'Cottam CCGT', fuel: 'gas', lat: 53.30, lng: -0.78, cap: 440, out: 310, color: '#ef4444' },
  { id: 'damhead', name: 'Damhead Creek', fuel: 'gas', lat: 51.43, lng: 0.58, cap: 805, out: 550, color: '#ef4444' },
  { id: 'whitelee', name: 'Whitelee Wind', fuel: 'wind', lat: 55.68, lng: -4.27, cap: 539, out: 340, color: '#10b981' },
];

// Interconnectors
const INTERCONNECTORS = [
  { name: 'IFA (France)', from: [50.92, 1.14], to: [49.5, 1.5], flow: 1000, color: '#06b6d4' },
  { name: 'BritNed (Netherlands)', from: [51.45, 1.35], to: [52.0, 4.0], flow: 600, color: '#06b6d4' },
  { name: 'Moyle (Ireland)', from: [55.20, -5.80], to: [55.10, -6.10], flow: 250, color: '#06b6d4' },
  { name: 'EWIC (Ireland)', from: [53.30, -4.60], to: [53.30, -6.10], flow: 350, color: '#06b6d4' },
  { name: 'NSL (Norway)', from: [55.10, 1.10], to: [58.0, 5.0], flow: 700, color: '#06b6d4' },
];

function headroomColor(h) {
  if (h > 100) return '#22c55e';
  if (h > 50) return '#f59e0b';
  return '#ef4444';
}

function fmtMW(mw) {
  if (mw >= 1000) return (mw / 1000).toFixed(1) + ' GW';
  return mw + ' MW';
}

const GridSimulatorMap = () => {
  const [selected, setSelected] = useState(null);
  const [showGSP, setShowGSP] = useState(true);
  const [showGen, setShowGen] = useState(true);
  const [showIC, setShowIC] = useState(true);

  const totalCap = GENERATORS.reduce((s, g) => s + g.cap, 0);
  const totalOut = GENERATORS.reduce((s, g) => s + g.out, 0);

  return (
    <div style={{ height: '100vh', width: '100vw', background: '#0f172a' }}>
      <MapContainer
        center={[54.5, -2.5]}
        zoom={6}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={true}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />

        {/* Interconnectors */}
        {showIC && INTERCONNECTORS.map((ic, i) => (
          <Polyline
            key={'ic-' + i}
            positions={[ic.from, ic.to]}
            pathOptions={{ color: ic.color, weight: 3, dashArray: '8 4', opacity: 0.7 }}
          >
            <Popup>
              <b>{ic.name}</b><br />
              Flow: {fmtMW(ic.flow)}
            </Popup>
          </Polyline>
        ))}

        {/* GSP Nodes */}
        {showGSP && GSPS.map((gsp) => (
          <CircleMarker
            key={gsp.id}
            center={[gsp.lat, gsp.lng]}
            radius={8}
            pathOptions={{
              color: '#ffffff',
              fillColor: headroomColor(gsp.headroom),
              fillOpacity: 0.9,
              weight: 2,
            }}
            eventHandlers={{ click: () => setSelected(gsp) }}
          >
            <Popup>
              <b>{gsp.name}</b><br />
              Voltage: {gsp.kv} kV<br />
              Headroom: {gsp.headroom} MW<br />
              Load: {gsp.load} MW
            </Popup>
          </CircleMarker>
        ))}

        {/* Generators */}
        {showGen && GENERATORS.map((gen) => (
          <CircleMarker
            key={gen.id}
            center={[gen.lat, gen.lng]}
            radius={Math.max(6, Math.sqrt(gen.cap) / 5)}
            pathOptions={{
              color: gen.color,
              fillColor: gen.color,
              fillOpacity: 0.7,
              weight: 2,
            }}
            eventHandlers={{ click: () => setSelected(gen) }}
          >
            <Popup>
              <b>{gen.name}</b><br />
              Fuel: {gen.fuel}<br />
              Output: {fmtMW(gen.out)} / {fmtMW(gen.cap)}
            </Popup>
          </CircleMarker>
        ))}
      </MapContainer>

      {/* Overlay: Header */}
      <div style={{
        position: 'fixed', top: 0, left: 0, right: 0, zIndex: 1000,
        background: 'rgba(15, 23, 42, 0.9)', backdropFilter: 'blur(8px)',
        padding: '12px 20px', display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        borderBottom: '1px solid rgba(255,255,255,0.1)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <span style={{ fontSize: '20px', fontWeight: 'bold', color: '#38bdf8' }}>⚡</span>
          <span style={{ fontSize: '18px', fontWeight: 'bold', color: 'white' }}>GridBridge Simulator</span>
          <span style={{ fontSize: '13px', color: '#94a3b8' }}>UK Real-Time Grid</span>
        </div>
        <div style={{ display: 'flex', gap: '16px', fontSize: '13px', color: '#e2e8f0' }}>
          <span>Capacity: <b style={{ color: '#38bdf8' }}>{fmtMW(totalCap)}</b></span>
          <span>Output: <b style={{ color: '#22c55e' }}>{fmtMW(totalOut)}</b></span>
          <span>GSPs: <b>{GSPS.length}</b></span>
          <span>Generators: <b>{GENERATORS.length}</b></span>
        </div>
      </div>

      {/* Overlay: Layer Controls */}
      <div style={{
        position: 'fixed', top: 60, left: 16, zIndex: 1000,
        background: 'rgba(15, 23, 42, 0.92)', backdropFilter: 'blur(8px)',
        borderRadius: '8px', padding: '14px', width: '180px',
        border: '1px solid rgba(255,255,255,0.1)',
      }}>
        <div style={{ color: '#94a3b8', fontSize: '11px', fontWeight: 600, marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Layers</div>
        {[
          { label: 'Grid Nodes', checked: showGSP, set: setShowGSP, dot: '#22c55e' },
          { label: 'Generators', checked: showGen, set: setShowGen, dot: '#ef4444' },
          { label: 'Interconnectors', checked: showIC, set: setShowIC, dot: '#06b6d4' },
        ].map((l) => (
          <label key={l.label} style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#e2e8f0', fontSize: '13px', cursor: 'pointer', marginBottom: '6px' }}>
            <input type="checkbox" checked={l.checked} onChange={() => l.set(!l.checked)} style={{ accentColor: '#38bdf8' }} />
            <span style={{ width: 8, height: 8, borderRadius: '50%', background: l.dot, display: 'inline-block' }}></span>
            {l.label}
          </label>
        ))}
      </div>

      {/* Overlay: Legend */}
      <div style={{
        position: 'fixed', bottom: 16, left: 16, zIndex: 1000,
        background: 'rgba(15, 23, 42, 0.92)', backdropFilter: 'blur(8px)',
        borderRadius: '8px', padding: '10px 14px',
        border: '1px solid rgba(255,255,255,0.1)',
      }}>
        <div style={{ color: '#94a3b8', fontSize: '10px', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Headroom</div>
        <div style={{ display: 'flex', gap: '12px' }}>
          {[
            { label: 'High (>100MW)', color: '#22c55e' },
            { label: 'Medium', color: '#f59e0b' },
            { label: 'Low (<50MW)', color: '#ef4444' },
          ].map((l) => (
            <span key={l.label} style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#e2e8f0', fontSize: '11px' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: l.color, display: 'inline-block' }}></span>
              {l.label}
            </span>
          ))}
        </div>
        <div style={{ color: '#94a3b8', fontSize: '10px', marginTop: '8px', marginBottom: '4px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Generators</div>
        <div style={{ display: 'flex', gap: '10px', flexWrap: 'wrap' }}>
          {[
            { label: 'Wind', color: '#10b981' },
            { label: 'Nuclear', color: '#f59e0b' },
            { label: 'Gas', color: '#ef4444' },
            { label: 'Hydro', color: '#3b82f6' },
            { label: 'Biomass', color: '#84cc16' },
          ].map((l) => (
            <span key={l.label} style={{ display: 'flex', alignItems: 'center', gap: '4px', color: '#e2e8f0', fontSize: '11px' }}>
              <span style={{ width: 8, height: 8, borderRadius: '50%', background: l.color, display: 'inline-block' }}></span>
              {l.label}
            </span>
          ))}
        </div>
      </div>

      {/* Overlay: Selection Detail */}
      {selected && (
        <div style={{
          position: 'fixed', top: 60, right: 16, zIndex: 1000,
          background: 'rgba(15, 23, 42, 0.92)', backdropFilter: 'blur(8px)',
          borderRadius: '8px', padding: '14px', width: '220px',
          border: '1px solid rgba(255,255,255,0.1)',
        }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <span style={{ color: 'white', fontWeight: 'bold', fontSize: '14px' }}>{selected.name}</span>
            <button onClick={() => setSelected(null)} style={{ color: '#94a3b8', background: 'none', border: 'none', cursor: 'pointer', fontSize: '16px' }}>✕</button>
          </div>
          <div style={{ color: '#e2e8f0', fontSize: '12px', lineHeight: '1.8' }}>
            {selected.kv && <div>Voltage: <b>{selected.kv} kV</b></div>}
            {selected.headroom !== undefined && <div>Headroom: <b style={{ color: headroomColor(selected.headroom) }}>{selected.headroom} MW</b></div>}
            {selected.load && <div>Load: <b>{selected.load} MW</b></div>}
            {selected.fuel && <div>Fuel: <b style={{ textTransform: 'capitalize' }}>{selected.fuel}</b></div>}
            {selected.cap && <div>Capacity: <b>{fmtMW(selected.cap)}</b></div>}
            {selected.out !== undefined && <div>Output: <b style={{ color: '#22c55e' }}>{fmtMW(selected.out)}</b></div>}
          </div>
        </div>
      )}
    </div>
  );
};

export default GridSimulatorMap;

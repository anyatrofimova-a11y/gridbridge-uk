/**
 * GridBridge UK - Real Map Grid Simulator
 *
 * Interactive Leaflet map with real UK geography showing:
 * - Power generators with animated icons
 * - Grid nodes (GSPs/BSPs) with headroom indicators
 * - Interconnector flows
 * - Carbon intensity overlays
 * - Market intelligence panels
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline, useMap, Tooltip } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import {
  Zap, Wind, Sun, Flame, Atom, Leaf, Battery, Droplet, Factory,
  ArrowLeftRight, Activity, TrendingUp, TrendingDown, RefreshCw, Layers,
  Eye, EyeOff, Play, Pause, Settings, ChevronDown, ChevronUp, Clock,
  Target, Wifi, WifiOff, AlertCircle, MapPin,
} from 'lucide-react';

// =============================================================================
// Constants
// =============================================================================

const UK_CENTER = [54.5, -2.5];
const UK_BOUNDS = [[49.5, -8], [60, 2]];

const FUEL_CONFIG = {
  wind: { color: '#10b981', icon: Wind, label: 'Wind' },
  solar: { color: '#fbbf24', icon: Sun, label: 'Solar' },
  gas: { color: '#ef4444', icon: Flame, label: 'Gas' },
  nuclear: { color: '#f59e0b', icon: Atom, label: 'Nuclear' },
  biomass: { color: '#84cc16', icon: Leaf, label: 'Biomass' },
  battery: { color: '#8b5cf6', icon: Battery, label: 'Battery' },
  hydro: { color: '#3b82f6', icon: Droplet, label: 'Hydro' },
  coal: { color: '#374151', icon: Factory, label: 'Coal' },
  imports: { color: '#06b6d4', icon: ArrowLeftRight, label: 'Imports' },
  other: { color: '#6b7280', icon: Zap, label: 'Other' },
};

const CARBON_COLORS = {
  'very low': '#22c55e',
  'low': '#84cc16',
  'moderate': '#f59e0b',
  'high': '#f97316',
  'very high': '#ef4444',
};

// Interconnector endpoints (country coordinates)
const INTERCONNECTOR_ENDPOINTS = {
  FR: [49.5, 1.5],
  BE: [51.2, 3.0],
  NL: [52.5, 4.5],
  NO: [58.0, 5.0],
  DK: [55.5, 8.0],
  IE: [53.5, -8.5],
};

// =============================================================================
// Utility Functions
// =============================================================================

const formatMW = (mw) => {
  if (!mw && mw !== 0) return '—';
  if (Math.abs(mw) >= 1000) return `${(mw / 1000).toFixed(1)} GW`;
  return `${mw.toFixed(0)} MW`;
};

// =============================================================================
// Custom Hooks
// =============================================================================

const useGridData = (refreshInterval = 60000) => {
  const [data, setData] = useState({
    snapshot: null,
    overlay: null,
    opportunities: [],
    loading: true,
    error: null,
    lastUpdate: null,
  });

  const fetchData = useCallback(async () => {
    try {
      const [snapshotRes, overlayRes, oppsRes] = await Promise.all([
        fetch('/api/aggregated/snapshot').then(r => r.ok ? r.json() : null),
        fetch('/api/overlay/state').then(r => r.ok ? r.json() : null),
        fetch('/api/aggregated/flexibility-opportunities').then(r => r.ok ? r.json() : null),
      ]);

      setData({
        snapshot: snapshotRes,
        overlay: overlayRes,
        opportunities: oppsRes?.opportunities || [],
        loading: false,
        error: null,
        lastUpdate: new Date(),
      });
    } catch (err) {
      setData(prev => ({ ...prev, loading: false, error: err.message }));
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, refreshInterval);
    return () => clearInterval(interval);
  }, [fetchData, refreshInterval]);

  return { ...data, refresh: fetchData };
};

// =============================================================================
// Map Components
// =============================================================================

// Generator marker on the map
const GeneratorMarker = ({ generator, onClick }) => {
  const config = FUEL_CONFIG[generator.fuel_type] || FUEL_CONFIG.other;
  const capFactor = (generator.output_mw || 0) / (generator.capacity_mw || 100);
  const radius = Math.max(5, Math.min(20, Math.sqrt(generator.capacity_mw || 50) / 2));

  if (!generator.coords?.lat || !generator.coords?.lng) return null;

  return (
    <CircleMarker
      center={[generator.coords.lat, generator.coords.lng]}
      radius={radius}
      pathOptions={{
        color: config.color,
        fillColor: config.color,
        fillOpacity: Math.max(0.3, capFactor),
        weight: 2,
      }}
      eventHandlers={{ click: () => onClick?.(generator) }}
    >
      <Tooltip direction="top" offset={[0, -10]} opacity={0.9}>
        <div className="text-xs">
          <div className="font-bold">{generator.name}</div>
          <div>{formatMW(generator.output_mw)} / {formatMW(generator.capacity_mw)}</div>
          <div className="capitalize">{generator.fuel_type}</div>
        </div>
      </Tooltip>
    </CircleMarker>
  );
};

// Grid node marker (GSP/BSP)
const GridNodeMarker = ({ node, onClick }) => {
  const headroom = node.headroom_mw || 0;
  let color = '#ef4444'; // Low
  if (headroom > 100) color = '#22c55e'; // High
  else if (headroom > 50) color = '#f59e0b'; // Medium

  if (!node.coords?.lat || !node.coords?.lng) return null;

  return (
    <CircleMarker
      center={[node.coords.lat, node.coords.lng]}
      radius={8}
      pathOptions={{
        color: '#fff',
        fillColor: color,
        fillOpacity: 0.9,
        weight: 2,
      }}
      eventHandlers={{ click: () => onClick?.(node) }}
    >
      <Tooltip direction="top" offset={[0, -10]} opacity={0.9}>
        <div className="text-xs">
          <div className="font-bold">{node.name}</div>
          <div>Headroom: {node.headroom_mw} MW</div>
          <div>Load: {node.load_mw} MW</div>
          <div>{node.voltage_kv} kV</div>
        </div>
      </Tooltip>
    </CircleMarker>
  );
};

// Interconnector line
const InterconnectorLine = ({ interconnector, onClick }) => {
  const flow = interconnector.flow_mw || 0;
  const isImport = flow > 0;
  const color = isImport ? '#22c55e' : flow < 0 ? '#ef4444' : '#6b7280';

  if (!interconnector.coords?.lat || !interconnector.coords?.lng) return null;

  const ukPoint = [interconnector.coords.lat, interconnector.coords.lng];
  const foreignPoint = INTERCONNECTOR_ENDPOINTS[interconnector.country_code] || [51, 2];

  return (
    <>
      <Polyline
        positions={[ukPoint, foreignPoint]}
        pathOptions={{
          color: color,
          weight: Math.max(2, Math.abs(flow) / 300),
          opacity: 0.7,
          dashArray: isImport ? null : '10, 10',
        }}
        eventHandlers={{ click: () => onClick?.(interconnector) }}
      >
        <Tooltip>
          <div className="text-xs">
            <div className="font-bold">{interconnector.name}</div>
            <div>{formatMW(Math.abs(flow))} {isImport ? 'Import' : 'Export'}</div>
            <div>To/From: {interconnector.country_code}</div>
          </div>
        </Tooltip>
      </Polyline>
      <CircleMarker
        center={ukPoint}
        radius={6}
        pathOptions={{
          color: '#fff',
          fillColor: color,
          fillOpacity: 1,
          weight: 2,
        }}
      />
    </>
  );
};

// Carbon intensity region overlay
const CarbonRegionMarker = ({ region }) => {
  const color = CARBON_COLORS[region.index?.toLowerCase()] || '#6b7280';

  if (!region.coords?.lat || !region.coords?.lng) return null;

  return (
    <CircleMarker
      center={[region.coords.lat, region.coords.lng]}
      radius={40}
      pathOptions={{
        color: color,
        fillColor: color,
        fillOpacity: 0.15,
        weight: 1,
      }}
    >
      <Tooltip>
        <div className="text-xs">
          <div className="font-bold">{region.name}</div>
          <div>{region.intensity} gCO2/kWh</div>
          <div className="capitalize">{region.index}</div>
        </div>
      </Tooltip>
    </CircleMarker>
  );
};

// Map bounds fitter
const FitBounds = () => {
  const map = useMap();
  useEffect(() => {
    map.fitBounds(UK_BOUNDS);
  }, [map]);
  return null;
};

// =============================================================================
// Side Panels
// =============================================================================

const LiveStatsPanel = ({ snapshot, isConnected }) => {
  if (!snapshot) return null;

  const genByFuel = snapshot.generation?.by_fuel || {};
  const totalGen = snapshot.generation?.total_mw || 0;

  return (
    <div className="bg-slate-800/95 backdrop-blur rounded-lg p-4 space-y-4 shadow-xl">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-white flex items-center gap-2">
          <Activity size={16} className="text-sky-400" />
          Live Grid Status
        </h3>
        <div className={`flex items-center gap-1 text-xs ${isConnected ? 'text-green-400' : 'text-red-400'}`}>
          {isConnected ? <Wifi size={12} /> : <WifiOff size={12} />}
          {isConnected ? 'Live' : 'Offline'}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-2">
        <div className="bg-slate-700/50 p-2 rounded">
          <div className="text-slate-400 text-xs">Generation</div>
          <div className="text-white font-bold text-lg">{formatMW(totalGen)}</div>
        </div>
        <div className="bg-slate-700/50 p-2 rounded">
          <div className="text-slate-400 text-xs">Demand</div>
          <div className="text-white font-bold text-lg">{formatMW(snapshot.demand?.total_mw)}</div>
        </div>
        <div className="bg-slate-700/50 p-2 rounded">
          <div className="text-slate-400 text-xs">Carbon</div>
          <div className={`font-bold text-lg ${
            snapshot.carbon?.index === 'very low' ? 'text-green-400' :
            snapshot.carbon?.index === 'low' ? 'text-lime-400' :
            snapshot.carbon?.index === 'moderate' ? 'text-amber-400' :
            'text-red-400'
          }`}>
            {snapshot.carbon?.intensity_gco2_kwh || 0} <span className="text-xs font-normal">g/kWh</span>
          </div>
        </div>
        <div className="bg-slate-700/50 p-2 rounded">
          <div className="text-slate-400 text-xs">Net Import</div>
          <div className={`font-bold text-lg ${
            (snapshot.interconnectors?.net_imports_mw || 0) >= 0 ? 'text-green-400' : 'text-red-400'
          }`}>
            {formatMW(snapshot.interconnectors?.net_imports_mw)}
          </div>
        </div>
      </div>

      <div className="space-y-1">
        <div className="text-slate-400 text-xs mb-2">Generation Mix</div>
        {Object.entries(genByFuel)
          .sort(([, a], [, b]) => b - a)
          .slice(0, 6)
          .map(([fuel, mw]) => {
            const config = FUEL_CONFIG[fuel] || FUEL_CONFIG.other;
            const pct = totalGen > 0 ? (mw / totalGen) * 100 : 0;
            return (
              <div key={fuel} className="flex items-center gap-2">
                <config.icon size={12} style={{ color: config.color }} />
                <span className="text-xs text-slate-300 w-12 capitalize truncate">{config.label}</span>
                <div className="flex-1 h-2 bg-slate-700 rounded overflow-hidden">
                  <div
                    className="h-full transition-all duration-500"
                    style={{ width: `${pct}%`, backgroundColor: config.color }}
                  />
                </div>
                <span className="text-xs text-slate-400 w-10 text-right">{pct.toFixed(0)}%</span>
              </div>
            );
          })}
      </div>

      {(snapshot.markets?.ets_price_eur || snapshot.markets?.agile_price_gbp) && (
        <div className="pt-2 border-t border-slate-700">
          <div className="text-slate-400 text-xs mb-2">Market Prices</div>
          <div className="grid grid-cols-2 gap-2 text-sm">
            {snapshot.markets?.agile_price_gbp && (
              <div>
                <span className="text-slate-500">Agile:</span>
                <span className="text-white ml-1">{snapshot.markets.agile_price_gbp.toFixed(1)}p/kWh</span>
              </div>
            )}
            {snapshot.markets?.ets_price_eur && (
              <div>
                <span className="text-slate-500">ETS:</span>
                <span className="text-white ml-1">€{snapshot.markets.ets_price_eur}/t</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

const LayerControlsPanel = ({ layers, onToggle }) => {
  const [expanded, setExpanded] = useState(true);

  const layerConfig = [
    { key: 'generators', label: 'Generators', icon: Zap, color: 'sky' },
    { key: 'interconnectors', label: 'Interconnectors', icon: ArrowLeftRight, color: 'cyan' },
    { key: 'gridNodes', label: 'Grid Nodes', icon: MapPin, color: 'purple' },
    { key: 'carbonRegions', label: 'Carbon Intensity', icon: Activity, color: 'green' },
  ];

  return (
    <div className="bg-slate-800/95 backdrop-blur rounded-lg overflow-hidden shadow-xl">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full p-3 flex items-center justify-between text-white hover:bg-slate-700/50"
      >
        <span className="flex items-center gap-2 font-medium">
          <Layers size={16} className="text-sky-400" />
          Layers
        </span>
        {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {expanded && (
        <div className="p-3 pt-0 space-y-2">
          {layerConfig.map(({ key, label, icon: Icon, color }) => (
            <button
              key={key}
              onClick={() => onToggle(key)}
              className={`w-full flex items-center gap-2 px-3 py-2 rounded text-sm transition-colors ${
                layers[key]
                  ? `bg-${color}-600 text-white`
                  : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
              }`}
            >
              <Icon size={14} />
              <span className="flex-1 text-left">{label}</span>
              {layers[key] ? <Eye size={14} /> : <EyeOff size={14} />}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

const SelectionPanel = ({ selection, onClose }) => {
  if (!selection) return null;

  const isGenerator = selection.fuel_type !== undefined;
  const isNode = selection.node_type !== undefined;
  const isInterconnector = selection.country_code !== undefined;

  return (
    <div className="bg-slate-800/95 backdrop-blur rounded-lg p-4 shadow-xl">
      <div className="flex items-start justify-between mb-3">
        <h3 className="font-semibold text-white">{selection.name}</h3>
        <button onClick={onClose} className="text-slate-400 hover:text-white text-xl">&times;</button>
      </div>

      <div className="space-y-2 text-sm">
        {isGenerator && (
          <>
            <div className="flex justify-between">
              <span className="text-slate-400">Type</span>
              <span className="text-white capitalize">{selection.fuel_type}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Output</span>
              <span className="text-white">{formatMW(selection.output_mw)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Capacity</span>
              <span className="text-white">{formatMW(selection.capacity_mw)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Capacity Factor</span>
              <span className="text-white">
                {(((selection.output_mw || 0) / (selection.capacity_mw || 1)) * 100).toFixed(1)}%
              </span>
            </div>
          </>
        )}

        {isNode && (
          <>
            <div className="flex justify-between">
              <span className="text-slate-400">Type</span>
              <span className="text-white uppercase">{selection.node_type}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Voltage</span>
              <span className="text-white">{selection.voltage_kv} kV</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Headroom</span>
              <span className={`font-medium ${
                selection.headroom_mw > 100 ? 'text-green-400' :
                selection.headroom_mw > 50 ? 'text-amber-400' : 'text-red-400'
              }`}>
                {selection.headroom_mw} MW
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Current Load</span>
              <span className="text-white">{selection.load_mw} MW</span>
            </div>
          </>
        )}

        {isInterconnector && (
          <>
            <div className="flex justify-between">
              <span className="text-slate-400">Country</span>
              <span className="text-white">{selection.country_code}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Capacity</span>
              <span className="text-white">{formatMW(selection.capacity_mw)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Flow</span>
              <span className={selection.flow_mw >= 0 ? 'text-green-400' : 'text-red-400'}>
                {formatMW(Math.abs(selection.flow_mw))} {selection.flow_mw >= 0 ? '(Import)' : '(Export)'}
              </span>
            </div>
          </>
        )}
      </div>

      <div className="mt-4 flex gap-2">
        <button className="flex-1 py-2 px-3 bg-sky-600 hover:bg-sky-500 rounded text-white text-sm">
          Analyze
        </button>
        <button className="flex-1 py-2 px-3 bg-slate-700 hover:bg-slate-600 rounded text-white text-sm">
          Add to Report
        </button>
      </div>
    </div>
  );
};

const FlexOpportunitiesPanel = ({ opportunities }) => {
  if (!opportunities?.length) return null;

  const actionConfig = {
    INCREASE_LOAD: { color: 'green', icon: TrendingUp },
    REDUCE_LOAD: { color: 'red', icon: TrendingDown },
    OFFER_DSR: { color: 'purple', icon: Activity },
    CHARGE_STORAGE: { color: 'blue', icon: Battery },
  };

  return (
    <div className="bg-slate-800/95 backdrop-blur rounded-lg p-4 shadow-xl">
      <h3 className="font-semibold text-white flex items-center gap-2 mb-3">
        <Target size={16} className="text-green-400" />
        Flex Opportunities
      </h3>

      <div className="space-y-2">
        {opportunities.slice(0, 3).map((opp, i) => {
          const config = actionConfig[opp.action] || actionConfig.INCREASE_LOAD;
          const Icon = config.icon;
          return (
            <div key={i} className="p-2 rounded bg-slate-700/50 border border-slate-600">
              <div className="flex items-center justify-between">
                <span className="flex items-center gap-1 text-white text-sm font-medium">
                  <Icon size={14} className={`text-${config.color}-400`} />
                  {opp.action.replace(/_/g, ' ')}
                </span>
                <span className="text-xs bg-slate-600 px-1.5 py-0.5 rounded text-slate-300">
                  {(opp.confidence * 100).toFixed(0)}%
                </span>
              </div>
              <p className="text-xs text-slate-400 mt-1">{opp.reason}</p>
            </div>
          );
        })}
      </div>
    </div>
  );
};

// =============================================================================
// Main Component
// =============================================================================

const GridSimulatorMap = () => {
  const { snapshot, overlay, opportunities, loading, error, lastUpdate, refresh } = useGridData();
  const [selection, setSelection] = useState(null);
  const [isPlaying, setIsPlaying] = useState(true);
  const [layers, setLayers] = useState({
    generators: true,
    interconnectors: true,
    gridNodes: true,
    carbonRegions: true,
  });

  // Extract data from overlay
  const generators = useMemo(() => overlay?.layers?.generators?.data || [], [overlay]);
  const interconnectors = useMemo(() => overlay?.layers?.interconnectors?.data || [], [overlay]);
  const gridNodes = useMemo(() => overlay?.layers?.grid_nodes?.data || [], [overlay]);
  const carbonRegions = useMemo(() => overlay?.layers?.carbon_intensity?.data || [], [overlay]);

  const toggleLayer = (key) => {
    setLayers(prev => ({ ...prev, [key]: !prev[key] }));
  };

  return (
    <div className="h-screen w-screen bg-slate-900 flex flex-col">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 px-4 py-3 flex items-center justify-between z-50">
        <div className="flex items-center gap-4">
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Zap className="text-sky-400" />
            GridBridge Simulator
          </h1>
          <span className="text-slate-400 text-sm hidden md:block">UK Real-Time Grid</span>
        </div>

        <div className="flex items-center gap-3">
          {lastUpdate && (
            <span className="text-slate-400 text-xs flex items-center gap-1">
              <Clock size={12} />
              {lastUpdate.toLocaleTimeString()}
            </span>
          )}

          <button
            onClick={() => setIsPlaying(!isPlaying)}
            className={`p-2 rounded ${isPlaying ? 'bg-green-600' : 'bg-slate-700'} text-white`}
          >
            {isPlaying ? <Pause size={16} /> : <Play size={16} />}
          </button>

          <button
            onClick={refresh}
            disabled={loading}
            className="p-2 rounded bg-slate-700 hover:bg-slate-600 text-white"
          >
            <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
          </button>

          <button className="p-2 rounded bg-slate-700 hover:bg-slate-600 text-white">
            <Settings size={16} />
          </button>
        </div>
      </header>

      {/* Error banner */}
      {error && (
        <div className="bg-red-900/50 border-b border-red-700 px-4 py-2 text-red-300 text-sm flex items-center gap-2">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      {/* Main content */}
      <div className="flex-1 relative">
        {/* Map */}
        <MapContainer
          center={UK_CENTER}
          zoom={6}
          className="h-full w-full"
          zoomControl={false}
          style={{ background: '#0f172a' }}
        >
          <FitBounds />

          {/* Dark tile layer */}
          <TileLayer
            url="https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png"
            attribution='&copy; <a href="https://carto.com/">CARTO</a>'
          />

          {/* Carbon intensity regions (background) */}
          {layers.carbonRegions && carbonRegions.map((region, i) => (
            <CarbonRegionMarker key={`carbon-${i}`} region={region} />
          ))}

          {/* Interconnector lines */}
          {layers.interconnectors && interconnectors.map((ic, i) => (
            <InterconnectorLine
              key={`ic-${i}`}
              interconnector={ic}
              onClick={setSelection}
            />
          ))}

          {/* Grid nodes */}
          {layers.gridNodes && gridNodes.map((node, i) => (
            <GridNodeMarker
              key={`node-${i}`}
              node={node}
              onClick={setSelection}
            />
          ))}

          {/* Generators */}
          {layers.generators && generators.slice(0, 200).map((gen, i) => (
            <GeneratorMarker
              key={`gen-${i}`}
              generator={gen}
              onClick={setSelection}
            />
          ))}
        </MapContainer>

        {/* Left panel overlay */}
        <div className="absolute top-4 left-4 z-[1000] w-72 space-y-4">
          <LiveStatsPanel snapshot={snapshot} isConnected={!error && !loading} />
          <LayerControlsPanel layers={layers} onToggle={toggleLayer} />
        </div>

        {/* Right panel overlay */}
        <div className="absolute top-4 right-4 z-[1000] w-72 space-y-4">
          {selection ? (
            <SelectionPanel selection={selection} onClose={() => setSelection(null)} />
          ) : (
            <div className="bg-slate-800/95 backdrop-blur rounded-lg p-4 text-center text-slate-500 shadow-xl">
              <MapPin size={24} className="mx-auto mb-2 opacity-50" />
              <p className="text-sm">Click on map elements to view details</p>
            </div>
          )}
          <FlexOpportunitiesPanel opportunities={opportunities} />
        </div>

        {/* Loading overlay */}
        {loading && !overlay && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-900/80 z-[2000]">
            <div className="text-center">
              <RefreshCw className="animate-spin text-sky-400 mx-auto mb-2" size={32} />
              <p className="text-slate-300">Loading grid data...</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default GridSimulatorMap;

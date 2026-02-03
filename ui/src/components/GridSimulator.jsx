/**
 * GridBridge UK - Advanced Grid Simulator Interface
 *
 * A sophisticated real-time grid visualization inspired by kilowatts-grid
 * with enhanced market intelligence, multi-layer data overlays, and
 * dispatch simulation tools.
 */

import React, { useState, useEffect, useCallback, useRef, useMemo } from 'react';
import {
  MapPin, Zap, Wind, Sun, Flame, Atom, Leaf, Battery, Droplet, Factory,
  ArrowLeftRight, Activity, TrendingUp, TrendingDown, RefreshCw, Layers,
  Eye, EyeOff, Info, AlertCircle, Play, Pause, Settings, ChevronDown,
  ChevronUp, BarChart3, Clock, DollarSign, Gauge, Target, Wifi, WifiOff,
  Maximize2, Minimize2, Filter, Download, Share2, AlertTriangle,
} from 'lucide-react';

// =============================================================================
// Constants
// =============================================================================

const UK_BOUNDS = { north: 60.0, south: 49.5, east: 2.0, west: -8.0 };
const MAP_WIDTH = 400;
const MAP_HEIGHT = 500;

const FUEL_CONFIG = {
  wind: { color: '#10b981', icon: Wind, label: 'Wind', animate: true },
  solar: { color: '#fbbf24', icon: Sun, label: 'Solar', animate: true },
  gas: { color: '#ef4444', icon: Flame, label: 'Gas (CCGT)', animate: false },
  nuclear: { color: '#f59e0b', icon: Atom, label: 'Nuclear', animate: true },
  biomass: { color: '#84cc16', icon: Leaf, label: 'Biomass', animate: false },
  battery: { color: '#8b5cf6', icon: Battery, label: 'Battery', animate: true },
  hydro: { color: '#3b82f6', icon: Droplet, label: 'Hydro', animate: true },
  coal: { color: '#374151', icon: Factory, label: 'Coal', animate: false },
  imports: { color: '#06b6d4', icon: ArrowLeftRight, label: 'Imports', animate: false },
  other: { color: '#6b7280', icon: Zap, label: 'Other', animate: false },
};

const CARBON_LEVELS = {
  'very low': { color: '#22c55e', bg: '#dcfce7', label: 'Very Low', max: 100 },
  'low': { color: '#84cc16', bg: '#ecfccb', label: 'Low', max: 150 },
  'moderate': { color: '#f59e0b', bg: '#fef3c7', label: 'Moderate', max: 200 },
  'high': { color: '#f97316', bg: '#ffedd5', label: 'High', max: 250 },
  'very high': { color: '#ef4444', bg: '#fee2e2', label: 'Very High', max: 999 },
};

// =============================================================================
// Utility Functions
// =============================================================================

const latLngToXY = (lat, lng) => {
  const x = ((lng - UK_BOUNDS.west) / (UK_BOUNDS.east - UK_BOUNDS.west)) * MAP_WIDTH;
  const y = ((UK_BOUNDS.north - lat) / (UK_BOUNDS.north - UK_BOUNDS.south)) * MAP_HEIGHT;
  return { x, y };
};

const formatMW = (mw) => {
  if (mw >= 1000) return `${(mw / 1000).toFixed(1)} GW`;
  return `${mw.toFixed(0)} MW`;
};

const formatPrice = (price, currency = '£') => {
  if (price === null || price === undefined) return '—';
  return `${currency}${price.toFixed(2)}`;
};

// =============================================================================
// API Hooks
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
// Animated Generator Icon
// =============================================================================

const AnimatedGeneratorIcon = ({ generator, scale = 1, onClick, selected }) => {
  const [rotation, setRotation] = useState(0);
  const config = FUEL_CONFIG[generator.fuel_type] || FUEL_CONFIG.other;
  const Icon = config.icon;

  // Animation for wind turbines, solar tracking, etc.
  useEffect(() => {
    if (!config.animate || generator.output_mw <= 0) return;

    const speed = Math.max(0.5, (generator.output_mw / (generator.capacity_mw || 100)) * 3);
    const interval = setInterval(() => {
      setRotation(prev => (prev + speed) % 360);
    }, 50);

    return () => clearInterval(interval);
  }, [config.animate, generator.output_mw, generator.capacity_mw]);

  const size = Math.max(12, Math.min(32, Math.sqrt(generator.capacity_mw || 50) * scale));
  const pos = latLngToXY(generator.coords?.lat || 54, generator.coords?.lng || -2);

  // Capacity factor for opacity
  const capFactor = Math.max(0.3, (generator.output_mw || 0) / (generator.capacity_mw || 100));

  return (
    <g
      transform={`translate(${pos.x}, ${pos.y})`}
      onClick={() => onClick?.(generator)}
      className="cursor-pointer transition-transform hover:scale-125"
      style={{ opacity: capFactor }}
    >
      {/* Glow effect when selected */}
      {selected && (
        <circle r={size + 8} fill={config.color} opacity={0.3}>
          <animate attributeName="r" values={`${size + 5};${size + 12};${size + 5}`} dur="1.5s" repeatCount="indefinite" />
        </circle>
      )}

      {/* Background circle */}
      <circle r={size / 2 + 4} fill="#1e293b" stroke={config.color} strokeWidth={2} />

      {/* Icon with animation */}
      <g transform={config.animate && generator.fuel_type === 'wind' ? `rotate(${rotation})` : ''}>
        <foreignObject x={-size / 2} y={-size / 2} width={size} height={size}>
          <div className="w-full h-full flex items-center justify-center">
            <Icon size={size * 0.7} color={config.color} />
          </div>
        </foreignObject>
      </g>

      {/* Balancing indicator */}
      {(generator.bids_mw > 0 || generator.offers_mw > 0) && (
        <circle
          cx={size / 2}
          cy={-size / 2}
          r={4}
          fill={generator.bids_mw > generator.offers_mw ? '#ef4444' : '#22c55e'}
        />
      )}

      <title>{`${generator.name}: ${formatMW(generator.output_mw || 0)} / ${formatMW(generator.capacity_mw || 0)}`}</title>
    </g>
  );
};

// =============================================================================
// Interconnector Cable
// =============================================================================

const InterconnectorCable = ({ interconnector, onClick }) => {
  const pos = latLngToXY(interconnector.coords?.lat || 51, interconnector.coords?.lng || 0);
  const flow = interconnector.flow_mw || 0;
  const isImport = flow > 0;
  const color = isImport ? '#22c55e' : flow < 0 ? '#ef4444' : '#6b7280';

  // Cable endpoint (outside UK bounds based on country)
  const countryOffsets = {
    FR: { x: 50, y: 100 },
    BE: { x: 70, y: 50 },
    NL: { x: 90, y: 30 },
    NO: { x: 30, y: -80 },
    DK: { x: 80, y: -40 },
    IE: { x: -60, y: 20 },
  };
  const offset = countryOffsets[interconnector.country_code] || { x: 50, y: 50 };

  return (
    <g onClick={() => onClick?.(interconnector)} className="cursor-pointer">
      {/* Cable line */}
      <line
        x1={pos.x}
        y1={pos.y}
        x2={pos.x + offset.x}
        y2={pos.y + offset.y}
        stroke={color}
        strokeWidth={Math.max(2, Math.abs(flow) / 500)}
        strokeDasharray={isImport ? "none" : "5,5"}
        opacity={0.7}
      >
        {Math.abs(flow) > 0 && (
          <animate
            attributeName="stroke-dashoffset"
            values={isImport ? "0;-20" : "0;20"}
            dur="1s"
            repeatCount="indefinite"
          />
        )}
      </line>

      {/* Connection point */}
      <circle cx={pos.x} cy={pos.y} r={6} fill={color} stroke="#fff" strokeWidth={1} />

      {/* Country label */}
      <text
        x={pos.x + offset.x * 0.7}
        y={pos.y + offset.y * 0.7}
        fill="#94a3b8"
        fontSize={10}
        textAnchor="middle"
      >
        {interconnector.country_code}
      </text>

      {/* Flow label */}
      <text
        x={pos.x + offset.x * 0.4}
        y={pos.y + offset.y * 0.4 + 12}
        fill={color}
        fontSize={9}
        textAnchor="middle"
        fontWeight="bold"
      >
        {formatMW(Math.abs(flow))}
      </text>

      <title>{`${interconnector.name}: ${formatMW(flow)} (${isImport ? 'Import' : 'Export'})`}</title>
    </g>
  );
};

// =============================================================================
// Grid Node (GSP/BSP)
// =============================================================================

const GridNodeMarker = ({ node, onClick, selected }) => {
  const pos = latLngToXY(node.coords?.lat || 54, node.coords?.lng || -2);
  const headroom = node.headroom_mw || 0;

  let color = '#ef4444'; // Low
  if (headroom > 100) color = '#22c55e'; // High
  else if (headroom > 50) color = '#f59e0b'; // Medium

  const size = node.node_type === 'gsp' ? 8 : 6;

  return (
    <g
      transform={`translate(${pos.x}, ${pos.y})`}
      onClick={() => onClick?.(node)}
      className="cursor-pointer"
    >
      {selected && (
        <circle r={size + 6} fill={color} opacity={0.3}>
          <animate attributeName="opacity" values="0.3;0.6;0.3" dur="1s" repeatCount="indefinite" />
        </circle>
      )}

      <rect
        x={-size}
        y={-size}
        width={size * 2}
        height={size * 2}
        fill={color}
        stroke="#fff"
        strokeWidth={1}
        transform="rotate(45)"
      />

      <title>{`${node.name}: ${headroom} MW headroom`}</title>
    </g>
  );
};

// =============================================================================
// Carbon Intensity Region
// =============================================================================

const CarbonRegion = ({ region }) => {
  const pos = latLngToXY(region.coords?.lat || 54, region.coords?.lng || -2);
  const level = CARBON_LEVELS[region.index?.toLowerCase()] || CARBON_LEVELS.moderate;

  return (
    <circle
      cx={pos.x}
      cy={pos.y}
      r={35}
      fill={level.bg}
      opacity={0.4}
      stroke={level.color}
      strokeWidth={1}
    >
      <title>{`${region.name}: ${region.intensity} gCO2/kWh (${level.label})`}</title>
    </circle>
  );
};

// =============================================================================
// UK Map SVG Path
// =============================================================================

const UKMapPath = () => {
  // Simplified UK coastline
  const path = `
    M 180 30 L 200 20 L 230 15 L 260 25 L 290 20 L 320 35
    L 340 60 L 355 100 L 350 150 L 370 200
    L 365 260 L 345 320 L 320 380 L 290 420
    L 250 450 L 200 470 L 150 460 L 100 430
    L 70 390 L 50 340 L 55 280 L 75 220
    L 65 160 L 85 100 L 120 60 L 150 40 Z
    M 30 200 L 50 180 L 70 190 L 60 220 L 35 230 Z
  `;

  return (
    <>
      <defs>
        <linearGradient id="ukGradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#334155" />
          <stop offset="100%" stopColor="#1e293b" />
        </linearGradient>
        <filter id="glow">
          <feGaussianBlur stdDeviation="2" result="coloredBlur" />
          <feMerge>
            <feMergeNode in="coloredBlur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>
      <path
        d={path}
        fill="url(#ukGradient)"
        stroke="#475569"
        strokeWidth={2}
      />
    </>
  );
};

// =============================================================================
// Live Stats Panel
// =============================================================================

const LiveStatsPanel = ({ snapshot, isConnected }) => {
  if (!snapshot) return null;

  const genByFuel = snapshot.generation?.by_fuel || {};
  const totalGen = snapshot.generation?.total_mw || 0;

  return (
    <div className="bg-slate-800/90 backdrop-blur rounded-lg p-4 space-y-4">
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

      {/* Key metrics */}
      <div className="grid grid-cols-2 gap-2">
        <div className="bg-slate-700/50 p-2 rounded">
          <div className="text-slate-400 text-xs">Generation</div>
          <div className="text-white font-bold text-lg">{formatMW(totalGen)}</div>
        </div>
        <div className="bg-slate-700/50 p-2 rounded">
          <div className="text-slate-400 text-xs">Demand</div>
          <div className="text-white font-bold text-lg">{formatMW(snapshot.demand?.total_mw || 0)}</div>
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
            {formatMW(snapshot.interconnectors?.net_imports_mw || 0)}
          </div>
        </div>
      </div>

      {/* Generation mix bars */}
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
                <span className="text-xs text-slate-300 w-14 capitalize truncate">{config.label}</span>
                <div className="flex-1 h-2 bg-slate-700 rounded overflow-hidden">
                  <div
                    className="h-full transition-all duration-500"
                    style={{ width: `${pct}%`, backgroundColor: config.color }}
                  />
                </div>
                <span className="text-xs text-slate-400 w-14 text-right">{pct.toFixed(1)}%</span>
              </div>
            );
          })}
      </div>

      {/* Market prices */}
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

// =============================================================================
// Layer Controls Panel
// =============================================================================

const LayerControlsPanel = ({ layers, onToggle, onOpacityChange }) => {
  const [expanded, setExpanded] = useState(true);

  const layerConfig = [
    { key: 'generators', label: 'Generators', icon: Zap },
    { key: 'interconnectors', label: 'Interconnectors', icon: ArrowLeftRight },
    { key: 'gridNodes', label: 'Grid Nodes', icon: MapPin },
    { key: 'carbonRegions', label: 'Carbon Intensity', icon: Activity },
    { key: 'constraints', label: 'Constraints', icon: AlertTriangle },
  ];

  return (
    <div className="bg-slate-800/90 backdrop-blur rounded-lg overflow-hidden">
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
          {layerConfig.map(({ key, label, icon: Icon }) => (
            <div key={key} className="flex items-center gap-2">
              <button
                onClick={() => onToggle(key)}
                className={`flex-1 flex items-center gap-2 px-2 py-1.5 rounded text-sm transition-colors ${
                  layers[key]?.visible
                    ? 'bg-sky-600 text-white'
                    : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
                }`}
              >
                <Icon size={14} />
                <span>{label}</span>
              </button>
              {layers[key]?.visible && (
                <input
                  type="range"
                  min="0"
                  max="100"
                  value={(layers[key]?.opacity || 1) * 100}
                  onChange={(e) => onOpacityChange(key, e.target.value / 100)}
                  className="w-16 h-1"
                />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

// =============================================================================
// Flexibility Opportunities Panel
// =============================================================================

const FlexOpportunitiesPanel = ({ opportunities }) => {
  if (!opportunities?.length) return null;

  const actionConfig = {
    INCREASE_LOAD: { color: 'green', icon: TrendingUp, label: 'Increase Load' },
    REDUCE_LOAD: { color: 'red', icon: TrendingDown, label: 'Reduce Load' },
    OFFER_DSR: { color: 'purple', icon: Activity, label: 'Offer DSR' },
    CHARGE_STORAGE: { color: 'blue', icon: Battery, label: 'Charge Storage' },
  };

  return (
    <div className="bg-slate-800/90 backdrop-blur rounded-lg p-4 space-y-3">
      <h3 className="font-semibold text-white flex items-center gap-2">
        <Target size={16} className="text-green-400" />
        Flex Opportunities
      </h3>

      {opportunities.slice(0, 3).map((opp, i) => {
        const config = actionConfig[opp.action] || actionConfig.INCREASE_LOAD;
        return (
          <div
            key={i}
            className={`p-2 rounded border border-${config.color}-600/50 bg-${config.color}-900/20`}
          >
            <div className="flex items-center justify-between">
              <span className="flex items-center gap-1 text-white text-sm font-medium">
                <config.icon size={14} className={`text-${config.color}-400`} />
                {config.label}
              </span>
              <span className="text-xs bg-slate-700 px-1.5 py-0.5 rounded text-slate-300">
                {(opp.confidence * 100).toFixed(0)}%
              </span>
            </div>
            <p className="text-xs text-slate-400 mt-1">{opp.reason}</p>
          </div>
        );
      })}
    </div>
  );
};

// =============================================================================
// Selection Detail Panel
// =============================================================================

const SelectionDetailPanel = ({ selection, onClose }) => {
  if (!selection) return null;

  const isGenerator = selection.fuel_type !== undefined;
  const isNode = selection.node_type !== undefined;
  const isInterconnector = selection.country_code !== undefined;

  return (
    <div className="bg-slate-800/95 backdrop-blur rounded-lg p-4 border border-slate-600">
      <div className="flex items-start justify-between mb-3">
        <h3 className="font-semibold text-white">{selection.name}</h3>
        <button onClick={onClose} className="text-slate-400 hover:text-white">&times;</button>
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
              <span className="text-white">{formatMW(selection.output_mw || 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Capacity</span>
              <span className="text-white">{formatMW(selection.capacity_mw || 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Capacity Factor</span>
              <span className="text-white">
                {((selection.output_mw / (selection.capacity_mw || 1)) * 100).toFixed(1)}%
              </span>
            </div>
            {selection.bids_mw > 0 && (
              <div className="flex justify-between text-red-400">
                <span>Bids</span>
                <span>{formatMW(selection.bids_mw)}</span>
              </div>
            )}
            {selection.offers_mw > 0 && (
              <div className="flex justify-between text-green-400">
                <span>Offers</span>
                <span>{formatMW(selection.offers_mw)}</span>
              </div>
            )}
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
              <span className={`${selection.headroom_mw > 100 ? 'text-green-400' : selection.headroom_mw > 50 ? 'text-amber-400' : 'text-red-400'}`}>
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
              <span className="text-white">{formatMW(selection.capacity_mw || 0)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-slate-400">Flow</span>
              <span className={selection.flow_mw >= 0 ? 'text-green-400' : 'text-red-400'}>
                {formatMW(Math.abs(selection.flow_mw || 0))} {selection.flow_mw >= 0 ? '(Import)' : '(Export)'}
              </span>
            </div>
          </>
        )}
      </div>

      <div className="mt-3 pt-3 border-t border-slate-700 flex gap-2">
        <button className="flex-1 py-1.5 px-2 bg-sky-600 hover:bg-sky-500 rounded text-white text-xs">
          View Details
        </button>
        <button className="flex-1 py-1.5 px-2 bg-slate-700 hover:bg-slate-600 rounded text-white text-xs">
          Add to Analysis
        </button>
      </div>
    </div>
  );
};

// =============================================================================
// Main Grid Simulator Component
// =============================================================================

const GridSimulator = () => {
  const { snapshot, overlay, opportunities, loading, error, lastUpdate, refresh } = useGridData();
  const [selection, setSelection] = useState(null);
  const [isPlaying, setIsPlaying] = useState(true);
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [layers, setLayers] = useState({
    generators: { visible: true, opacity: 1 },
    interconnectors: { visible: true, opacity: 1 },
    gridNodes: { visible: true, opacity: 0.8 },
    carbonRegions: { visible: true, opacity: 0.5 },
    constraints: { visible: false, opacity: 1 },
  });

  const svgRef = useRef(null);

  // Extract data from overlay
  const generators = useMemo(() =>
    overlay?.layers?.generators?.data || [], [overlay]);
  const interconnectors = useMemo(() =>
    overlay?.layers?.interconnectors?.data || [], [overlay]);
  const gridNodes = useMemo(() =>
    overlay?.layers?.grid_nodes?.data || [], [overlay]);
  const carbonRegions = useMemo(() =>
    overlay?.layers?.carbon_intensity?.data || [], [overlay]);

  const toggleLayer = (key) => {
    setLayers(prev => ({
      ...prev,
      [key]: { ...prev[key], visible: !prev[key]?.visible }
    }));
  };

  const setLayerOpacity = (key, opacity) => {
    setLayers(prev => ({
      ...prev,
      [key]: { ...prev[key], opacity }
    }));
  };

  // Handle wheel zoom
  const handleWheel = useCallback((e) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? 0.9 : 1.1;
    setZoom(prev => Math.max(0.5, Math.min(3, prev * delta)));
  }, []);

  return (
    <div className="bg-slate-900 min-h-screen">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 px-4 py-3">
        <div className="max-w-[1800px] mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <Zap className="text-sky-400" />
              GridBridge Simulator
            </h1>
            <span className="text-slate-400 text-sm">UK Real-Time Grid Visualization</span>
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
              title={isPlaying ? 'Pause updates' : 'Resume updates'}
            >
              {isPlaying ? <Pause size={16} /> : <Play size={16} />}
            </button>

            <button
              onClick={refresh}
              disabled={loading}
              className="p-2 rounded bg-slate-700 hover:bg-slate-600 text-white"
              title="Refresh data"
            >
              <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
            </button>

            <button className="p-2 rounded bg-slate-700 hover:bg-slate-600 text-white" title="Settings">
              <Settings size={16} />
            </button>
          </div>
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
      <div className="flex h-[calc(100vh-60px)]">
        {/* Left panel */}
        <div className="w-80 p-4 space-y-4 overflow-y-auto border-r border-slate-700">
          <LiveStatsPanel snapshot={snapshot} isConnected={!error && !loading} />
          <LayerControlsPanel
            layers={layers}
            onToggle={toggleLayer}
            onOpacityChange={setLayerOpacity}
          />
          <FlexOpportunitiesPanel opportunities={opportunities} />
        </div>

        {/* Map area */}
        <div className="flex-1 relative overflow-hidden bg-slate-950">
          {/* Zoom controls */}
          <div className="absolute top-4 right-4 z-10 flex flex-col gap-2">
            <button
              onClick={() => setZoom(prev => Math.min(3, prev * 1.2))}
              className="p-2 bg-slate-800 hover:bg-slate-700 rounded text-white"
            >
              <Maximize2 size={16} />
            </button>
            <button
              onClick={() => setZoom(prev => Math.max(0.5, prev * 0.8))}
              className="p-2 bg-slate-800 hover:bg-slate-700 rounded text-white"
            >
              <Minimize2 size={16} />
            </button>
            <div className="text-center text-slate-400 text-xs mt-1">
              {(zoom * 100).toFixed(0)}%
            </div>
          </div>

          {/* SVG Map */}
          <svg
            ref={svgRef}
            viewBox={`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`}
            className="w-full h-full"
            style={{ cursor: 'grab' }}
            onWheel={handleWheel}
          >
            <g transform={`scale(${zoom}) translate(${pan.x}, ${pan.y})`}>
              {/* Background */}
              <rect width={MAP_WIDTH} height={MAP_HEIGHT} fill="#0f172a" />

              {/* UK map outline */}
              <UKMapPath />

              {/* Carbon intensity regions */}
              {layers.carbonRegions?.visible && carbonRegions.map((region, i) => (
                <g key={`carbon-${i}`} opacity={layers.carbonRegions?.opacity || 1}>
                  <CarbonRegion region={region} />
                </g>
              ))}

              {/* Grid nodes */}
              {layers.gridNodes?.visible && gridNodes.map((node, i) => (
                <g key={`node-${i}`} opacity={layers.gridNodes?.opacity || 1}>
                  <GridNodeMarker
                    node={node}
                    onClick={setSelection}
                    selected={selection?.id === node.id}
                  />
                </g>
              ))}

              {/* Interconnectors */}
              {layers.interconnectors?.visible && interconnectors.map((ic, i) => (
                <g key={`ic-${i}`} opacity={layers.interconnectors?.opacity || 1}>
                  <InterconnectorCable
                    interconnector={ic}
                    onClick={setSelection}
                  />
                </g>
              ))}

              {/* Generators */}
              {layers.generators?.visible && generators.slice(0, 100).map((gen, i) => (
                <g key={`gen-${i}`} opacity={layers.generators?.opacity || 1}>
                  <AnimatedGeneratorIcon
                    generator={gen}
                    scale={zoom}
                    onClick={setSelection}
                    selected={selection?.id === gen.id}
                  />
                </g>
              ))}
            </g>
          </svg>

          {/* Loading overlay */}
          {loading && !overlay && (
            <div className="absolute inset-0 flex items-center justify-center bg-slate-900/80">
              <div className="text-center">
                <RefreshCw className="animate-spin text-sky-400 mx-auto mb-2" size={32} />
                <p className="text-slate-300">Loading grid data...</p>
              </div>
            </div>
          )}
        </div>

        {/* Right panel - Selection detail */}
        <div className="w-72 p-4 border-l border-slate-700 overflow-y-auto">
          {selection ? (
            <SelectionDetailPanel
              selection={selection}
              onClose={() => setSelection(null)}
            />
          ) : (
            <div className="text-center text-slate-500 py-8">
              <MapPin size={32} className="mx-auto mb-2 opacity-50" />
              <p className="text-sm">Click on a generator, node, or interconnector to view details</p>
            </div>
          )}

          {/* Data sources info */}
          <div className="mt-6 p-3 bg-slate-800/50 rounded text-xs text-slate-500">
            <div className="font-medium text-slate-400 mb-2">Data Sources</div>
            <ul className="space-y-1">
              <li>• Kilowatts Grid (generators)</li>
              <li>• NG Data Portal (demand)</li>
              <li>• Carbon Intensity API</li>
              <li>• Octopus Agile tariff</li>
              <li>• EU ETS prices</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

export default GridSimulator;

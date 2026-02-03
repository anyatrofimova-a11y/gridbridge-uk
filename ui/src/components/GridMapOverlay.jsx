import React, { useState, useEffect, useCallback } from 'react';
import {
  MapPin,
  Zap,
  Wind,
  Sun,
  Flame,
  Atom,
  Leaf,
  Battery,
  ArrowLeftRight,
  Activity,
  TrendingUp,
  RefreshCw,
  Layers,
  Eye,
  EyeOff,
  Info,
  AlertCircle,
} from 'lucide-react';

// Fuel type icons
const FuelIcons = {
  wind: Wind,
  solar: Sun,
  gas: Flame,
  nuclear: Atom,
  biomass: Leaf,
  battery: Battery,
  hydro: Activity,
  coal: Flame,
  other: Zap,
};

// Fuel type colors
const FuelColors = {
  wind: '#10b981',
  solar: '#fbbf24',
  gas: '#ef4444',
  nuclear: '#f59e0b',
  biomass: '#84cc16',
  battery: '#8b5cf6',
  hydro: '#3b82f6',
  coal: '#1f2937',
  other: '#6b7280',
};

// Carbon intensity colors
const CarbonColors = {
  'very low': '#22c55e',
  low: '#84cc16',
  moderate: '#f59e0b',
  high: '#f97316',
  'very high': '#ef4444',
};

// API helpers
const fetchOverlayState = async () => {
  try {
    const res = await fetch('/api/overlay/state');
    if (!res.ok) throw new Error('Overlay not available');
    return await res.json();
  } catch (e) {
    console.error('Failed to fetch overlay:', e);
    return null;
  }
};

const fetchAggregatedSnapshot = async () => {
  try {
    const res = await fetch('/api/aggregated/snapshot');
    if (!res.ok) throw new Error('Snapshot not available');
    return await res.json();
  } catch (e) {
    console.error('Failed to fetch snapshot:', e);
    return null;
  }
};

const fetchFlexibilityOpportunities = async () => {
  try {
    const res = await fetch('/api/aggregated/flexibility-opportunities');
    if (!res.ok) throw new Error('Opportunities not available');
    return await res.json();
  } catch (e) {
    console.error('Failed to fetch opportunities:', e);
    return null;
  }
};

// Simple SVG Map of UK
const UKMapSVG = ({ generators, interconnectors, gridNodes, carbonRegions, onNodeClick }) => {
  // Simplified UK outline path
  const ukPath = `
    M 150 50
    L 170 30 L 200 25 L 220 40 L 240 35 L 260 50
    L 270 80 L 280 120 L 275 160 L 290 200
    L 285 240 L 270 280 L 250 320 L 230 350
    L 200 380 L 170 400 L 140 390 L 110 370
    L 90 340 L 80 300 L 85 260 L 100 220
    L 95 180 L 110 140 L 130 100 L 140 70
    Z
  `;

  // Convert lat/lng to SVG coordinates (simplified projection)
  const toSVG = (lat, lng) => {
    // UK bounds: lat 49.5-60, lng -8 to 2
    const x = ((lng + 8) / 10) * 200 + 50;
    const y = ((60 - lat) / 10.5) * 380 + 20;
    return { x, y };
  };

  return (
    <svg viewBox="0 0 350 450" className="w-full h-full">
      {/* Background */}
      <rect width="350" height="450" fill="#1e293b" />

      {/* UK Outline */}
      <path d={ukPath} fill="#334155" stroke="#475569" strokeWidth="2" />

      {/* Carbon intensity regions (simplified) */}
      {carbonRegions?.map((region, i) => {
        const pos = toSVG(region.coords?.lat || 54, region.coords?.lng || -2);
        const color = CarbonColors[region.index?.toLowerCase()] || '#6b7280';
        return (
          <circle
            key={`carbon-${i}`}
            cx={pos.x}
            cy={pos.y}
            r={25}
            fill={color}
            opacity={0.2}
          />
        );
      })}

      {/* Grid nodes */}
      {gridNodes?.map((node, i) => {
        if (!node.coords) return null;
        const pos = toSVG(node.coords.lat, node.coords.lng);
        const color = node.headroom_mw > 100 ? '#22c55e' : node.headroom_mw > 50 ? '#f59e0b' : '#ef4444';
        return (
          <g key={`node-${i}`} onClick={() => onNodeClick?.(node)} className="cursor-pointer">
            <circle cx={pos.x} cy={pos.y} r={6} fill={color} stroke="#fff" strokeWidth="1" />
            <title>{node.name}: {node.headroom_mw} MW headroom</title>
          </g>
        );
      })}

      {/* Generators */}
      {generators?.slice(0, 50).map((gen, i) => {
        if (!gen.coords || gen.coords.lat === 0) return null;
        const pos = toSVG(gen.coords.lat, gen.coords.lng);
        const color = FuelColors[gen.fuel_type] || '#6b7280';
        const size = Math.min(Math.max(gen.output_mw / 100, 3), 12);
        return (
          <g key={`gen-${i}`} onClick={() => onNodeClick?.(gen)} className="cursor-pointer">
            <circle cx={pos.x} cy={pos.y} r={size} fill={color} opacity={0.8} />
            <title>{gen.name}: {gen.output_mw?.toFixed(0)} MW ({gen.fuel_type})</title>
          </g>
        );
      })}

      {/* Interconnectors */}
      {interconnectors?.map((ic, i) => {
        if (!ic.coords) return null;
        const pos = toSVG(ic.coords.lat, ic.coords.lng);
        const color = ic.flow_mw > 0 ? '#22c55e' : ic.flow_mw < 0 ? '#ef4444' : '#6b7280';
        return (
          <g key={`ic-${i}`}>
            <line x1={pos.x - 10} y1={pos.y} x2={pos.x + 10} y2={pos.y} stroke={color} strokeWidth="3" />
            <circle cx={pos.x} cy={pos.y} r={4} fill={color} />
            <title>{ic.name}: {ic.flow_mw?.toFixed(0)} MW ({ic.flow_mw > 0 ? 'import' : 'export'})</title>
          </g>
        );
      })}

      {/* Legend */}
      <g transform="translate(260, 20)">
        <rect x="0" y="0" width="80" height="120" fill="#1e293b" rx="4" />
        <text x="10" y="15" fill="#94a3b8" fontSize="10" fontWeight="bold">Legend</text>

        <circle cx="15" cy="30" r="4" fill="#22c55e" />
        <text x="25" y="33" fill="#94a3b8" fontSize="8">High headroom</text>

        <circle cx="15" cy="45" r="4" fill="#f59e0b" />
        <text x="25" y="48" fill="#94a3b8" fontSize="8">Med headroom</text>

        <circle cx="15" cy="60" r="4" fill="#ef4444" />
        <text x="25" y="63" fill="#94a3b8" fontSize="8">Low headroom</text>

        <circle cx="15" cy="80" r="4" fill="#10b981" />
        <text x="25" y="83" fill="#94a3b8" fontSize="8">Wind</text>

        <circle cx="15" cy="95" r="4" fill="#ef4444" />
        <text x="25" y="98" fill="#94a3b8" fontSize="8">Gas</text>

        <circle cx="15" cy="110" r="4" fill="#f59e0b" />
        <text x="25" y="113" fill="#94a3b8" fontSize="8">Nuclear</text>
      </g>
    </svg>
  );
};

// Layer toggle component
const LayerToggle = ({ name, visible, onChange, icon: Icon }) => (
  <button
    onClick={() => onChange(!visible)}
    className={`flex items-center gap-2 px-3 py-2 rounded text-sm transition-colors ${
      visible ? 'bg-sky-600 text-white' : 'bg-slate-700 text-slate-300 hover:bg-slate-600'
    }`}
  >
    <Icon size={14} />
    <span>{name}</span>
    {visible ? <Eye size={12} /> : <EyeOff size={12} />}
  </button>
);

// Opportunity card
const OpportunityCard = ({ opportunity }) => {
  const actionColors = {
    INCREASE_LOAD: 'bg-green-900/50 border-green-600',
    REDUCE_LOAD: 'bg-red-900/50 border-red-600',
    OFFER_DSR: 'bg-purple-900/50 border-purple-600',
    CHARGE_STORAGE: 'bg-blue-900/50 border-blue-600',
  };

  return (
    <div className={`p-3 rounded border ${actionColors[opportunity.action] || 'bg-slate-800 border-slate-600'}`}>
      <div className="flex justify-between items-start">
        <span className="font-medium text-white">{opportunity.action.replace(/_/g, ' ')}</span>
        <span className="text-xs bg-slate-700 px-2 py-0.5 rounded">
          {(opportunity.confidence * 100).toFixed(0)}% conf
        </span>
      </div>
      <p className="text-sm text-slate-300 mt-1">{opportunity.reason}</p>
      <span className="text-xs text-slate-400">{opportunity.type}</span>
    </div>
  );
};

// Main component
const GridMapOverlay = () => {
  const [overlayState, setOverlayState] = useState(null);
  const [snapshot, setSnapshot] = useState(null);
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedNode, setSelectedNode] = useState(null);

  // Layer visibility
  const [layers, setLayers] = useState({
    generators: true,
    interconnectors: true,
    gridNodes: true,
    carbonIntensity: true,
  });

  const refreshData = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const [overlay, snap, opps] = await Promise.all([
        fetchOverlayState(),
        fetchAggregatedSnapshot(),
        fetchFlexibilityOpportunities(),
      ]);

      if (overlay) setOverlayState(overlay);
      if (snap) setSnapshot(snap);
      if (opps) setOpportunities(opps.opportunities || []);
    } catch (e) {
      setError('Failed to load grid data');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refreshData();
    const interval = setInterval(refreshData, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, [refreshData]);

  const toggleLayer = (layer) => {
    setLayers(prev => ({ ...prev, [layer]: !prev[layer] }));
  };

  // Extract layer data
  const generators = layers.generators ? overlayState?.layers?.generators?.data || [] : [];
  const interconnectors = layers.interconnectors ? overlayState?.layers?.interconnectors?.data || [] : [];
  const gridNodes = layers.gridNodes ? overlayState?.layers?.grid_nodes?.data || [] : [];
  const carbonRegions = layers.carbonIntensity ? overlayState?.layers?.carbon_intensity?.data || [] : [];

  return (
    <div className="bg-slate-900 rounded-lg border border-slate-700 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-slate-700 flex justify-between items-center">
        <div className="flex items-center gap-2">
          <Layers className="text-sky-400" size={20} />
          <h2 className="text-lg font-semibold text-white">Grid Overlay Interface</h2>
        </div>
        <button
          onClick={refreshData}
          disabled={loading}
          className="flex items-center gap-2 px-3 py-1.5 bg-slate-700 hover:bg-slate-600 rounded text-sm text-white transition-colors"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="p-4 bg-red-900/30 border-b border-red-800 flex items-center gap-2 text-red-300">
          <AlertCircle size={16} />
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-0">
        {/* Map */}
        <div className="lg:col-span-2 p-4 border-r border-slate-700">
          {/* Layer toggles */}
          <div className="flex flex-wrap gap-2 mb-4">
            <LayerToggle
              name="Generators"
              visible={layers.generators}
              onChange={() => toggleLayer('generators')}
              icon={Zap}
            />
            <LayerToggle
              name="Interconnectors"
              visible={layers.interconnectors}
              onChange={() => toggleLayer('interconnectors')}
              icon={ArrowLeftRight}
            />
            <LayerToggle
              name="Grid Nodes"
              visible={layers.gridNodes}
              onChange={() => toggleLayer('gridNodes')}
              icon={MapPin}
            />
            <LayerToggle
              name="Carbon Intensity"
              visible={layers.carbonIntensity}
              onChange={() => toggleLayer('carbonIntensity')}
              icon={Activity}
            />
          </div>

          {/* Map SVG */}
          <div className="aspect-[3/4] max-h-[500px] bg-slate-800 rounded-lg overflow-hidden">
            {loading && !overlayState ? (
              <div className="w-full h-full flex items-center justify-center text-slate-400">
                <RefreshCw className="animate-spin mr-2" size={20} />
                Loading grid data...
              </div>
            ) : (
              <UKMapSVG
                generators={generators}
                interconnectors={interconnectors}
                gridNodes={gridNodes}
                carbonRegions={carbonRegions}
                onNodeClick={setSelectedNode}
              />
            )}
          </div>

          {/* Selected node info */}
          {selectedNode && (
            <div className="mt-4 p-3 bg-slate-800 rounded-lg">
              <div className="flex justify-between items-start">
                <h3 className="font-medium text-white">{selectedNode.name}</h3>
                <button onClick={() => setSelectedNode(null)} className="text-slate-400 hover:text-white">
                  &times;
                </button>
              </div>
              <div className="grid grid-cols-2 gap-2 mt-2 text-sm">
                {selectedNode.fuel_type && (
                  <div className="text-slate-400">
                    Type: <span className="text-white">{selectedNode.fuel_type}</span>
                  </div>
                )}
                {selectedNode.output_mw !== undefined && (
                  <div className="text-slate-400">
                    Output: <span className="text-white">{selectedNode.output_mw?.toFixed(0)} MW</span>
                  </div>
                )}
                {selectedNode.headroom_mw !== undefined && (
                  <div className="text-slate-400">
                    Headroom: <span className="text-white">{selectedNode.headroom_mw} MW</span>
                  </div>
                )}
                {selectedNode.capacity_mw !== undefined && (
                  <div className="text-slate-400">
                    Capacity: <span className="text-white">{selectedNode.capacity_mw?.toFixed(0)} MW</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Sidebar */}
        <div className="p-4 space-y-4">
          {/* Snapshot summary */}
          {snapshot && (
            <div className="space-y-3">
              <h3 className="font-medium text-white flex items-center gap-2">
                <Activity size={16} className="text-sky-400" />
                Live Grid Status
              </h3>

              <div className="grid grid-cols-2 gap-2 text-sm">
                <div className="bg-slate-800 p-2 rounded">
                  <div className="text-slate-400">Generation</div>
                  <div className="text-white font-medium">
                    {(snapshot.generation?.total_mw / 1000)?.toFixed(1)} GW
                  </div>
                </div>
                <div className="bg-slate-800 p-2 rounded">
                  <div className="text-slate-400">Demand</div>
                  <div className="text-white font-medium">
                    {(snapshot.demand?.total_mw / 1000)?.toFixed(1)} GW
                  </div>
                </div>
                <div className="bg-slate-800 p-2 rounded">
                  <div className="text-slate-400">Carbon</div>
                  <div className={`font-medium ${
                    snapshot.carbon?.index === 'very low' ? 'text-green-400' :
                    snapshot.carbon?.index === 'low' ? 'text-lime-400' :
                    snapshot.carbon?.index === 'moderate' ? 'text-amber-400' :
                    'text-red-400'
                  }`}>
                    {snapshot.carbon?.intensity_gco2_kwh} g/kWh
                  </div>
                </div>
                <div className="bg-slate-800 p-2 rounded">
                  <div className="text-slate-400">Imports</div>
                  <div className={`font-medium ${
                    snapshot.interconnectors?.net_imports_mw > 0 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {snapshot.interconnectors?.net_imports_mw > 0 ? '+' : ''}
                    {(snapshot.interconnectors?.net_imports_mw / 1000)?.toFixed(1)} GW
                  </div>
                </div>
              </div>

              {/* Generation mix */}
              <div className="bg-slate-800 p-3 rounded">
                <div className="text-slate-400 text-sm mb-2">Generation Mix</div>
                <div className="space-y-1">
                  {Object.entries(snapshot.generation?.by_fuel || {})
                    .sort(([, a], [, b]) => b - a)
                    .slice(0, 5)
                    .map(([fuel, mw]) => {
                      const pct = (mw / snapshot.generation?.total_mw * 100) || 0;
                      const Icon = FuelIcons[fuel] || Zap;
                      return (
                        <div key={fuel} className="flex items-center gap-2">
                          <Icon size={12} style={{ color: FuelColors[fuel] }} />
                          <span className="text-xs text-slate-300 w-16 capitalize">{fuel}</span>
                          <div className="flex-1 h-2 bg-slate-700 rounded overflow-hidden">
                            <div
                              className="h-full rounded"
                              style={{
                                width: `${pct}%`,
                                backgroundColor: FuelColors[fuel],
                              }}
                            />
                          </div>
                          <span className="text-xs text-slate-400 w-12 text-right">
                            {pct.toFixed(0)}%
                          </span>
                        </div>
                      );
                    })}
                </div>
              </div>

              {/* Market prices */}
              {(snapshot.markets?.ets_price_eur || snapshot.markets?.agile_price_gbp) && (
                <div className="bg-slate-800 p-3 rounded">
                  <div className="text-slate-400 text-sm mb-2">Market Prices</div>
                  <div className="grid grid-cols-2 gap-2 text-sm">
                    {snapshot.markets?.ets_price_eur && (
                      <div>
                        <div className="text-slate-500 text-xs">EU ETS</div>
                        <div className="text-white">{snapshot.markets.ets_price_eur} EUR/t</div>
                      </div>
                    )}
                    {snapshot.markets?.agile_price_gbp && (
                      <div>
                        <div className="text-slate-500 text-xs">Agile</div>
                        <div className="text-white">{snapshot.markets.agile_price_gbp}p/kWh</div>
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Flexibility opportunities */}
          {opportunities.length > 0 && (
            <div className="space-y-3">
              <h3 className="font-medium text-white flex items-center gap-2">
                <TrendingUp size={16} className="text-green-400" />
                Flexibility Opportunities
              </h3>
              <div className="space-y-2">
                {opportunities.slice(0, 3).map((opp, i) => (
                  <OpportunityCard key={i} opportunity={opp} />
                ))}
              </div>
            </div>
          )}

          {/* Data sources */}
          <div className="pt-4 border-t border-slate-700">
            <div className="flex items-center gap-2 text-slate-400 text-xs">
              <Info size={12} />
              <span>
                Data: Kilowatts Grid, NG Data Portal, Carbon Intensity API, CfD Watch, Octopy Energy, ETS Watch
              </span>
            </div>
            {overlayState?.timestamp && (
              <div className="text-slate-500 text-xs mt-1">
                Updated: {new Date(overlayState.timestamp).toLocaleTimeString()}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default GridMapOverlay;

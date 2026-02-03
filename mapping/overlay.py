"""
GridBridge UK - Grid Overlay Interface

Combines multiple data sources into visual overlay layers
for the simulated grid interface.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Callable, Any

from .sources import (
    DataSourceRegistry,
    Generator,
    Interconnector,
    GridNode,
    CfDContract,
    Coords,
    FuelType,
)


class LayerType(str, Enum):
    GENERATORS = "generators"
    INTERCONNECTORS = "interconnectors"
    GRID_NODES = "grid_nodes"
    CARBON_INTENSITY = "carbon_intensity"
    CfD_PROJECTS = "cfd_projects"
    DEMAND_HEATMAP = "demand_heatmap"
    CONSTRAINTS = "constraints"
    HEADROOM = "headroom"


@dataclass
class OverlayLayer:
    """A single overlay layer for the grid map."""

    layer_type: LayerType
    name: str
    visible: bool = True
    opacity: float = 1.0
    data: list = field(default_factory=list)
    style: dict = field(default_factory=dict)
    last_updated: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "layer_type": self.layer_type.value,
            "name": self.name,
            "visible": self.visible,
            "opacity": self.opacity,
            "data": [
                d.to_dict() if hasattr(d, "to_dict") else d
                for d in self.data
            ],
            "style": self.style,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }


@dataclass
class MapBounds:
    """Geographic bounds for the map view."""

    north: float = 60.0  # Northern Scotland
    south: float = 49.5  # Channel Islands
    east: float = 2.0    # East coast
    west: float = -8.0   # Western Ireland border

    def contains(self, lat: float, lng: float) -> bool:
        return (self.south <= lat <= self.north) and (self.west <= lng <= self.east)

    def to_dict(self) -> dict:
        return {
            "north": self.north,
            "south": self.south,
            "east": self.east,
            "west": self.west,
        }


# Default styles for different layer types
DEFAULT_STYLES = {
    LayerType.GENERATORS: {
        "gas": {"color": "#ef4444", "icon": "flame"},
        "coal": {"color": "#1f2937", "icon": "factory"},
        "nuclear": {"color": "#f59e0b", "icon": "atom"},
        "wind": {"color": "#10b981", "icon": "wind"},
        "solar": {"color": "#fbbf24", "icon": "sun"},
        "hydro": {"color": "#3b82f6", "icon": "droplet"},
        "biomass": {"color": "#84cc16", "icon": "leaf"},
        "battery": {"color": "#8b5cf6", "icon": "battery"},
        "other": {"color": "#6b7280", "icon": "zap"},
    },
    LayerType.INTERCONNECTORS: {
        "default": {"color": "#06b6d4", "width": 3},
        "import": {"color": "#22c55e", "width": 3},
        "export": {"color": "#ef4444", "width": 3},
    },
    LayerType.CARBON_INTENSITY: {
        "very low": {"color": "#22c55e", "fill": "#dcfce7"},
        "low": {"color": "#84cc16", "fill": "#ecfccb"},
        "moderate": {"color": "#f59e0b", "fill": "#fef3c7"},
        "high": {"color": "#f97316", "fill": "#ffedd5"},
        "very high": {"color": "#ef4444", "fill": "#fee2e2"},
    },
    LayerType.GRID_NODES: {
        "gsp": {"color": "#3b82f6", "size": 12},
        "bsp": {"color": "#8b5cf6", "size": 10},
        "substation": {"color": "#6b7280", "size": 8},
    },
    LayerType.HEADROOM: {
        "high": {"color": "#22c55e", "fill_opacity": 0.6},
        "medium": {"color": "#f59e0b", "fill_opacity": 0.6},
        "low": {"color": "#ef4444", "fill_opacity": 0.6},
    },
}


class GridOverlay:
    """
    Main overlay manager that combines data from multiple sources
    into visual layers for the grid interface.
    """

    def __init__(self, registry: Optional[DataSourceRegistry] = None):
        self.registry = registry or DataSourceRegistry.create_default()
        self.layers: dict[LayerType, OverlayLayer] = {}
        self.bounds = MapBounds()
        self._update_callbacks: list[Callable[[LayerType], None]] = []

    def on_update(self, callback: Callable[[LayerType], None]):
        """Register a callback for layer updates."""
        self._update_callbacks.append(callback)

    def _notify_update(self, layer_type: LayerType):
        """Notify callbacks of layer update."""
        for callback in self._update_callbacks:
            try:
                callback(layer_type)
            except Exception:
                pass

    def refresh_layer(self, layer_type: LayerType) -> OverlayLayer:
        """Refresh a specific layer with latest data."""
        refreshers = {
            LayerType.GENERATORS: self._refresh_generators,
            LayerType.INTERCONNECTORS: self._refresh_interconnectors,
            LayerType.CARBON_INTENSITY: self._refresh_carbon_intensity,
            LayerType.CfD_PROJECTS: self._refresh_cfd_projects,
            LayerType.GRID_NODES: self._refresh_grid_nodes,
            LayerType.HEADROOM: self._refresh_headroom,
        }

        refresher = refreshers.get(layer_type)
        if refresher:
            layer = refresher()
            self.layers[layer_type] = layer
            self._notify_update(layer_type)
            return layer

        return self.layers.get(layer_type, OverlayLayer(layer_type=layer_type, name=layer_type.value))

    def refresh_all(self) -> dict[LayerType, OverlayLayer]:
        """Refresh all layers."""
        for layer_type in LayerType:
            try:
                self.refresh_layer(layer_type)
            except Exception as e:
                print(f"Error refreshing {layer_type}: {e}")
        return self.layers

    def _refresh_generators(self) -> OverlayLayer:
        """Refresh generator layer from Kilowatts Grid."""
        source = self.registry.get("kilowatts-grid")
        generators = source.get_generators() if source else []

        # Filter to UK bounds
        generators = [
            g for g in generators
            if self.bounds.contains(g.coords.lat, g.coords.lng)
        ]

        return OverlayLayer(
            layer_type=LayerType.GENERATORS,
            name="Power Generators",
            data=generators,
            style=DEFAULT_STYLES[LayerType.GENERATORS],
            last_updated=datetime.now(timezone.utc),
        )

    def _refresh_interconnectors(self) -> OverlayLayer:
        """Refresh interconnector layer from Kilowatts Grid."""
        source = self.registry.get("kilowatts-grid")
        interconnectors = source.get_interconnectors() if source else []

        # Add flow direction styling
        for ic in interconnectors:
            if ic.flow_mw > 0:
                ic.metadata = {"flow_direction": "import"}
            elif ic.flow_mw < 0:
                ic.metadata = {"flow_direction": "export"}
            else:
                ic.metadata = {"flow_direction": "balanced"}

        return OverlayLayer(
            layer_type=LayerType.INTERCONNECTORS,
            name="Interconnectors",
            data=interconnectors,
            style=DEFAULT_STYLES[LayerType.INTERCONNECTORS],
            last_updated=datetime.now(timezone.utc),
        )

    def _refresh_carbon_intensity(self) -> OverlayLayer:
        """Refresh carbon intensity layer from Carbon Intensity API."""
        source = self.registry.get("carbon-intensity")
        regions = source.get_regional_map_data() if source else []

        return OverlayLayer(
            layer_type=LayerType.CARBON_INTENSITY,
            name="Carbon Intensity by Region",
            data=regions,
            style=DEFAULT_STYLES[LayerType.CARBON_INTENSITY],
            last_updated=datetime.now(timezone.utc),
        )

    def _refresh_cfd_projects(self) -> OverlayLayer:
        """Refresh CfD projects layer."""
        source = self.registry.get("cfd-watch")
        contracts = source.get_cfd_contracts() if source else []

        return OverlayLayer(
            layer_type=LayerType.CfD_PROJECTS,
            name="CfD Projects",
            data=contracts,
            style={
                "default": {"color": "#8b5cf6", "icon": "contract"},
            },
            last_updated=datetime.now(timezone.utc),
        )

    def _refresh_grid_nodes(self) -> OverlayLayer:
        """Refresh grid nodes (GSPs/BSPs) - uses mock data for demo."""
        # Major UK Grid Supply Points with approximate coordinates
        gsps = [
            GridNode("bolney", "Bolney GSP", "gsp", Coords(50.97, -0.18), 400, 120, 450),
            GridNode("bramford", "Bramford GSP", "gsp", Coords(52.08, 1.08), 400, 85, 380),
            GridNode("canterbury", "Canterbury North GSP", "gsp", Coords(51.28, 1.08), 400, 95, 320),
            GridNode("dungeness", "Dungeness GSP", "gsp", Coords(50.91, 0.96), 400, 45, 1200),
            GridNode("grain", "Grain GSP", "gsp", Coords(51.45, 0.72), 400, 110, 890),
            GridNode("kemsley", "Kemsley GSP", "gsp", Coords(51.35, 0.73), 132, 65, 280),
            GridNode("littlebrook", "Littlebrook GSP", "gsp", Coords(51.45, 0.25), 400, 130, 520),
            GridNode("northfleet", "Northfleet East GSP", "gsp", Coords(51.43, 0.33), 400, 75, 410),
            GridNode("sellindge", "Sellindge GSP", "gsp", Coords(51.10, 0.98), 400, 200, 2000),
            GridNode("sizewell", "Sizewell GSP", "gsp", Coords(52.21, 1.62), 400, 30, 1200),
            GridNode("pelham", "Pelham GSP", "gsp", Coords(51.95, 0.10), 400, 90, 350),
            GridNode("rye-house", "Rye House GSP", "gsp", Coords(51.77, -0.01), 400, 55, 680),
            GridNode("sundon", "Sundon GSP", "gsp", Coords(51.93, -0.46), 400, 70, 290),
            GridNode("waltham-cross", "Waltham Cross GSP", "gsp", Coords(51.69, -0.03), 400, 100, 510),
            GridNode("wymondley", "Wymondley GSP", "gsp", Coords(51.90, -0.22), 132, 40, 180),
            GridNode("barking", "Barking GSP", "gsp", Coords(51.53, 0.08), 400, 85, 720),
            GridNode("brimsdown", "Brimsdown GSP", "gsp", Coords(51.66, -0.03), 132, 55, 340),
            GridNode("city-road", "City Road GSP", "gsp", Coords(51.53, -0.10), 400, 25, 890),
            GridNode("hackney", "Hackney GSP", "gsp", Coords(51.55, -0.06), 132, 35, 420),
            GridNode("new-cross", "New Cross GSP", "gsp", Coords(51.47, -0.04), 132, 45, 380),
            GridNode("st-johns-wood", "St Johns Wood GSP", "gsp", Coords(51.53, -0.17), 400, 30, 650),
            GridNode("west-ham", "West Ham GSP", "gsp", Coords(51.53, 0.00), 132, 60, 490),
            GridNode("wimbledon", "Wimbledon GSP", "gsp", Coords(51.42, -0.21), 132, 75, 380),
            # Scotland
            GridNode("beauly", "Beauly GSP", "gsp", Coords(57.47, -4.47), 275, 180, 890),
            GridNode("dounreay", "Dounreay GSP", "gsp", Coords(58.58, -3.73), 132, 45, 120),
            GridNode("keith", "Keith GSP", "gsp", Coords(57.55, -2.95), 275, 120, 340),
            GridNode("kintore", "Kintore GSP", "gsp", Coords(57.23, -2.35), 275, 95, 450),
            GridNode("peterhead", "Peterhead GSP", "gsp", Coords(57.50, -1.80), 400, 65, 1180),
            GridNode("tealing", "Tealing GSP", "gsp", Coords(56.52, -2.98), 275, 85, 520),
            GridNode("westfield", "Westfield GSP", "gsp", Coords(56.18, -3.33), 275, 70, 380),
            # Wales
            GridNode("deeside", "Deeside GSP", "gsp", Coords(53.22, -3.03), 400, 110, 890),
            GridNode("legacy", "Legacy GSP", "gsp", Coords(53.05, -3.72), 400, 130, 420),
            GridNode("pentir", "Pentir GSP", "gsp", Coords(53.18, -4.18), 400, 95, 680),
            GridNode("trawsfynydd", "Trawsfynydd GSP", "gsp", Coords(52.90, -3.93), 400, 55, 240),
            GridNode("wylfa", "Wylfa GSP", "gsp", Coords(53.42, -4.48), 400, 180, 970),
        ]

        return OverlayLayer(
            layer_type=LayerType.GRID_NODES,
            name="Grid Supply Points",
            data=gsps,
            style=DEFAULT_STYLES[LayerType.GRID_NODES],
            last_updated=datetime.now(timezone.utc),
        )

    def _refresh_headroom(self) -> OverlayLayer:
        """Refresh headroom visualization layer."""
        # Get grid nodes and classify by headroom
        nodes_layer = self.refresh_layer(LayerType.GRID_NODES)
        headroom_data = []

        for node in nodes_layer.data:
            if isinstance(node, GridNode):
                # Classify headroom
                if node.headroom_mw > 100:
                    level = "high"
                elif node.headroom_mw > 50:
                    level = "medium"
                else:
                    level = "low"

                headroom_data.append({
                    "node_id": node.id,
                    "name": node.name,
                    "coords": node.coords.to_dict(),
                    "headroom_mw": node.headroom_mw,
                    "level": level,
                })

        return OverlayLayer(
            layer_type=LayerType.HEADROOM,
            name="Available Headroom",
            data=headroom_data,
            style=DEFAULT_STYLES[LayerType.HEADROOM],
            last_updated=datetime.now(timezone.utc),
        )

    def get_layer(self, layer_type: LayerType) -> Optional[OverlayLayer]:
        """Get a layer by type."""
        return self.layers.get(layer_type)

    def set_layer_visibility(self, layer_type: LayerType, visible: bool):
        """Set layer visibility."""
        if layer_type in self.layers:
            self.layers[layer_type].visible = visible

    def set_layer_opacity(self, layer_type: LayerType, opacity: float):
        """Set layer opacity (0-1)."""
        if layer_type in self.layers:
            self.layers[layer_type].opacity = max(0, min(1, opacity))

    def get_state(self) -> dict:
        """Get complete overlay state for serialization."""
        return {
            "bounds": self.bounds.to_dict(),
            "layers": {
                lt.value: layer.to_dict()
                for lt, layer in self.layers.items()
            },
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_summary(self) -> dict:
        """Get summary statistics across all layers."""
        summary = {
            "total_generators": 0,
            "total_capacity_mw": 0,
            "total_output_mw": 0,
            "generation_by_fuel": {},
            "interconnector_flow_mw": 0,
            "avg_carbon_intensity": 0,
            "cfd_projects": 0,
            "cfd_capacity_mw": 0,
            "grid_nodes": 0,
            "total_headroom_mw": 0,
        }

        # Generators
        gen_layer = self.layers.get(LayerType.GENERATORS)
        if gen_layer:
            summary["total_generators"] = len(gen_layer.data)
            for gen in gen_layer.data:
                if isinstance(gen, Generator):
                    summary["total_capacity_mw"] += gen.capacity_mw
                    summary["total_output_mw"] += gen.output_mw
                    fuel = gen.fuel_type.value
                    if fuel not in summary["generation_by_fuel"]:
                        summary["generation_by_fuel"][fuel] = 0
                    summary["generation_by_fuel"][fuel] += gen.output_mw

        # Interconnectors
        ic_layer = self.layers.get(LayerType.INTERCONNECTORS)
        if ic_layer:
            for ic in ic_layer.data:
                if isinstance(ic, Interconnector):
                    summary["interconnector_flow_mw"] += ic.flow_mw

        # Carbon intensity
        ci_layer = self.layers.get(LayerType.CARBON_INTENSITY)
        if ci_layer and ci_layer.data:
            intensities = [r.get("intensity", 0) for r in ci_layer.data if isinstance(r, dict)]
            if intensities:
                summary["avg_carbon_intensity"] = sum(intensities) / len(intensities)

        # CfD projects
        cfd_layer = self.layers.get(LayerType.CfD_PROJECTS)
        if cfd_layer:
            summary["cfd_projects"] = len(cfd_layer.data)
            for c in cfd_layer.data:
                if isinstance(c, CfDContract):
                    summary["cfd_capacity_mw"] += c.capacity_mw

        # Grid nodes
        nodes_layer = self.layers.get(LayerType.GRID_NODES)
        if nodes_layer:
            summary["grid_nodes"] = len(nodes_layer.data)
            for node in nodes_layer.data:
                if isinstance(node, GridNode):
                    summary["total_headroom_mw"] += node.headroom_mw

        return summary

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
        """Refresh grid nodes (GSPs/BSPs) with accurate UK geographic coordinates."""
        # Comprehensive UK Grid Supply Points by region
        gsps = [
            # ============= SCOTLAND - North =============
            GridNode("thurso", "Thurso GSP", "gsp", Coords(58.59, -3.52), 132, 85, 120),
            GridNode("dounreay", "Dounreay GSP", "gsp", Coords(58.58, -3.73), 132, 45, 120),
            GridNode("mybster", "Mybster GSP", "gsp", Coords(58.45, -3.35), 132, 95, 80),
            GridNode("beauly", "Beauly GSP", "gsp", Coords(57.47, -4.47), 275, 180, 890),
            GridNode("inverness", "Inverness GSP", "gsp", Coords(57.48, -4.22), 275, 110, 450),
            GridNode("elgin", "Elgin GSP", "gsp", Coords(57.65, -3.32), 132, 75, 220),
            GridNode("keith", "Keith GSP", "gsp", Coords(57.55, -2.95), 275, 120, 340),
            GridNode("peterhead", "Peterhead GSP", "gsp", Coords(57.50, -1.78), 400, 65, 1180),
            GridNode("kintore", "Kintore GSP", "gsp", Coords(57.23, -2.35), 275, 95, 450),
            GridNode("persley", "Persley GSP", "gsp", Coords(57.18, -2.12), 275, 88, 380),
            GridNode("fetteresso", "Fetteresso GSP", "gsp", Coords(56.95, -2.25), 275, 72, 290),
            GridNode("tealing", "Tealing GSP", "gsp", Coords(56.52, -2.98), 275, 85, 520),
            GridNode("arbroath", "Arbroath GSP", "gsp", Coords(56.56, -2.58), 132, 55, 180),
            GridNode("charleston", "Charleston GSP", "gsp", Coords(56.35, -3.42), 275, 92, 410),
            GridNode("glenrothes", "Glenrothes GSP", "gsp", Coords(56.20, -3.15), 132, 68, 320),
            GridNode("westfield", "Westfield GSP", "gsp", Coords(56.18, -3.33), 275, 70, 380),

            # ============= SCOTLAND - Central =============
            GridNode("kincardine", "Kincardine GSP", "gsp", Coords(56.07, -3.72), 275, 105, 620),
            GridNode("longannet", "Longannet GSP", "gsp", Coords(56.05, -3.70), 400, 145, 2400),
            GridNode("grangemouth", "Grangemouth GSP", "gsp", Coords(56.02, -3.70), 275, 78, 890),
            GridNode("bonnybridge", "Bonnybridge GSP", "gsp", Coords(55.99, -3.88), 275, 65, 340),
            GridNode("stirling", "Stirling GSP", "gsp", Coords(56.12, -3.93), 132, 82, 280),
            GridNode("dunfermline", "Dunfermline GSP", "gsp", Coords(56.07, -3.45), 132, 58, 310),
            GridNode("edinburgh-portobello", "Portobello GSP", "gsp", Coords(55.95, -3.10), 275, 45, 520),
            GridNode("edinburgh-gorgie", "Gorgie GSP", "gsp", Coords(55.93, -3.25), 132, 52, 440),
            GridNode("cockenzie", "Cockenzie GSP", "gsp", Coords(55.97, -2.97), 400, 125, 1200),
            GridNode("torness", "Torness GSP", "gsp", Coords(55.97, -2.41), 400, 35, 1300),
            GridNode("hunterston", "Hunterston GSP", "gsp", Coords(55.72, -4.89), 400, 140, 1000),
            GridNode("inverkip", "Inverkip GSP", "gsp", Coords(55.90, -4.87), 275, 95, 680),
            GridNode("devol-moor", "Devol Moor GSP", "gsp", Coords(55.93, -4.72), 275, 88, 420),
            GridNode("erskine", "Erskine GSP", "gsp", Coords(55.90, -4.45), 275, 72, 380),
            GridNode("glasgow-neilston", "Neilston GSP", "gsp", Coords(55.78, -4.42), 132, 62, 350),
            GridNode("glasgow-busby", "Busby GSP", "gsp", Coords(55.78, -4.27), 132, 48, 290),
            GridNode("east-kilbride", "East Kilbride GSP", "gsp", Coords(55.76, -4.18), 275, 75, 410),
            GridNode("strathaven", "Strathaven GSP", "gsp", Coords(55.68, -4.07), 275, 110, 520),
            GridNode("coalburn", "Coalburn GSP", "gsp", Coords(55.58, -3.92), 275, 135, 380),
            GridNode("elvanfoot", "Elvanfoot GSP", "gsp", Coords(55.43, -3.65), 275, 165, 280),

            # ============= SCOTLAND - South =============
            GridNode("eccles", "Eccles GSP", "gsp", Coords(55.65, -2.38), 275, 125, 340),
            GridNode("galashiels", "Galashiels GSP", "gsp", Coords(55.62, -2.80), 132, 95, 220),
            GridNode("hawick", "Hawick GSP", "gsp", Coords(55.42, -2.78), 132, 88, 180),
            GridNode("gretna", "Gretna GSP", "gsp", Coords(55.00, -3.07), 275, 145, 420),

            # ============= NORTH ENGLAND =============
            GridNode("stella-west", "Stella West GSP", "gsp", Coords(54.97, -1.75), 275, 85, 680),
            GridNode("newcastle-south-shields", "South Shields GSP", "gsp", Coords(55.00, -1.43), 132, 65, 380),
            GridNode("blyth", "Blyth GSP", "gsp", Coords(55.13, -1.50), 275, 115, 890),
            GridNode("tynemouth", "Tynemouth GSP", "gsp", Coords(55.02, -1.45), 132, 55, 320),
            GridNode("hartlepool", "Hartlepool GSP", "gsp", Coords(54.68, -1.21), 275, 95, 1450),
            GridNode("norton", "Norton GSP", "gsp", Coords(54.60, -1.32), 275, 78, 520),
            GridNode("middlesbrough", "Lackenby GSP", "gsp", Coords(54.57, -1.15), 275, 105, 780),
            GridNode("grangetown", "Grangetown GSP", "gsp", Coords(54.55, -1.18), 132, 68, 420),
            GridNode("saltholme", "Saltholme GSP", "gsp", Coords(54.62, -1.22), 275, 125, 650),

            # ============= NORTH WEST ENGLAND =============
            GridNode("harker", "Harker GSP", "gsp", Coords(54.95, -2.90), 400, 175, 520),
            GridNode("carlisle", "Carlisle GSP", "gsp", Coords(54.89, -2.93), 132, 85, 280),
            GridNode("penrith", "Penrith GSP", "gsp", Coords(54.66, -2.75), 132, 95, 180),
            GridNode("kendal", "Kendal GSP", "gsp", Coords(54.33, -2.74), 132, 72, 220),
            GridNode("heysham", "Heysham GSP", "gsp", Coords(54.03, -2.90), 400, 45, 2400),
            GridNode("lancaster", "Lancaster GSP", "gsp", Coords(54.05, -2.80), 132, 68, 280),
            GridNode("stanah", "Stanah GSP", "gsp", Coords(53.88, -2.98), 275, 92, 480),
            GridNode("penwortham", "Penwortham GSP", "gsp", Coords(53.75, -2.72), 400, 125, 680),
            GridNode("preston", "Preston GSP", "gsp", Coords(53.76, -2.70), 132, 78, 420),
            GridNode("padiham", "Padiham GSP", "gsp", Coords(53.80, -2.30), 275, 105, 520),
            GridNode("rochdale", "Rochdale GSP", "gsp", Coords(53.62, -2.15), 132, 58, 380),
            GridNode("whitegate", "Whitegate GSP", "gsp", Coords(53.25, -2.52), 275, 115, 620),
            GridNode("kearsley", "Kearsley GSP", "gsp", Coords(53.55, -2.37), 275, 88, 780),
            GridNode("south-manchester", "South Manchester GSP", "gsp", Coords(53.43, -2.22), 275, 65, 890),
            GridNode("carrington", "Carrington GSP", "gsp", Coords(53.43, -2.40), 275, 95, 1200),
            GridNode("fiddlers-ferry", "Fiddlers Ferry GSP", "gsp", Coords(53.37, -2.68), 400, 135, 2000),
            GridNode("warrington", "Warrington GSP", "gsp", Coords(53.40, -2.58), 275, 82, 520),
            GridNode("birkenhead", "Birkenhead GSP", "gsp", Coords(53.38, -3.02), 132, 72, 380),
            GridNode("capenhurst", "Capenhurst GSP", "gsp", Coords(53.27, -2.95), 400, 145, 450),
            GridNode("deeside", "Deeside GSP", "gsp", Coords(53.22, -3.03), 400, 110, 890),

            # ============= YORKSHIRE =============
            GridNode("drax", "Drax GSP", "gsp", Coords(53.73, -0.98), 400, 35, 4000),
            GridNode("eggborough", "Eggborough GSP", "gsp", Coords(53.71, -1.13), 400, 55, 2000),
            GridNode("ferrybridge", "Ferrybridge GSP", "gsp", Coords(53.72, -1.27), 400, 65, 2000),
            GridNode("monk-fryston", "Monk Fryston GSP", "gsp", Coords(53.77, -1.25), 275, 95, 680),
            GridNode("leeds-skelton", "Skelton Grange GSP", "gsp", Coords(53.78, -1.48), 275, 72, 890),
            GridNode("leeds-kirkstall", "Kirkstall GSP", "gsp", Coords(53.82, -1.60), 132, 55, 420),
            GridNode("bradford-west", "Bradford West GSP", "gsp", Coords(53.80, -1.78), 132, 62, 380),
            GridNode("thornton", "Thornton GSP", "gsp", Coords(53.81, -1.85), 275, 85, 320),
            GridNode("keighley", "Keighley GSP", "gsp", Coords(53.87, -1.90), 132, 75, 280),
            GridNode("skipton", "Skipton GSP", "gsp", Coords(53.96, -2.02), 132, 95, 180),
            GridNode("sheffield-templeborough", "Templeborough GSP", "gsp", Coords(53.42, -1.38), 275, 78, 680),
            GridNode("sheffield-neepsend", "Neepsend GSP", "gsp", Coords(53.40, -1.48), 132, 52, 420),
            GridNode("sheffield-jordanthorpe", "Jordanthorpe GSP", "gsp", Coords(53.33, -1.48), 132, 65, 380),
            GridNode("doncaster", "Doncaster GSP", "gsp", Coords(53.52, -1.12), 132, 88, 320),
            GridNode("rotherham", "Thurcroft GSP", "gsp", Coords(53.40, -1.25), 275, 105, 480),
            GridNode("hull", "Saltend GSP", "gsp", Coords(53.73, -0.25), 275, 115, 1200),
            GridNode("hull-creyke-beck", "Creyke Beck GSP", "gsp", Coords(53.88, -0.42), 400, 145, 520),
            GridNode("grimsby", "Grimsby West GSP", "gsp", Coords(53.57, -0.12), 275, 125, 680),
            GridNode("killingholme", "Killingholme GSP", "gsp", Coords(53.65, -0.22), 400, 95, 1400),
            GridNode("scunthorpe", "Scunthorpe GSP", "gsp", Coords(53.58, -0.65), 275, 85, 580),

            # ============= EAST MIDLANDS =============
            GridNode("west-burton", "West Burton GSP", "gsp", Coords(53.37, -0.82), 400, 55, 2000),
            GridNode("cottam", "Cottam GSP", "gsp", Coords(53.30, -0.78), 400, 65, 2000),
            GridNode("high-marnham", "High Marnham GSP", "gsp", Coords(53.22, -0.85), 400, 105, 1000),
            GridNode("staythorpe", "Staythorpe GSP", "gsp", Coords(53.07, -0.90), 400, 75, 1700),
            GridNode("nottingham-ratcliffe", "Ratcliffe GSP", "gsp", Coords(52.87, -1.25), 400, 85, 2000),
            GridNode("nottingham-wilford", "Wilford GSP", "gsp", Coords(52.93, -1.15), 275, 62, 520),
            GridNode("leicester-aylestone", "Aylestone GSP", "gsp", Coords(52.60, -1.15), 132, 55, 380),
            GridNode("leicester-east", "Leicester East GSP", "gsp", Coords(52.63, -1.05), 275, 72, 420),
            GridNode("coventry", "Coventry GSP", "gsp", Coords(52.42, -1.50), 132, 68, 480),
            GridNode("rugby", "Rugby GSP", "gsp", Coords(52.37, -1.25), 132, 95, 280),
            GridNode("corby", "Corby GSP", "gsp", Coords(52.50, -0.70), 132, 115, 320),
            GridNode("peterborough", "Peterborough GSP", "gsp", Coords(52.58, -0.25), 132, 88, 380),

            # ============= EAST ANGLIA =============
            GridNode("walpole", "Walpole GSP", "gsp", Coords(52.73, 0.18), 400, 165, 420),
            GridNode("norwich-main", "Norwich Main GSP", "gsp", Coords(52.62, 1.28), 400, 125, 520),
            GridNode("norwich-trowse", "Trowse GSP", "gsp", Coords(52.60, 1.30), 132, 72, 380),
            GridNode("kings-lynn", "Kings Lynn GSP", "gsp", Coords(52.75, 0.40), 132, 95, 280),
            GridNode("march", "March GSP", "gsp", Coords(52.55, 0.08), 132, 85, 220),
            GridNode("bury-st-edmunds", "Bury St Edmunds GSP", "gsp", Coords(52.25, 0.72), 132, 105, 320),
            GridNode("bramford", "Bramford GSP", "gsp", Coords(52.08, 1.08), 400, 85, 380),
            GridNode("sizewell", "Sizewell GSP", "gsp", Coords(52.21, 1.62), 400, 30, 1200),
            GridNode("leiston", "Leiston GSP", "gsp", Coords(52.20, 1.58), 132, 45, 180),
            GridNode("ipswich", "Ipswich GSP", "gsp", Coords(52.05, 1.15), 132, 65, 380),
            GridNode("colchester", "Colchester GSP", "gsp", Coords(51.88, 0.90), 132, 78, 320),
            GridNode("clacton", "Clacton GSP", "gsp", Coords(51.78, 1.15), 132, 92, 180),
            GridNode("pelham", "Pelham GSP", "gsp", Coords(51.95, 0.10), 400, 90, 350),
            GridNode("cambridge-burwell", "Burwell GSP", "gsp", Coords(52.28, 0.33), 132, 115, 280),
            GridNode("cambridge-fulbourn", "Fulbourn GSP", "gsp", Coords(52.18, 0.22), 132, 88, 320),
            GridNode("eaton-socon", "Eaton Socon GSP", "gsp", Coords(52.22, -0.28), 400, 135, 520),

            # ============= WEST MIDLANDS =============
            GridNode("ironbridge", "Ironbridge GSP", "gsp", Coords(52.63, -2.50), 400, 95, 1000),
            GridNode("rugeley", "Rugeley GSP", "gsp", Coords(52.75, -1.92), 400, 115, 1000),
            GridNode("drakelow", "Drakelow GSP", "gsp", Coords(52.77, -1.65), 400, 85, 2000),
            GridNode("wolverhampton", "Wolverhampton GSP", "gsp", Coords(52.58, -2.12), 132, 55, 480),
            GridNode("walsall", "Bustleholme GSP", "gsp", Coords(52.57, -1.98), 275, 72, 420),
            GridNode("birmingham-nechells", "Nechells GSP", "gsp", Coords(52.50, -1.85), 275, 48, 680),
            GridNode("birmingham-hams-hall", "Hams Hall GSP", "gsp", Coords(52.52, -1.70), 400, 105, 520),
            GridNode("birmingham-tyseley", "Tyseley GSP", "gsp", Coords(52.45, -1.82), 132, 62, 380),
            GridNode("birmingham-kitwell", "Kitwell GSP", "gsp", Coords(52.42, -1.95), 132, 55, 320),
            GridNode("stoke", "Stoke GSP", "gsp", Coords(53.00, -2.15), 132, 75, 380),
            GridNode("crewe", "Crewe GSP", "gsp", Coords(53.10, -2.45), 132, 82, 280),
            GridNode("shrewsbury", "Shrewsbury GSP", "gsp", Coords(52.72, -2.75), 132, 98, 220),
            GridNode("telford", "Telford GSP", "gsp", Coords(52.68, -2.48), 132, 88, 320),
            GridNode("worcester", "Worcester GSP", "gsp", Coords(52.20, -2.20), 132, 75, 280),
            GridNode("hereford", "Hereford GSP", "gsp", Coords(52.05, -2.72), 132, 105, 180),

            # ============= SOUTH WEST ENGLAND =============
            GridNode("gloucester", "Gloucester GSP", "gsp", Coords(51.87, -2.23), 132, 85, 320),
            GridNode("cheltenham", "Cheltenham GSP", "gsp", Coords(51.90, -2.07), 132, 72, 280),
            GridNode("swindon", "Swindon GSP", "gsp", Coords(51.55, -1.78), 132, 95, 380),
            GridNode("melksham", "Melksham GSP", "gsp", Coords(51.38, -2.13), 275, 125, 280),
            GridNode("bristol-seabank", "Seabank GSP", "gsp", Coords(51.53, -2.67), 400, 75, 1200),
            GridNode("bristol-iron-acton", "Iron Acton GSP", "gsp", Coords(51.55, -2.48), 275, 95, 520),
            GridNode("bristol-filton", "Filton GSP", "gsp", Coords(51.50, -2.57), 132, 65, 380),
            GridNode("bristol-avonmouth", "Avonmouth GSP", "gsp", Coords(51.50, -2.70), 275, 85, 480),
            GridNode("bridgwater", "Bridgwater GSP", "gsp", Coords(51.13, -3.00), 275, 115, 280),
            GridNode("hinkley", "Hinkley Point GSP", "gsp", Coords(51.21, -3.13), 400, 25, 3200),
            GridNode("taunton", "Taunton GSP", "gsp", Coords(51.02, -3.10), 132, 95, 220),
            GridNode("exeter", "Exeter GSP", "gsp", Coords(50.73, -3.52), 132, 85, 320),
            GridNode("plymouth", "Plymouth GSP", "gsp", Coords(50.38, -4.12), 132, 75, 280),
            GridNode("indian-queens", "Indian Queens GSP", "gsp", Coords(50.40, -4.92), 400, 145, 180),
            GridNode("landulph", "Landulph GSP", "gsp", Coords(50.45, -4.23), 275, 125, 220),
            GridNode("alverdiscott", "Alverdiscott GSP", "gsp", Coords(51.02, -4.15), 275, 155, 180),
            GridNode("barnstaple", "Barnstaple GSP", "gsp", Coords(51.08, -4.05), 132, 95, 140),

            # ============= SOUTH ENGLAND =============
            GridNode("didcot", "Didcot GSP", "gsp", Coords(51.62, -1.27), 400, 75, 2000),
            GridNode("cowley", "Cowley GSP", "gsp", Coords(51.73, -1.22), 275, 95, 380),
            GridNode("reading", "Reading GSP", "gsp", Coords(51.45, -0.97), 132, 72, 420),
            GridNode("newbury", "Newbury GSP", "gsp", Coords(51.40, -1.32), 132, 85, 280),
            GridNode("basingstoke", "Basingstoke GSP", "gsp", Coords(51.27, -1.08), 132, 92, 320),
            GridNode("winchester", "Winchester GSP", "gsp", Coords(51.07, -1.32), 132, 105, 220),
            GridNode("portsmouth", "Portsmouth GSP", "gsp", Coords(50.82, -1.07), 132, 68, 380),
            GridNode("fawley", "Fawley GSP", "gsp", Coords(50.82, -1.33), 400, 115, 1200),
            GridNode("southampton", "Southampton GSP", "gsp", Coords(50.90, -1.40), 132, 58, 520),
            GridNode("bournemouth", "Bournemouth GSP", "gsp", Coords(50.72, -1.87), 132, 75, 280),
            GridNode("poole", "Poole GSP", "gsp", Coords(50.72, -2.00), 132, 82, 220),
            GridNode("mannington", "Mannington GSP", "gsp", Coords(50.85, -1.88), 400, 145, 380),

            # ============= SOUTH EAST ENGLAND =============
            GridNode("rye-house", "Rye House GSP", "gsp", Coords(51.77, -0.01), 400, 55, 680),
            GridNode("waltham-cross", "Waltham Cross GSP", "gsp", Coords(51.69, -0.03), 400, 100, 510),
            GridNode("brimsdown", "Brimsdown GSP", "gsp", Coords(51.66, -0.03), 132, 55, 340),
            GridNode("tottenham", "Tottenham GSP", "gsp", Coords(51.60, -0.07), 132, 42, 480),
            GridNode("hackney", "Hackney GSP", "gsp", Coords(51.55, -0.06), 132, 35, 420),
            GridNode("city-road", "City Road GSP", "gsp", Coords(51.53, -0.10), 400, 25, 890),
            GridNode("st-johns-wood", "St Johns Wood GSP", "gsp", Coords(51.53, -0.17), 400, 30, 650),
            GridNode("willesden", "Willesden GSP", "gsp", Coords(51.55, -0.23), 275, 45, 520),
            GridNode("mill-hill", "Mill Hill GSP", "gsp", Coords(51.62, -0.22), 132, 58, 380),
            GridNode("elstree", "Elstree GSP", "gsp", Coords(51.65, -0.28), 400, 85, 420),
            GridNode("barking", "Barking GSP", "gsp", Coords(51.53, 0.08), 400, 85, 720),
            GridNode("west-ham", "West Ham GSP", "gsp", Coords(51.53, 0.00), 132, 60, 490),
            GridNode("new-cross", "New Cross GSP", "gsp", Coords(51.47, -0.04), 132, 45, 380),
            GridNode("wimbledon", "Wimbledon GSP", "gsp", Coords(51.42, -0.21), 132, 75, 380),
            GridNode("west-weybridge", "West Weybridge GSP", "gsp", Coords(51.37, -0.45), 275, 92, 420),
            GridNode("chessington", "Chessington GSP", "gsp", Coords(51.35, -0.30), 275, 78, 380),
            GridNode("littlebrook", "Littlebrook GSP", "gsp", Coords(51.45, 0.25), 400, 130, 520),
            GridNode("northfleet", "Northfleet East GSP", "gsp", Coords(51.43, 0.33), 400, 75, 410),
            GridNode("grain", "Grain GSP", "gsp", Coords(51.45, 0.72), 400, 110, 890),
            GridNode("kemsley", "Kemsley GSP", "gsp", Coords(51.35, 0.73), 132, 65, 280),
            GridNode("canterbury", "Canterbury North GSP", "gsp", Coords(51.28, 1.08), 400, 95, 320),
            GridNode("sellindge", "Sellindge GSP", "gsp", Coords(51.10, 0.98), 400, 200, 2000),
            GridNode("dungeness", "Dungeness GSP", "gsp", Coords(50.91, 0.96), 400, 45, 1200),
            GridNode("bolney", "Bolney GSP", "gsp", Coords(50.97, -0.18), 400, 120, 450),
            GridNode("ninfield", "Ninfield GSP", "gsp", Coords(50.88, 0.42), 132, 95, 280),
            GridNode("hastings", "Hastings GSP", "gsp", Coords(50.85, 0.58), 132, 88, 220),

            # ============= WALES =============
            GridNode("wylfa", "Wylfa GSP", "gsp", Coords(53.42, -4.48), 400, 180, 970),
            GridNode("pentir", "Pentir GSP", "gsp", Coords(53.18, -4.18), 400, 95, 680),
            GridNode("trawsfynydd", "Trawsfynydd GSP", "gsp", Coords(52.90, -3.93), 400, 55, 240),
            GridNode("legacy", "Legacy GSP", "gsp", Coords(53.05, -3.72), 400, 130, 420),
            GridNode("connah's-quay", "Connah's Quay GSP", "gsp", Coords(53.22, -3.07), 400, 105, 1400),
            GridNode("ffestiniog", "Ffestiniog GSP", "gsp", Coords(52.98, -3.95), 275, 145, 360),
            GridNode("dinorwig", "Dinorwig GSP", "gsp", Coords(53.12, -4.12), 400, 125, 1800),
            GridNode("aberystwyth", "Aberystwyth GSP", "gsp", Coords(52.42, -4.08), 132, 115, 120),
            GridNode("carmarthen", "Carmarthen GSP", "gsp", Coords(51.85, -4.30), 132, 95, 180),
            GridNode("pembroke", "Pembroke GSP", "gsp", Coords(51.68, -4.95), 400, 85, 2000),
            GridNode("swansea-north", "Swansea North GSP", "gsp", Coords(51.65, -3.93), 275, 75, 380),
            GridNode("swansea-port-talbot", "Port Talbot GSP", "gsp", Coords(51.60, -3.78), 275, 68, 680),
            GridNode("cardiff-tremorfa", "Tremorfa GSP", "gsp", Coords(51.48, -3.15), 275, 82, 520),
            GridNode("cardiff-east", "Cardiff East GSP", "gsp", Coords(51.47, -3.12), 275, 78, 420),
            GridNode("uskmouth", "Uskmouth GSP", "gsp", Coords(51.55, -2.95), 400, 95, 850),
            GridNode("newport", "Newport GSP", "gsp", Coords(51.58, -3.00), 132, 65, 380),
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

"""
GridBridge UK - Multi-Source Data Mapping Integration

Integrates data from multiple UK grid sources:
- OpenEnergyMonitor UK Grid (Elexon real-time)
- Kilowatts Grid (generator locations + balancing)
- National Grid Data Portal (historical streams)
- CfD-Watch (Contracts for Difference)
- Octopy-Energy (tariffs and consumption)
- ETS-Watch (carbon market prices)
"""

from .sources import (
    DataSourceRegistry,
    KilowattsGridSource,
    NGDataPortalSource,
    CfDWatchSource,
    OctopyEnergySource,
    ETSWatchSource,
    CarbonIntensitySource,
)
from .overlay import GridOverlay, OverlayLayer
from .aggregator import MultiSourceAggregator

__all__ = [
    "DataSourceRegistry",
    "KilowattsGridSource",
    "NGDataPortalSource",
    "CfDWatchSource",
    "OctopyEnergySource",
    "ETSWatchSource",
    "CarbonIntensitySource",
    "GridOverlay",
    "OverlayLayer",
    "MultiSourceAggregator",
]

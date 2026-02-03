"""
GridBridge UK - Multi-Source Data Connectors

Data source integrations for UK grid mapping overlay.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional, Any
from enum import Enum
import json
import hashlib

import pandas as pd
import numpy as np
import requests


# =============================================================================
# Data Models
# =============================================================================

class FuelType(str, Enum):
    GAS = "gas"
    COAL = "coal"
    NUCLEAR = "nuclear"
    WIND = "wind"
    SOLAR = "solar"
    HYDRO = "hydro"
    BIOMASS = "biomass"
    BATTERY = "battery"
    IMPORTS = "imports"
    OTHER = "other"


@dataclass
class Coords:
    lat: float
    lng: float

    def to_dict(self) -> dict:
        return {"lat": self.lat, "lng": self.lng}


@dataclass
class Generator:
    id: str
    name: str
    fuel_type: FuelType
    coords: Coords
    capacity_mw: float = 0
    output_mw: float = 0
    bids_mw: float = 0
    offers_mw: float = 0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "fuel_type": self.fuel_type.value,
            "coords": self.coords.to_dict(),
            "capacity_mw": self.capacity_mw,
            "output_mw": self.output_mw,
            "bids_mw": self.bids_mw,
            "offers_mw": self.offers_mw,
        }


@dataclass
class Interconnector:
    id: str
    name: str
    country_code: str
    coords: Coords
    capacity_mw: float = 0
    flow_mw: float = 0  # positive = import, negative = export

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "country_code": self.country_code,
            "coords": self.coords.to_dict(),
            "capacity_mw": self.capacity_mw,
            "flow_mw": self.flow_mw,
        }


@dataclass
class GridNode:
    id: str
    name: str
    node_type: str  # "gsp", "bsp", "substation", "generator"
    coords: Coords
    voltage_kv: float = 0
    headroom_mw: float = 0
    load_mw: float = 0
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "node_type": self.node_type,
            "coords": self.coords.to_dict(),
            "voltage_kv": self.voltage_kv,
            "headroom_mw": self.headroom_mw,
            "load_mw": self.load_mw,
            "metadata": self.metadata,
        }


@dataclass
class CfDContract:
    id: str
    name: str
    technology: str
    capacity_mw: float
    strike_price: float
    allocation_round: str
    status: str
    coords: Optional[Coords] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "technology": self.technology,
            "capacity_mw": self.capacity_mw,
            "strike_price": self.strike_price,
            "allocation_round": self.allocation_round,
            "status": self.status,
            "coords": self.coords.to_dict() if self.coords else None,
        }


@dataclass
class MarketPrice:
    timestamp: datetime
    price: float
    currency: str
    market: str
    unit: str

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "price": self.price,
            "currency": self.currency,
            "market": self.market,
            "unit": self.unit,
        }


# =============================================================================
# Base Data Source
# =============================================================================

class DataSource(ABC):
    """Abstract base class for grid data sources."""

    def __init__(self, name: str, base_url: str, cache_ttl_seconds: int = 300):
        self.name = name
        self.base_url = base_url
        self.cache_ttl = cache_ttl_seconds
        self._cache: dict[str, tuple[datetime, Any]] = {}

    def _cache_key(self, endpoint: str, params: dict) -> str:
        param_str = json.dumps(params, sort_keys=True)
        return hashlib.md5(f"{endpoint}:{param_str}".encode()).hexdigest()

    def _get_cached(self, key: str) -> Optional[Any]:
        if key in self._cache:
            cached_time, data = self._cache[key]
            if datetime.now(timezone.utc) - cached_time < timedelta(seconds=self.cache_ttl):
                return data
        return None

    def _set_cached(self, key: str, data: Any):
        self._cache[key] = (datetime.now(timezone.utc), data)

    def _request(self, endpoint: str, params: dict = None, use_cache: bool = True) -> dict:
        params = params or {}
        cache_key = self._cache_key(endpoint, params)

        if use_cache:
            cached = self._get_cached(cache_key)
            if cached is not None:
                return cached

        url = f"{self.base_url}{endpoint}"
        try:
            r = requests.get(url, params=params, timeout=30)
            r.raise_for_status()
            data = r.json()
            self._set_cached(cache_key, data)
            return data
        except requests.RequestException as e:
            return {"error": str(e), "source": self.name}

    @abstractmethod
    def fetch_latest(self) -> dict:
        """Fetch latest data from the source."""
        pass

    @abstractmethod
    def get_generators(self) -> list[Generator]:
        """Get generator data with locations."""
        pass


# =============================================================================
# Kilowatts Grid Source
# =============================================================================

class KilowattsGridSource(DataSource):
    """
    Kilowatts Grid - Real-time GB generator output with coordinates.

    Data includes:
    - Generator locations (lat/lng)
    - Real-time output (MW)
    - Balancing bids/offers
    - Fuel type classification

    Source: https://github.com/BenjaminWatts/kilowatts-grid
    """

    # CDN endpoint for summary data
    CDN_DOMAIN = "d3n6b26b0e2e0z.cloudfront.net"

    def __init__(self, cache_ttl_seconds: int = 60):
        super().__init__(
            name="kilowatts-grid",
            base_url=f"https://{self.CDN_DOMAIN}",
            cache_ttl_seconds=cache_ttl_seconds,
        )

    def fetch_latest(self) -> dict:
        """Fetch latest GB summary from CDN."""
        return self._request("/gb/summary_output.json")

    def get_generators(self) -> list[Generator]:
        """Get all generators with coordinates and output."""
        data = self.fetch_latest()
        if "error" in data:
            return []

        generators = []
        for gen in data.get("generators", []):
            coords = gen.get("coords", {})
            fuel_str = gen.get("fuel_type", "other").lower()
            try:
                fuel_type = FuelType(fuel_str)
            except ValueError:
                fuel_type = FuelType.OTHER

            generators.append(Generator(
                id=gen.get("code", ""),
                name=gen.get("name", ""),
                fuel_type=fuel_type,
                coords=Coords(lat=coords.get("lat", 0), lng=coords.get("lng", 0)),
                capacity_mw=gen.get("cp", 0),
                output_mw=gen.get("ac", 0),
                bids_mw=gen.get("bids", 0),
                offers_mw=gen.get("offers", 0),
            ))
        return generators

    def get_interconnectors(self) -> list[Interconnector]:
        """Get interconnector flows."""
        data = self.fetch_latest()
        if "error" in data:
            return []

        interconnectors = []
        for market in data.get("foreign_markets", []):
            country = market.get("code", "").upper()
            coords = market.get("coords", {})

            for ic in market.get("interconnectors", []):
                flow = ic.get("ac", 0)  # Actual flow
                interconnectors.append(Interconnector(
                    id=ic.get("code", ""),
                    name=ic.get("name", ""),
                    country_code=country,
                    coords=Coords(lat=coords.get("lat", 0), lng=coords.get("lng", 0)),
                    capacity_mw=ic.get("cp", 0),
                    flow_mw=flow,
                ))
        return interconnectors

    def get_totals_by_fuel(self) -> dict[str, float]:
        """Get total generation by fuel type."""
        data = self.fetch_latest()
        if "error" in data:
            return {}

        return {
            t.get("code", "unknown"): t.get("ac", 0)
            for t in data.get("totals", [])
        }

    def get_balancing_totals(self) -> dict:
        """Get total balancing bids and offers."""
        data = self.fetch_latest()
        return data.get("balancing_totals", {"bids": 0, "offers": 0})


# =============================================================================
# National Grid Data Portal Source
# =============================================================================

class NGDataPortalSource(DataSource):
    """
    National Grid ESO Data Portal via CKAN API.

    Streams available:
    - demand-outturn: Historic demand data
    - generation-mix: Generation by fuel type
    - carbon-intensity-forecast: Carbon intensity predictions
    - embedded-wind-and-solar: Distributed generation estimates

    Source: https://github.com/OSUKED/NGDataPortal
    """

    # Stream to resource ID mapping
    STREAMS = {
        "demand-outturn": "177f6fa4-ae49-4182-81ea-0c6b35f26ca6",
        "generation-mix": "88313ae5-94e4-4ad7-9c78-79e7f5cc0906",
        "carbon-intensity-forecast": "7c0411cd-2714-4bb5-a408-571b56a80690",
        "embedded-wind-and-solar": "db6c038f-98af-4570-ab60-24d71ebd0ae5",
        "system-frequency": "9a203f38-6c70-4d4e-a4ed-d1bf64c2abb7",
        "demand-forecast": "93c3048e-1dab-4057-a2a9-417540583929",
    }

    def __init__(self, cache_ttl_seconds: int = 300):
        super().__init__(
            name="ng-data-portal",
            base_url="https://national-grid-admin.ckan.io/api/3/action",
            cache_ttl_seconds=cache_ttl_seconds,
        )

    def fetch_latest(self) -> dict:
        """Fetch latest demand outturn."""
        return self.query_stream("demand-outturn", limit=48)

    def query_stream(
        self,
        stream: str,
        limit: int = 100,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> dict:
        """Query a specific data stream."""
        if stream not in self.STREAMS:
            return {"error": f"Unknown stream: {stream}", "available": list(self.STREAMS.keys())}

        resource_id = self.STREAMS[stream]

        if start_date and end_date:
            # Use SQL query for date filtering
            sql = f"""
                SELECT * FROM "{resource_id}"
                WHERE "DATETIME" BETWEEN '{start_date}'::timestamp AND '{end_date}'::timestamp
                ORDER BY "DATETIME" DESC
                LIMIT {limit}
            """
            params = {"sql": sql}
            endpoint = "/datastore_search_sql"
        else:
            params = {"resource_id": resource_id, "limit": limit}
            endpoint = "/datastore_search"

        return self._request(endpoint, params)

    def get_generators(self) -> list[Generator]:
        """NG Data Portal doesn't provide generator locations."""
        return []

    def get_demand_history(self, days: int = 7) -> pd.DataFrame:
        """Get demand history as DataFrame."""
        end = datetime.now(timezone.utc)
        start = end - timedelta(days=days)

        data = self.query_stream(
            "demand-outturn",
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d"),
            limit=days * 48,  # 48 settlement periods per day
        )

        if "error" in data or "result" not in data:
            return pd.DataFrame()

        records = data["result"].get("records", [])
        if not records:
            return pd.DataFrame()

        df = pd.DataFrame(records)
        if "DATETIME" in df.columns:
            df["DATETIME"] = pd.to_datetime(df["DATETIME"])
            df = df.set_index("DATETIME").sort_index()
        return df

    def get_embedded_generation(self) -> dict:
        """Get latest embedded wind and solar estimates."""
        data = self.query_stream("embedded-wind-and-solar", limit=1)
        if "result" in data and data["result"].get("records"):
            return data["result"]["records"][0]
        return {}


# =============================================================================
# Carbon Intensity API Source
# =============================================================================

class CarbonIntensitySource(DataSource):
    """
    UK National Grid Carbon Intensity API.

    Provides:
    - Real-time carbon intensity (gCO2/kWh)
    - Regional breakdown
    - Generation mix percentages
    - Forecasts

    Source: https://carbonintensity.org.uk/
    """

    def __init__(self, cache_ttl_seconds: int = 300):
        super().__init__(
            name="carbon-intensity",
            base_url="https://api.carbonintensity.org.uk",
            cache_ttl_seconds=cache_ttl_seconds,
        )

    def fetch_latest(self) -> dict:
        """Fetch current carbon intensity."""
        return self._request("/intensity")

    def get_generators(self) -> list[Generator]:
        """Carbon Intensity API doesn't provide generator data."""
        return []

    def get_current_intensity(self) -> dict:
        """Get current carbon intensity with forecast."""
        data = self._request("/intensity")
        if "data" in data and data["data"]:
            return data["data"][0]
        return {}

    def get_generation_mix(self) -> dict:
        """Get current generation mix percentages."""
        data = self._request("/generation")
        if "data" in data:
            return {
                item["fuel"]: item["perc"]
                for item in data["data"].get("generationmix", [])
            }
        return {}

    def get_regional_intensity(self) -> list[dict]:
        """Get carbon intensity by DNO region."""
        data = self._request("/regional")
        if "data" in data:
            regions = data["data"]
            if isinstance(regions, list):
                return regions
            return regions.get("regions", [])
        return []

    def get_regional_map_data(self) -> list[dict]:
        """Get regional data formatted for map overlay."""
        regions = self.get_regional_intensity()
        # DNO region approximate centroids
        region_coords = {
            1: {"lat": 51.5, "lng": -0.1, "name": "North Scotland"},
            2: {"lat": 56.5, "lng": -4.0, "name": "South Scotland"},
            3: {"lat": 54.5, "lng": -1.5, "name": "North East England"},
            4: {"lat": 53.5, "lng": -2.5, "name": "North West England"},
            5: {"lat": 53.8, "lng": -1.5, "name": "Yorkshire"},
            6: {"lat": 52.5, "lng": -1.5, "name": "West Midlands"},
            7: {"lat": 52.5, "lng": 0.5, "name": "East Midlands"},
            8: {"lat": 52.0, "lng": 1.0, "name": "East England"},
            9: {"lat": 51.5, "lng": -1.5, "name": "South West England"},
            10: {"lat": 51.3, "lng": -0.5, "name": "South England"},
            11: {"lat": 51.5, "lng": -0.1, "name": "London"},
            12: {"lat": 51.3, "lng": 0.5, "name": "South East England"},
            13: {"lat": 52.0, "lng": -3.5, "name": "Wales"},
        }

        result = []
        for region in regions:
            region_id = region.get("regionid", 0)
            if region_id in region_coords:
                intensity = region.get("intensity", {})
                result.append({
                    "id": region_id,
                    "name": region_coords[region_id]["name"],
                    "coords": {
                        "lat": region_coords[region_id]["lat"],
                        "lng": region_coords[region_id]["lng"],
                    },
                    "intensity": intensity.get("forecast", 0),
                    "index": intensity.get("index", "unknown"),
                })
        return result


# =============================================================================
# CfD Watch Source
# =============================================================================

class CfDWatchSource(DataSource):
    """
    Contracts for Difference (CfD) data from Low Carbon Contracts Company.

    Provides:
    - CfD project list by allocation round
    - Strike prices
    - Technology types
    - Project status

    Source: https://github.com/OSUKED/CfD-Watch
    """

    def __init__(self, cache_ttl_seconds: int = 3600):  # 1 hour cache
        super().__init__(
            name="cfd-watch",
            base_url="https://www.lowcarboncontracts.uk",
            cache_ttl_seconds=cache_ttl_seconds,
        )
        self._projects: list[CfDContract] = []

    def fetch_latest(self) -> dict:
        """Fetch CfD data by scraping the LCCC website."""
        return self._scrape_cfd_data()

    def _scrape_cfd_data(self) -> dict:
        """Scrape CfD data from Low Carbon Contracts Company."""
        allocation_rounds = [
            "Allocation Round 1",
            "Allocation Round 2",
            "Allocation Round 3",
            "Allocation Round 4",
            "Allocation Round 5",
            "Investment Contract",
        ]

        all_projects = []
        for allocation_round in allocation_rounds:
            try:
                params = {
                    "agreement_type": "All",
                    "allocation_round[]": allocation_round,
                    "sort_by": "name_1",
                    "page": 0,
                }
                r = requests.get(f"{self.base_url}/cfds", params=params, timeout=30)
                if r.ok:
                    # Parse HTML table
                    tables = pd.read_html(r.text)
                    if tables:
                        df = tables[0]
                        df["allocation_round"] = allocation_round
                        all_projects.append(df)
            except Exception:
                continue

        if all_projects:
            combined = pd.concat(all_projects, ignore_index=True)
            return {"success": True, "projects": combined.to_dict(orient="records")}
        return {"success": False, "projects": []}

    def get_generators(self) -> list[Generator]:
        """CfD Watch doesn't provide real-time generator data."""
        return []

    def get_cfd_contracts(self) -> list[CfDContract]:
        """Get all CfD contracts."""
        data = self.fetch_latest()
        contracts = []

        for proj in data.get("projects", []):
            # Extract fields with fallbacks
            name = proj.get("Name", proj.get("name_1", "Unknown"))
            tech = proj.get("Technology", "Unknown")
            capacity = proj.get("Capacity (MW)", 0)
            strike = proj.get("Strike Price (£/MWh)", proj.get("Current Strike Price", 0))
            alloc = proj.get("allocation_round", "Unknown")
            status = proj.get("Status", "Active")

            # Parse numeric fields
            try:
                capacity = float(str(capacity).replace(",", ""))
            except (ValueError, TypeError):
                capacity = 0

            try:
                strike = float(str(strike).replace("£", "").replace(",", ""))
            except (ValueError, TypeError):
                strike = 0

            contracts.append(CfDContract(
                id=hashlib.md5(name.encode()).hexdigest()[:8],
                name=name,
                technology=tech,
                capacity_mw=capacity,
                strike_price=strike,
                allocation_round=alloc,
                status=status,
            ))

        return contracts

    def get_contracts_by_technology(self) -> dict[str, list[CfDContract]]:
        """Group contracts by technology type."""
        contracts = self.get_cfd_contracts()
        result: dict[str, list[CfDContract]] = {}
        for c in contracts:
            if c.technology not in result:
                result[c.technology] = []
            result[c.technology].append(c)
        return result

    def get_capacity_by_round(self) -> dict[str, float]:
        """Get total CfD capacity by allocation round."""
        contracts = self.get_cfd_contracts()
        result: dict[str, float] = {}
        for c in contracts:
            if c.allocation_round not in result:
                result[c.allocation_round] = 0
            result[c.allocation_round] += c.capacity_mw
        return result


# =============================================================================
# Octopy Energy Source
# =============================================================================

class OctopyEnergySource(DataSource):
    """
    Octopus Energy API for tariff and pricing data.

    Provides:
    - Product tariffs
    - Unit rates
    - Agile pricing

    Source: https://github.com/OSUKED/Octopy-Energy
    """

    def __init__(self, api_key: Optional[str] = None, cache_ttl_seconds: int = 300):
        super().__init__(
            name="octopy-energy",
            base_url="https://api.octopus.energy",
            cache_ttl_seconds=cache_ttl_seconds,
        )
        self.api_key = api_key

    def fetch_latest(self) -> dict:
        """Fetch available products."""
        return self._request("/v1/products/")

    def get_generators(self) -> list[Generator]:
        """Octopy doesn't provide generator data."""
        return []

    def get_products(self) -> list[dict]:
        """Get available Octopus Energy products."""
        data = self._request("/v1/products/")
        return data.get("results", [])

    def get_agile_rates(self, region: str = "C") -> pd.DataFrame:
        """
        Get Agile tariff rates for a region.

        Regions: A-P (DNO regions)
        """
        product_code = "AGILE-24-10-01"  # Current Agile product
        tariff_code = f"E-1R-{product_code}-{region}"

        data = self._request(
            f"/v1/products/{product_code}/electricity-tariffs/{tariff_code}/standard-unit-rates/",
            params={"page_size": 200},
        )

        if "results" not in data:
            return pd.DataFrame()

        df = pd.DataFrame(data["results"])
        if "valid_from" in df.columns:
            df["valid_from"] = pd.to_datetime(df["valid_from"])
            df = df.set_index("valid_from").sort_index()
        return df

    def get_current_agile_price(self, region: str = "C") -> Optional[float]:
        """Get current Agile price for a region."""
        df = self.get_agile_rates(region)
        if df.empty:
            return None
        now = pd.Timestamp.now(tz="Europe/London")
        # Find rate valid for current time
        valid_rates = df[df.index <= now]
        if not valid_rates.empty:
            return float(valid_rates.iloc[-1].get("value_inc_vat", 0))
        return None


# =============================================================================
# ETS Watch Source
# =============================================================================

class ETSWatchSource(DataSource):
    """
    EU Emissions Trading Scheme price data.

    Provides:
    - Carbon price (EUR/tonne CO2)
    - Historical OHLCV data

    Source: https://github.com/OSUKED/ETS-Watch
    """

    def __init__(self, cache_ttl_seconds: int = 3600):
        super().__init__(
            name="ets-watch",
            base_url="https://raw.githubusercontent.com/OSUKED/ETS-Watch/main",
            cache_ttl_seconds=cache_ttl_seconds,
        )

    def fetch_latest(self) -> dict:
        """Fetch latest ETS market data."""
        return self._request("/data/ets_mkt.json")

    def get_generators(self) -> list[Generator]:
        """ETS Watch doesn't provide generator data."""
        return []

    def get_carbon_price(self) -> Optional[MarketPrice]:
        """Get latest EU ETS carbon price."""
        data = self.fetch_latest()
        if "error" in data or "close" not in data:
            return None

        dates = data.get("datetime", [])
        prices = data.get("close", [])

        if not dates or not prices:
            return None

        # Get latest non-null price
        for i in range(len(prices) - 1, -1, -1):
            if prices[i] is not None:
                return MarketPrice(
                    timestamp=datetime.fromisoformat(dates[i]),
                    price=float(prices[i]),
                    currency="EUR",
                    market="EU-ETS",
                    unit="EUR/tonne CO2",
                )
        return None

    def get_price_history(self) -> pd.DataFrame:
        """Get full ETS price history."""
        data = self.fetch_latest()
        if "error" in data:
            return pd.DataFrame()

        df = pd.DataFrame({
            "datetime": data.get("datetime", []),
            "open": data.get("open", []),
            "high": data.get("high", []),
            "low": data.get("low", []),
            "close": data.get("close", []),
            "volume": data.get("volume", []),
        })

        if "datetime" in df.columns:
            df["datetime"] = pd.to_datetime(df["datetime"])
            df = df.set_index("datetime").sort_index()
            df = df.replace(-99999, np.nan)  # Handle null placeholder

        return df


# =============================================================================
# Data Source Registry
# =============================================================================

class DataSourceRegistry:
    """Registry for managing multiple data sources."""

    def __init__(self):
        self._sources: dict[str, DataSource] = {}

    def register(self, source: DataSource):
        """Register a data source."""
        self._sources[source.name] = source

    def get(self, name: str) -> Optional[DataSource]:
        """Get a registered source by name."""
        return self._sources.get(name)

    def list_sources(self) -> list[str]:
        """List all registered source names."""
        return list(self._sources.keys())

    def fetch_all(self) -> dict[str, dict]:
        """Fetch latest data from all sources."""
        return {
            name: source.fetch_latest()
            for name, source in self._sources.items()
        }

    def get_all_generators(self) -> list[Generator]:
        """Get generators from all sources."""
        generators = []
        for source in self._sources.values():
            generators.extend(source.get_generators())
        return generators

    @classmethod
    def create_default(cls) -> "DataSourceRegistry":
        """Create registry with all default sources."""
        registry = cls()
        registry.register(KilowattsGridSource())
        registry.register(NGDataPortalSource())
        registry.register(CarbonIntensitySource())
        registry.register(CfDWatchSource())
        registry.register(OctopyEnergySource())
        registry.register(ETSWatchSource())
        return registry

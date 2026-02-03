"""
GridBridge UK - Multi-Source Data Aggregator

Aggregates and correlates data from multiple grid sources
to provide unified insights.
"""

from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from typing import Optional
import pandas as pd
import numpy as np

from .sources import (
    DataSourceRegistry,
    KilowattsGridSource,
    NGDataPortalSource,
    CarbonIntensitySource,
    CfDWatchSource,
    OctopyEnergySource,
    ETSWatchSource,
    Generator,
    FuelType,
)


@dataclass
class AggregatedSnapshot:
    """Complete grid state snapshot from all sources."""

    timestamp: datetime

    # Generation
    total_generation_mw: float
    generation_by_fuel: dict[str, float]
    generator_count: int

    # Demand
    total_demand_mw: float
    embedded_wind_mw: float
    embedded_solar_mw: float

    # Interconnectors
    net_imports_mw: float
    imports_by_country: dict[str, float]

    # Carbon
    carbon_intensity: float
    carbon_index: str

    # Markets
    ets_price_eur: Optional[float]
    agile_price_gbp: Optional[float]

    # CfD
    cfd_total_capacity_mw: float
    cfd_project_count: int

    # Balancing
    total_bids_mw: float
    total_offers_mw: float

    def to_dict(self) -> dict:
        return {
            "timestamp": self.timestamp.isoformat(),
            "generation": {
                "total_mw": self.total_generation_mw,
                "by_fuel": self.generation_by_fuel,
                "generator_count": self.generator_count,
            },
            "demand": {
                "total_mw": self.total_demand_mw,
                "embedded_wind_mw": self.embedded_wind_mw,
                "embedded_solar_mw": self.embedded_solar_mw,
            },
            "interconnectors": {
                "net_imports_mw": self.net_imports_mw,
                "by_country": self.imports_by_country,
            },
            "carbon": {
                "intensity_gco2_kwh": self.carbon_intensity,
                "index": self.carbon_index,
            },
            "markets": {
                "ets_price_eur": self.ets_price_eur,
                "agile_price_gbp": self.agile_price_gbp,
            },
            "cfd": {
                "total_capacity_mw": self.cfd_total_capacity_mw,
                "project_count": self.cfd_project_count,
            },
            "balancing": {
                "bids_mw": self.total_bids_mw,
                "offers_mw": self.total_offers_mw,
            },
        }


class MultiSourceAggregator:
    """
    Aggregates data from multiple UK grid sources into unified views.

    Sources integrated:
    - Kilowatts Grid: Real-time generation, balancing
    - NG Data Portal: Historical demand, embedded gen
    - Carbon Intensity: Regional carbon data
    - CfD Watch: Contract for Difference projects
    - Octopy Energy: Electricity pricing
    - ETS Watch: Carbon market prices
    """

    def __init__(self, registry: Optional[DataSourceRegistry] = None):
        self.registry = registry or DataSourceRegistry.create_default()
        self._snapshot_cache: Optional[tuple[datetime, AggregatedSnapshot]] = None
        self._cache_ttl = timedelta(seconds=60)

    def get_snapshot(self, use_cache: bool = True) -> AggregatedSnapshot:
        """Get aggregated snapshot from all sources."""
        now = datetime.now(timezone.utc)

        # Check cache
        if use_cache and self._snapshot_cache:
            cache_time, cached_snapshot = self._snapshot_cache
            if now - cache_time < self._cache_ttl:
                return cached_snapshot

        # Fetch from all sources
        snapshot = self._build_snapshot()
        self._snapshot_cache = (now, snapshot)
        return snapshot

    def _build_snapshot(self) -> AggregatedSnapshot:
        """Build snapshot by fetching all sources."""
        now = datetime.now(timezone.utc)

        # Kilowatts Grid - Generation and balancing
        kw_source: KilowattsGridSource = self.registry.get("kilowatts-grid")
        generators = kw_source.get_generators() if kw_source else []
        totals = kw_source.get_totals_by_fuel() if kw_source else {}
        balancing = kw_source.get_balancing_totals() if kw_source else {"bids": 0, "offers": 0}
        interconnectors = kw_source.get_interconnectors() if kw_source else []

        total_gen = sum(totals.values())
        gen_by_fuel = {k: round(v, 1) for k, v in totals.items()}

        # Net imports from interconnectors
        net_imports = sum(ic.flow_mw for ic in interconnectors)
        imports_by_country = {}
        for ic in interconnectors:
            if ic.country_code not in imports_by_country:
                imports_by_country[ic.country_code] = 0
            imports_by_country[ic.country_code] += ic.flow_mw

        # NG Data Portal - Embedded generation
        ng_source: NGDataPortalSource = self.registry.get("ng-data-portal")
        embedded = ng_source.get_embedded_generation() if ng_source else {}
        embedded_wind = embedded.get("EMBEDDED_WIND_GENERATION", 0) or 0
        embedded_solar = embedded.get("EMBEDDED_SOLAR_GENERATION", 0) or 0

        # Carbon Intensity
        ci_source: CarbonIntensitySource = self.registry.get("carbon-intensity")
        intensity_data = ci_source.get_current_intensity() if ci_source else {}
        carbon_intensity = intensity_data.get("intensity", {}).get("forecast", 0)
        carbon_index = intensity_data.get("intensity", {}).get("index", "unknown")

        # ETS Price
        ets_source: ETSWatchSource = self.registry.get("ets-watch")
        ets_price = None
        if ets_source:
            market_price = ets_source.get_carbon_price()
            if market_price:
                ets_price = market_price.price

        # Agile Price
        octo_source: OctopyEnergySource = self.registry.get("octopy-energy")
        agile_price = octo_source.get_current_agile_price() if octo_source else None

        # CfD Data
        cfd_source: CfDWatchSource = self.registry.get("cfd-watch")
        cfd_contracts = cfd_source.get_cfd_contracts() if cfd_source else []
        cfd_capacity = sum(c.capacity_mw for c in cfd_contracts)

        # Calculate demand (generation + imports)
        total_demand = total_gen + net_imports

        return AggregatedSnapshot(
            timestamp=now,
            total_generation_mw=round(total_gen, 1),
            generation_by_fuel=gen_by_fuel,
            generator_count=len(generators),
            total_demand_mw=round(total_demand, 1),
            embedded_wind_mw=round(embedded_wind, 1),
            embedded_solar_mw=round(embedded_solar, 1),
            net_imports_mw=round(net_imports, 1),
            imports_by_country={k: round(v, 1) for k, v in imports_by_country.items()},
            carbon_intensity=round(carbon_intensity, 1),
            carbon_index=carbon_index,
            ets_price_eur=round(ets_price, 2) if ets_price else None,
            agile_price_gbp=round(agile_price, 2) if agile_price else None,
            cfd_total_capacity_mw=round(cfd_capacity, 1),
            cfd_project_count=len(cfd_contracts),
            total_bids_mw=round(balancing.get("bids", 0), 1),
            total_offers_mw=round(balancing.get("offers", 0), 1),
        )

    def get_generation_timeseries(self, hours: int = 24) -> pd.DataFrame:
        """
        Build generation time series combining multiple sources.

        Note: This requires historical data which may need API keys.
        Returns mock data structure for demonstration.
        """
        now = datetime.now(timezone.utc)
        periods = hours * 2  # 30-min settlement periods

        # Create time index
        idx = pd.date_range(
            end=now,
            periods=periods,
            freq="30min",
            tz="UTC",
        )

        # Get current generation mix as baseline
        kw_source: KilowattsGridSource = self.registry.get("kilowatts-grid")
        totals = kw_source.get_totals_by_fuel() if kw_source else {}

        # Simulate historical variation
        np.random.seed(42)

        data = {
            "timestamp": idx,
            "demand_mw": [],
            "wind_mw": [],
            "solar_mw": [],
            "gas_mw": [],
            "nuclear_mw": [],
            "imports_mw": [],
        }

        base_demand = totals.get("demand", 30000) or 30000
        base_wind = totals.get("wind", 8000) or 8000
        base_solar = totals.get("solar", 2000) or 2000
        base_gas = totals.get("gas", 12000) or 12000
        base_nuclear = totals.get("nuclear", 4500) or 4500
        base_imports = totals.get("imports", 2000) or 2000

        for i, ts in enumerate(idx):
            hour = ts.hour

            # Demand curve (higher during day)
            demand_factor = 0.8 + 0.4 * np.sin((hour - 6) * np.pi / 12) ** 2
            demand_noise = np.random.normal(1, 0.05)
            data["demand_mw"].append(base_demand * demand_factor * demand_noise)

            # Wind (variable)
            wind_factor = 0.5 + 0.5 * np.sin(i / 10)
            wind_noise = np.random.normal(1, 0.15)
            data["wind_mw"].append(max(0, base_wind * wind_factor * wind_noise))

            # Solar (daytime only)
            if 6 <= hour <= 20:
                solar_factor = np.sin((hour - 6) * np.pi / 14)
                solar_noise = np.random.normal(1, 0.1)
                data["solar_mw"].append(max(0, base_solar * solar_factor * solar_noise))
            else:
                data["solar_mw"].append(0)

            # Gas (fills gap)
            gas_noise = np.random.normal(1, 0.08)
            data["gas_mw"].append(base_gas * gas_noise)

            # Nuclear (stable)
            nuclear_noise = np.random.normal(1, 0.02)
            data["nuclear_mw"].append(base_nuclear * nuclear_noise)

            # Imports (variable)
            import_noise = np.random.normal(1, 0.2)
            data["imports_mw"].append(base_imports * import_noise)

        df = pd.DataFrame(data).set_index("timestamp")
        return df.round(1)

    def get_price_correlation(self) -> dict:
        """
        Analyze correlation between carbon price, electricity price,
        and carbon intensity.
        """
        # Get current values
        snapshot = self.get_snapshot()

        # Get Agile price history (if available)
        octo_source: OctopyEnergySource = self.registry.get("octopy-energy")
        agile_df = octo_source.get_agile_rates() if octo_source else pd.DataFrame()

        # Get ETS price history
        ets_source: ETSWatchSource = self.registry.get("ets-watch")
        ets_df = ets_source.get_price_history() if ets_source else pd.DataFrame()

        return {
            "current": {
                "carbon_intensity": snapshot.carbon_intensity,
                "ets_price_eur": snapshot.ets_price_eur,
                "agile_price_gbp": snapshot.agile_price_gbp,
            },
            "agile_rate_count": len(agile_df),
            "ets_history_days": len(ets_df),
            "insight": self._generate_price_insight(snapshot),
        }

    def _generate_price_insight(self, snapshot: AggregatedSnapshot) -> str:
        """Generate insight about current market conditions."""
        insights = []

        # Carbon intensity insight
        if snapshot.carbon_index == "very low":
            insights.append("Grid is very clean - good time for flexible loads")
        elif snapshot.carbon_index == "very high":
            insights.append("High carbon period - consider load shifting")

        # Price insight
        if snapshot.agile_price_gbp:
            if snapshot.agile_price_gbp < 10:
                insights.append(f"Agile price low at {snapshot.agile_price_gbp}p/kWh")
            elif snapshot.agile_price_gbp > 30:
                insights.append(f"Agile price elevated at {snapshot.agile_price_gbp}p/kWh")

        # Generation mix insight
        wind_pct = snapshot.generation_by_fuel.get("wind", 0) / max(snapshot.total_generation_mw, 1) * 100
        if wind_pct > 40:
            insights.append(f"High wind generation ({wind_pct:.0f}% of mix)")

        return " | ".join(insights) if insights else "Normal grid conditions"

    def get_cfd_analysis(self) -> dict:
        """Analyze CfD contract portfolio."""
        cfd_source: CfDWatchSource = self.registry.get("cfd-watch")
        if not cfd_source:
            return {"error": "CfD source not available"}

        by_tech = cfd_source.get_contracts_by_technology()
        by_round = cfd_source.get_capacity_by_round()

        # Calculate statistics
        all_contracts = cfd_source.get_cfd_contracts()
        strike_prices = [c.strike_price for c in all_contracts if c.strike_price > 0]

        return {
            "by_technology": {
                tech: {
                    "count": len(contracts),
                    "total_mw": sum(c.capacity_mw for c in contracts),
                    "avg_strike": (
                        sum(c.strike_price for c in contracts if c.strike_price > 0) /
                        max(len([c for c in contracts if c.strike_price > 0]), 1)
                    ),
                }
                for tech, contracts in by_tech.items()
            },
            "by_allocation_round": by_round,
            "totals": {
                "projects": len(all_contracts),
                "capacity_mw": sum(c.capacity_mw for c in all_contracts),
                "avg_strike_price": sum(strike_prices) / max(len(strike_prices), 1) if strike_prices else 0,
                "min_strike_price": min(strike_prices) if strike_prices else 0,
                "max_strike_price": max(strike_prices) if strike_prices else 0,
            },
        }

    def get_flexibility_opportunities(self) -> list[dict]:
        """
        Identify flexibility opportunities based on current grid state.

        Returns recommended actions for flexible loads.
        """
        snapshot = self.get_snapshot()
        opportunities = []

        # Low carbon opportunity
        if snapshot.carbon_index in ["very low", "low"]:
            opportunities.append({
                "type": "carbon_optimized",
                "action": "INCREASE_LOAD",
                "reason": f"Low carbon intensity ({snapshot.carbon_intensity} gCO2/kWh)",
                "confidence": 0.9 if snapshot.carbon_index == "very low" else 0.7,
            })

        # High wind = low wholesale price typically
        wind_mw = snapshot.generation_by_fuel.get("wind", 0)
        if wind_mw > 10000:
            opportunities.append({
                "type": "price_optimized",
                "action": "INCREASE_LOAD",
                "reason": f"High wind generation ({wind_mw:.0f} MW)",
                "confidence": 0.75,
            })

        # System tight (high gas)
        gas_mw = snapshot.generation_by_fuel.get("gas", 0)
        if gas_mw > 15000:
            opportunities.append({
                "type": "system_support",
                "action": "REDUCE_LOAD",
                "reason": f"High gas dependency ({gas_mw:.0f} MW)",
                "confidence": 0.65,
            })

        # Balancing opportunity
        if snapshot.total_bids_mw > 1000:
            opportunities.append({
                "type": "balancing_service",
                "action": "OFFER_DSR",
                "reason": f"High bid volume ({snapshot.total_bids_mw:.0f} MW)",
                "confidence": 0.6,
            })

        # Price opportunity
        if snapshot.agile_price_gbp and snapshot.agile_price_gbp < 5:
            opportunities.append({
                "type": "cost_saving",
                "action": "CHARGE_STORAGE",
                "reason": f"Very low Agile price ({snapshot.agile_price_gbp:.1f}p/kWh)",
                "confidence": 0.85,
            })

        return sorted(opportunities, key=lambda x: x["confidence"], reverse=True)

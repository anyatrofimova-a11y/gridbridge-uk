#!/usr/bin/env python3
"""
examples/ingest_real_data.py

Fetches real UK grid data from public APIs (no API keys required for basic access):
 - Carbon Intensity API (National Grid ESO) - demand forecasts, generation mix
 - Elexon Insights API (public subset) - system prices, generation by fuel
 - Met Office DataPoint (requires free registration) - weather for DLR

Writes canonical.parquet, runs pypsa snapshot, produces audit trace.

Usage:
  python examples/ingest_real_data.py --start 2025-01-15 --days 1
"""

import argparse
import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

import numpy as np
import pandas as pd
import requests

try:
    import pypsa
except ImportError:
    pypsa = None

# ============================================================================
# API ENDPOINTS - UK PUBLIC DATA SOURCES
# ============================================================================

CARBON_INTENSITY_BASE = "https://api.carbonintensity.org.uk"
ELEXON_INSIGHTS_BASE = "https://data.elexon.co.uk/bmrs/api/v1"
# Met Office DataPoint requires free API key from https://www.metoffice.gov.uk/services/data/datapoint
METOFFICE_BASE = "https://datapoint.metoffice.gov.uk/public/data"


class APIClient:
    """Simple rate-limited HTTP client with retries."""

    def __init__(self, base_url: str, rate_limit_delay: float = 0.5):
        self.base_url = base_url.rstrip("/")
        self.rate_limit_delay = rate_limit_delay
        self.session = requests.Session()
        self.session.headers.update({"Accept": "application/json"})

    def get(
        self, endpoint: str, params: Optional[dict] = None, retries: int = 3
    ) -> dict:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        for attempt in range(retries):
            try:
                time.sleep(self.rate_limit_delay)
                resp = self.session.get(url, params=params, timeout=30)
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as e:
                print(f"API request failed (attempt {attempt + 1}): {e}")
                if attempt == retries - 1:
                    raise
                time.sleep(2**attempt)
        return {}


# ============================================================================
# CARBON INTENSITY API - generation mix, demand, carbon intensity
# ============================================================================


def fetch_carbon_intensity_generation(start: datetime, end: datetime) -> pd.DataFrame:
    """
    Fetch half-hourly generation mix from Carbon Intensity API.

    Endpoint: /generation/{from}/{to}
    Returns: biomass, coal, imports, gas, nuclear, other, hydro, solar, wind

    Note: This is forecast/estimate data, not metered settlement data.
    For metered data, use Elexon BMRS (requires API key for full access).
    """
    client = APIClient(CARBON_INTENSITY_BASE)

    # API accepts ISO format, max 14 days per request
    from_str = start.strftime("%Y-%m-%dT%H:%MZ")
    to_str = end.strftime("%Y-%m-%dT%H:%MZ")

    print(f"Fetching Carbon Intensity generation mix: {from_str} to {to_str}")

    try:
        data = client.get(f"/generation/{from_str}/{to_str}")
    except Exception as e:
        print(f"Carbon Intensity API failed: {e}")
        return pd.DataFrame()

    if "data" not in data:
        print("No 'data' field in Carbon Intensity response")
        return pd.DataFrame()

    records = []
    for item in data["data"]:
        ts = pd.Timestamp(item["from"]).tz_convert("UTC")
        gen_mix = item.get("generationmix", [])
        row = {"timestamp": ts}
        for fuel in gen_mix:
            # API returns percentage; we'll keep as-is (can scale by demand later)
            row[f"{fuel['fuel']}_pct"] = fuel["perc"]
        records.append(row)

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.set_index("timestamp").sort_index()

    return df


def fetch_carbon_intensity_demand(start: datetime, end: datetime) -> pd.DataFrame:
    """
    Fetch national demand and carbon intensity.

    Endpoint: /intensity/{from}/{to}
    """
    client = APIClient(CARBON_INTENSITY_BASE)

    from_str = start.strftime("%Y-%m-%dT%H:%MZ")
    to_str = end.strftime("%Y-%m-%dT%H:%MZ")

    print(f"Fetching Carbon Intensity demand data: {from_str} to {to_str}")

    try:
        data = client.get(f"/intensity/{from_str}/{to_str}")
    except Exception as e:
        print(f"Carbon Intensity intensity endpoint failed: {e}")
        return pd.DataFrame()

    if "data" not in data:
        return pd.DataFrame()

    records = []
    for item in data["data"]:
        ts = pd.Timestamp(item["from"]).tz_convert("UTC")
        intensity = item.get("intensity", {})
        records.append(
            {
                "timestamp": ts,
                "carbon_intensity_forecast": intensity.get("forecast"),
                "carbon_intensity_actual": intensity.get("actual"),
                "carbon_intensity_index": intensity.get("index"),
            }
        )

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.set_index("timestamp").sort_index()

    return df


def fetch_carbon_intensity_regional(
    start: datetime, end: datetime, region_id: int = 13
) -> pd.DataFrame:
    """
    Fetch regional generation/demand data.

    Region IDs (DNO regions):
      1: North Scotland, 2: South Scotland, 3: North West England,
      4: North East England, 5: Yorkshire, 6: North Wales & Merseyside,
      7: South Wales, 8: West Midlands, 9: East Midlands, 10: Eastern,
      11: South West England, 12: South England, 13: London,
      14: South East England, 15: England, 16: Scotland, 17: GB
    """
    client = APIClient(CARBON_INTENSITY_BASE)

    from_str = start.strftime("%Y-%m-%dT%H:%MZ")
    to_str = end.strftime("%Y-%m-%dT%H:%MZ")

    print(f"Fetching regional data for region {region_id}")

    try:
        data = client.get(
            f"/regional/intensity/{from_str}/{to_str}/regionid/{region_id}"
        )
    except Exception as e:
        print(f"Regional endpoint failed: {e}")
        return pd.DataFrame()

    if "data" not in data or "data" not in data["data"]:
        return pd.DataFrame()

    records = []
    for item in data["data"]["data"]:
        ts = pd.Timestamp(item["from"]).tz_convert("UTC")
        intensity = item.get("intensity", {})
        gen_mix = item.get("generationmix", [])
        row = {
            "timestamp": ts,
            "region_id": region_id,
            "intensity_forecast": intensity.get("forecast"),
        }
        for fuel in gen_mix:
            row[f"{fuel['fuel']}_pct"] = fuel["perc"]
        records.append(row)

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.set_index("timestamp").sort_index()

    return df


# ============================================================================
# ELEXON INSIGHTS API - public subset (no key required for some endpoints)
# ============================================================================


def fetch_elexon_generation_by_fuel(settlement_date: str) -> pd.DataFrame:
    """
    Fetch actual generation by fuel type from Elexon Insights API.

    Endpoint: /datasets/FUELINST
    Note: Some Elexon endpoints require API key; this one has public access.

    settlement_date: YYYY-MM-DD format
    """
    client = APIClient(ELEXON_INSIGHTS_BASE, rate_limit_delay=1.0)

    print(f"Fetching Elexon FUELINST for {settlement_date}")

    try:
        # FUELINST provides 5-minute resolution instantaneous generation by fuel
        data = client.get(
            "/datasets/FUELINST",
            params={"settlementDate": settlement_date, "format": "json"},
        )
    except Exception as e:
        print(f"Elexon FUELINST failed: {e}")
        return pd.DataFrame()

    if not isinstance(data, list) and "data" in data:
        data = data["data"]

    if not data:
        print("No FUELINST data returned")
        return pd.DataFrame()

    records = []
    for item in data:
        # Parse settlement period to timestamp
        sp = item.get("settlementPeriod", 1)
        sd = item.get("settlementDate", settlement_date)
        # SP 1 = 00:00-00:30, SP 2 = 00:30-01:00, etc.
        ts = pd.Timestamp(sd, tz="Europe/London") + timedelta(minutes=30 * (sp - 1))
        ts = ts.tz_convert("UTC")

        records.append(
            {
                "timestamp": ts,
                "fuel_type": item.get("fuelType"),
                "generation_mw": item.get("generation"),
            }
        )

    df = pd.DataFrame(records)
    if df.empty:
        return df

    # Pivot to wide format
    df_pivot = df.pivot_table(
        index="timestamp", columns="fuel_type", values="generation_mw", aggfunc="mean"
    )

    return df_pivot


def fetch_elexon_demand(settlement_date: str) -> pd.DataFrame:
    """
    Fetch system demand from Elexon.

    Endpoint: /datasets/INDOD (Initial National Demand Outturn)
    """
    client = APIClient(ELEXON_INSIGHTS_BASE, rate_limit_delay=1.0)

    print(f"Fetching Elexon INDOD for {settlement_date}")

    try:
        data = client.get(
            "/datasets/INDOD",
            params={"settlementDate": settlement_date, "format": "json"},
        )
    except Exception as e:
        print(f"Elexon INDOD failed: {e}")
        return pd.DataFrame()

    if not isinstance(data, list) and "data" in data:
        data = data["data"]

    if not data:
        return pd.DataFrame()

    records = []
    for item in data:
        sp = item.get("settlementPeriod", 1)
        sd = item.get("settlementDate", settlement_date)
        ts = pd.Timestamp(sd, tz="Europe/London") + timedelta(minutes=30 * (sp - 1))
        ts = ts.tz_convert("UTC")

        records.append(
            {
                "timestamp": ts,
                "demand_mw": item.get("demand"),
            }
        )

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.set_index("timestamp").sort_index()

    return df


def fetch_elexon_system_prices(settlement_date: str) -> pd.DataFrame:
    """
    Fetch system buy/sell prices.

    Endpoint: /balancing/settlement/system-prices
    """
    client = APIClient(ELEXON_INSIGHTS_BASE, rate_limit_delay=1.0)

    print(f"Fetching Elexon system prices for {settlement_date}")

    try:
        data = client.get(
            "/balancing/settlement/system-prices",
            params={"settlementDate": settlement_date, "format": "json"},
        )
    except Exception as e:
        print(f"Elexon system prices failed: {e}")
        return pd.DataFrame()

    if not isinstance(data, list) and "data" in data:
        data = data["data"]

    if not data:
        return pd.DataFrame()

    records = []
    for item in data:
        sp = item.get("settlementPeriod", 1)
        sd = item.get("settlementDate", settlement_date)
        ts = pd.Timestamp(sd, tz="Europe/London") + timedelta(minutes=30 * (sp - 1))
        ts = ts.tz_convert("UTC")

        records.append(
            {
                "timestamp": ts,
                "system_sell_price": item.get("systemSellPrice"),
                "system_buy_price": item.get("systemBuyPrice"),
            }
        )

    df = pd.DataFrame(records)
    if not df.empty:
        df = df.set_index("timestamp").sort_index()

    return df


# ============================================================================
# DATA CANONICALISATION
# ============================================================================


def canonicalize_to_schema(
    carbon_gen: pd.DataFrame,
    carbon_intensity: pd.DataFrame,
    elexon_demand: pd.DataFrame,
    elexon_gen: pd.DataFrame,
    elexon_prices: pd.DataFrame,
) -> pd.DataFrame:
    """
    Merge all sources into canonical schema for GridBridge.

    Canonical columns:
      - timestamp (index, UTC)
      - demand_mw: National demand
      - wind_mw: Wind generation (estimated from % if MW not available)
      - solar_mw: Solar generation
      - gas_mw, nuclear_mw, coal_mw, hydro_mw, biomass_mw, imports_mw
      - carbon_intensity_gco2_kwh: Carbon intensity
      - system_price_gbp_mwh: System price (average of buy/sell)

    Resolution: 30-minute (GB settlement period standard)
    """
    # Start with demand as the base (most reliable)
    if not elexon_demand.empty:
        canonical = elexon_demand.copy()
    else:
        # If no Elexon demand, create empty frame
        canonical = pd.DataFrame()

    # Merge Elexon generation if available
    if not elexon_gen.empty:
        # Rename Elexon fuel columns to canonical names
        fuel_map = {
            "WIND": "wind_mw",
            "SOLAR": "solar_mw",
            "CCGT": "gas_mw",
            "OCGT": "gas_ocgt_mw",
            "NUCLEAR": "nuclear_mw",
            "COAL": "coal_mw",
            "HYDRO": "hydro_mw",
            "BIOMASS": "biomass_mw",
            "INTFR": "import_fr_mw",
            "INTIRL": "import_irl_mw",
            "INTNED": "import_ned_mw",
            "INTEW": "import_ew_mw",
            "INTNEM": "import_nem_mw",
            "INTNSL": "import_nsl_mw",
            "INTELEC": "import_elec_mw",
            "INTIFA2": "import_ifa2_mw",
            "INTVKL": "import_vkl_mw",
            "PS": "pumped_storage_mw",
            "NPSHYD": "hydro_non_ps_mw",
            "OTHER": "other_gen_mw",
            "OIL": "oil_mw",
        }
        elexon_gen_renamed = elexon_gen.rename(columns=fuel_map)

        # Aggregate imports
        import_cols = [c for c in elexon_gen_renamed.columns if c.startswith("import_")]
        if import_cols:
            elexon_gen_renamed["imports_mw"] = elexon_gen_renamed[import_cols].sum(
                axis=1
            )

        if canonical.empty:
            canonical = elexon_gen_renamed
        else:
            canonical = canonical.join(elexon_gen_renamed, how="outer")

    # If we have Carbon Intensity % data but no MW, estimate from demand
    if not carbon_gen.empty and "wind_mw" not in canonical.columns:
        # Carbon Intensity gives percentages; multiply by demand to get MW estimate
        if "demand_mw" in canonical.columns:
            for fuel in [
                "wind",
                "solar",
                "gas",
                "nuclear",
                "coal",
                "hydro",
                "biomass",
                "imports",
            ]:
                pct_col = f"{fuel}_pct"
                if pct_col in carbon_gen.columns:
                    # Join and calculate
                    canonical = canonical.join(carbon_gen[[pct_col]], how="left")
                    canonical[f"{fuel}_mw_est"] = (
                        canonical["demand_mw"] * canonical[pct_col] / 100
                    )
                    canonical = canonical.drop(columns=[pct_col], errors="ignore")

    # Add carbon intensity
    if not carbon_intensity.empty:
        canonical = canonical.join(
            carbon_intensity[["carbon_intensity_actual", "carbon_intensity_forecast"]],
            how="left",
        )
        # Prefer actual, fall back to forecast
        canonical["carbon_intensity_gco2_kwh"] = canonical[
            "carbon_intensity_actual"
        ].fillna(canonical["carbon_intensity_forecast"])

    # Add system prices
    if not elexon_prices.empty:
        canonical = canonical.join(elexon_prices, how="left")
        # Average of buy/sell as reference price
        if (
            "system_buy_price" in canonical.columns
            and "system_sell_price" in canonical.columns
        ):
            canonical["system_price_gbp_mwh"] = (
                canonical["system_buy_price"] + canonical["system_sell_price"]
            ) / 2

    # Clean up and ensure standard columns exist
    standard_cols = [
        "demand_mw",
        "wind_mw",
        "solar_mw",
        "gas_mw",
        "nuclear_mw",
        "coal_mw",
        "hydro_mw",
        "biomass_mw",
        "imports_mw",
        "carbon_intensity_gco2_kwh",
        "system_price_gbp_mwh",
    ]

    for col in standard_cols:
        if col not in canonical.columns:
            canonical[col] = np.nan

    # Reorder columns
    other_cols = [c for c in canonical.columns if c not in standard_cols]
    canonical = canonical[standard_cols + other_cols]

    # Remove duplicate timestamps
    canonical = canonical[~canonical.index.duplicated(keep="first")]
    canonical = canonical.sort_index()

    return canonical


# ============================================================================
# PYPSA NETWORK CONSTRUCTION
# ============================================================================


def build_gb_minimal_network(canonical_df: pd.DataFrame) -> "pypsa.Network":
    """
    Build a minimal but realistic GB network structure for demonstration.

    This is NOT a full transmission model-use pypsa-uk for that.
    This creates a simplified 5-zone aggregation suitable for testing
    the data pipeline and basic powerflow.

    Zones:
      - SCOT: Scotland (SPT + SSEN-T)
      - NORTH: North England
      - MIDL: Midlands
      - SOUTH: South England + Wales
      - LON: London/SE

    Interconnectors:
      - SCOT-NORTH: 3.3 GW (approximate)
      - NORTH-MIDL: 10 GW
      - MIDL-SOUTH: 10 GW
      - MIDL-LON: 5 GW
      - SOUTH-LON: 5 GW
    """
    if pypsa is None:
        raise ImportError("pypsa required for network construction")

    net = pypsa.Network()
    # PyPSA requires timezone-naive timestamps
    snapshots = (
        canonical_df.index.tz_localize(None)
        if canonical_df.index.tz
        else canonical_df.index
    )
    net.set_snapshots(snapshots)

    # Define zones
    zones = {
        "SCOT": {"v_nom": 400, "x": -4.0, "y": 56.0},
        "NORTH": {"v_nom": 400, "x": -1.5, "y": 54.0},
        "MIDL": {"v_nom": 400, "x": -1.5, "y": 52.5},
        "SOUTH": {"v_nom": 400, "x": -3.0, "y": 51.0},
        "LON": {"v_nom": 400, "x": 0.0, "y": 51.5},
    }

    for zone, params in zones.items():
        net.add("Bus", zone, **params)

    # Add transmission lines (simplified)
    lines = [
        ("SCOT", "NORTH", 3300, 0.01),  # Scotland-England boundary ~3.3GW
        ("NORTH", "MIDL", 10000, 0.005),
        ("MIDL", "SOUTH", 10000, 0.005),
        ("MIDL", "LON", 5000, 0.008),
        ("SOUTH", "LON", 5000, 0.008),
    ]

    for bus0, bus1, s_nom, x in lines:
        net.add(
            "Line",
            f"{bus0}-{bus1}",
            bus0=bus0,
            bus1=bus1,
            s_nom=s_nom,
            x=x,
            r=x * 0.1,  # Approximate R/X ratio
        )

    # Allocate generation by zone (rough approximation)
    # In reality, this would come from BMU location data
    gen_allocation = {
        "SCOT": {"wind": 0.35, "hydro": 0.8, "nuclear": 0.15},
        "NORTH": {"wind": 0.30, "gas": 0.25, "coal": 0.5, "nuclear": 0.35},
        "MIDL": {"gas": 0.35, "coal": 0.3, "biomass": 0.4},
        "SOUTH": {"nuclear": 0.35, "gas": 0.20, "solar": 0.4, "wind": 0.15},
        "LON": {"gas": 0.20, "solar": 0.2},
    }

    # Demand allocation (rough, based on population/industry)
    demand_allocation = {
        "SCOT": 0.08,
        "NORTH": 0.20,
        "MIDL": 0.25,
        "SOUTH": 0.22,
        "LON": 0.25,
    }

    # Add generators
    _fuel_types = [  # noqa: F841
        "wind",
        "solar",
        "gas",
        "nuclear",
        "coal",
        "hydro",
        "biomass",
    ]

    for zone, alloc in gen_allocation.items():
        for fuel, share in alloc.items():
            gen_name = f"{zone}_{fuel}"
            col = f"{fuel}_mw"

            if col in canonical_df.columns:
                p_max = canonical_df[col].max() * share
                if p_max > 0:
                    # Create time-varying availability
                    p_set = canonical_df[col] * share

                    net.add(
                        "Generator",
                        gen_name,
                        bus=zone,
                        p_nom=p_max * 1.1,  # 10% headroom
                        marginal_cost=_get_marginal_cost(fuel),
                        carrier=fuel,
                    )

                    # Set time series
                    net.generators_t.p_max_pu[gen_name] = (p_set / (p_max * 1.1)).clip(
                        0, 1
                    )

    # Add loads
    if "demand_mw" in canonical_df.columns:
        for zone, share in demand_allocation.items():
            load_name = f"{zone}_load"
            net.add("Load", load_name, bus=zone)
            net.loads_t.p_set[load_name] = canonical_df["demand_mw"] * share

    # Add slack generator (for powerflow feasibility)
    net.add(
        "Generator",
        "slack",
        bus="MIDL",
        p_nom=50000,
        marginal_cost=1000,
        control="Slack",
    )

    return net


def _get_marginal_cost(fuel: str) -> float:
    """Approximate marginal costs in GBP/MWh for merit order."""
    costs = {
        "nuclear": 10,
        "wind": 0,
        "solar": 0,
        "hydro": 5,
        "biomass": 50,
        "gas": 80,
        "coal": 100,
        "oil": 150,
    }
    return costs.get(fuel, 100)


# ============================================================================
# AUDIT TRACE
# ============================================================================


def compute_data_hash(df: pd.DataFrame) -> str:
    """Compute deterministic hash of dataframe for audit trail."""
    # Convert to CSV string for hashing (deterministic)
    csv_str = df.to_csv()
    return hashlib.sha256(csv_str.encode()).hexdigest()[:16]


def write_audit_trace(
    out_dir: Path,
    canonical_df: pd.DataFrame,
    metadata: dict,
    data_sources: dict,
) -> Path:
    """
    Write tamper-evident audit trace.

    For production: use append-only database with cryptographic chaining.
    """
    out_dir.mkdir(parents=True, exist_ok=True)

    trace = {
        "run_id": metadata.get(
            "run_id", f"r-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        ),
        "timestamp_utc": datetime.now(timezone.utc).isoformat() + "Z",
        "data_hash": compute_data_hash(canonical_df),
        "row_count": len(canonical_df),
        "time_range": {
            "start": str(canonical_df.index.min()) if not canonical_df.empty else None,
            "end": str(canonical_df.index.max()) if not canonical_df.empty else None,
        },
        "columns": list(canonical_df.columns),
        "data_sources": data_sources,
        "metadata": metadata,
        "quality_metrics": {
            "completeness": {
                col: float(1 - canonical_df[col].isna().mean())
                for col in canonical_df.columns
            },
            "demand_range_mw": [
                (
                    float(canonical_df["demand_mw"].min())
                    if "demand_mw" in canonical_df.columns
                    else None
                ),
                (
                    float(canonical_df["demand_mw"].max())
                    if "demand_mw" in canonical_df.columns
                    else None
                ),
            ],
        },
    }

    fn = out_dir / f"audit_{trace['run_id']}.json"
    with fn.open("w") as f:
        json.dump(trace, f, indent=2, default=str)

    print(f"Wrote audit trace: {fn}")
    return fn


# ============================================================================
# MAIN
# ============================================================================


def main(args):
    out_dir = Path(args.output).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    start = pd.Timestamp(args.start, tz="UTC")
    end = start + timedelta(days=int(args.days))

    print(f"Fetching UK grid data: {start} to {end}")
    print("=" * 60)

    data_sources = {}

    # Fetch Carbon Intensity data
    carbon_gen = fetch_carbon_intensity_generation(
        start.to_pydatetime(), end.to_pydatetime()
    )
    data_sources["carbon_intensity_generation"] = {
        "rows": len(carbon_gen),
        "source": CARBON_INTENSITY_BASE,
    }

    carbon_intensity = fetch_carbon_intensity_demand(
        start.to_pydatetime(), end.to_pydatetime()
    )
    data_sources["carbon_intensity"] = {
        "rows": len(carbon_intensity),
        "source": CARBON_INTENSITY_BASE,
    }

    # Fetch Elexon data (day by day due to API structure)
    elexon_demand_list = []
    elexon_gen_list = []
    elexon_prices_list = []

    current = start
    while current < end:
        date_str = current.strftime("%Y-%m-%d")

        demand = fetch_elexon_demand(date_str)
        if not demand.empty:
            elexon_demand_list.append(demand)

        gen = fetch_elexon_generation_by_fuel(date_str)
        if not gen.empty:
            elexon_gen_list.append(gen)

        prices = fetch_elexon_system_prices(date_str)
        if not prices.empty:
            elexon_prices_list.append(prices)

        current += timedelta(days=1)

    elexon_demand = (
        pd.concat(elexon_demand_list) if elexon_demand_list else pd.DataFrame()
    )
    elexon_gen = pd.concat(elexon_gen_list) if elexon_gen_list else pd.DataFrame()
    elexon_prices = (
        pd.concat(elexon_prices_list) if elexon_prices_list else pd.DataFrame()
    )

    data_sources["elexon_demand"] = {
        "rows": len(elexon_demand),
        "source": ELEXON_INSIGHTS_BASE,
    }
    data_sources["elexon_generation"] = {
        "rows": len(elexon_gen),
        "source": ELEXON_INSIGHTS_BASE,
    }
    data_sources["elexon_prices"] = {
        "rows": len(elexon_prices),
        "source": ELEXON_INSIGHTS_BASE,
    }

    print("=" * 60)
    print("Data fetch summary:")
    for source, info in data_sources.items():
        print(f"  {source}: {info['rows']} rows")

    # Canonicalise
    print("\nCanonicalising data...")
    canonical = canonicalize_to_schema(
        carbon_gen, carbon_intensity, elexon_demand, elexon_gen, elexon_prices
    )

    if canonical.empty:
        print("WARNING: No data fetched. Using synthetic fallback.")
        idx = pd.date_range(start, end - timedelta(minutes=30), freq="30min", tz="UTC")
        canonical = pd.DataFrame(
            {
                "demand_mw": 25000 + 5000 * np.sin(np.linspace(0, 4 * np.pi, len(idx))),
                "wind_mw": 5000
                + 3000 * np.sin(np.linspace(0.5, 4.5 * np.pi, len(idx))),
                "solar_mw": 2000
                * np.clip(np.sin(np.linspace(-1, 3 * np.pi, len(idx))), 0, 1),
                "gas_mw": 10000 + 2000 * np.random.randn(len(idx)),
                "nuclear_mw": np.full(len(idx), 5500),
            },
            index=idx,
        )
        for col in [
            "coal_mw",
            "hydro_mw",
            "biomass_mw",
            "imports_mw",
            "carbon_intensity_gco2_kwh",
            "system_price_gbp_mwh",
        ]:
            canonical[col] = np.nan

    # Write canonical parquet
    canonical_path = out_dir / "canonical.parquet"
    canonical.to_parquet(canonical_path)
    print(f"\nWrote canonical data: {canonical_path}")
    print(f"  Shape: {canonical.shape}")
    print(f"  Columns: {list(canonical.columns)}")

    # Build PyPSA network and run powerflow
    if pypsa is not None:
        print("\nBuilding PyPSA network...")
        net = build_gb_minimal_network(canonical)

        print(
            f"Network: {len(net.buses)} buses, {len(net.generators)} generators, {len(net.lines)} lines"
        )

        # Run LOPF on subset of snapshots (full day would be slow)
        snapshots = net.snapshots[: min(48, len(net.snapshots))]  # Max 1 day
        print(f"Running LOPF on {len(snapshots)} snapshots...")

        try:
            net.optimize(snapshots, solver_name="highs")
            print("LOPF completed successfully")
        except Exception as e:
            print(f"LOPF failed: {e}")
            print("Attempting simple powerflow...")
            try:
                net.pf(snapshots[:1])
                print("Powerflow completed for single snapshot")
            except Exception as e2:
                print(f"Powerflow also failed: {e2}")

        # Export network
        snapshot_path = out_dir / "pypsa_snapshot.nc"
        net.export_to_netcdf(snapshot_path)
        print(f"Wrote PyPSA network: {snapshot_path}")
    else:
        print("\nSkipping PyPSA (not installed)")

    # Write audit trace
    metadata = {
        "run_id": f"r-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}",
        "start": str(start),
        "end": str(end),
        "script": "ingest_real_data.py",
    }
    write_audit_trace(out_dir / "audit", canonical, metadata, data_sources)

    print("\n" + "=" * 60)
    print("COMPLETE. Outputs:")
    print(f"  {out_dir / 'canonical.parquet'}")
    if pypsa:
        print(f"  {out_dir / 'pypsa_snapshot.nc'}")
    print(f"  {out_dir / 'audit' / '*.json'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Ingest real UK grid data and run PyPSA demo"
    )
    parser.add_argument("--start", default="2025-01-15", help="Start date YYYY-MM-DD")
    parser.add_argument("--days", type=int, default=1, help="Number of days")
    parser.add_argument("--output", default="out", help="Output directory")
    args = parser.parse_args()
    main(args)

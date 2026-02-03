"""
GridBridge UK - FastAPI Backend
Serves grid data to the React UI dashboard.

Endpoints:
  GET /api/headroom          - System headroom and top GSPs
  GET /api/scenarios         - Scenario stress test results
  GET /api/queue             - Connection queue with attrition predictions
  GET /api/timeseries        - Time series data from canonical.parquet
  GET /api/generation        - Generation mix data
  GET /api/status            - API health check

Run:
  uvicorn api.main:app --reload --port 8000
"""

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional
import random

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import pandas as pd
import numpy as np

# ============================================================================
# Configuration
# ============================================================================

DATA_DIR = Path(__file__).parent.parent / "out"
CANONICAL_PATH = DATA_DIR / "canonical.parquet"

# ============================================================================
# FastAPI App
# ============================================================================

app = FastAPI(
    title="GridBridge UK API",
    description="AI-Accelerated Grid Connection Platform - Backend API",
    version="1.0.0",
)

# CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Data Models
# ============================================================================

class GSP(BaseModel):
    id: str
    name: str
    voltage: str
    region: str
    hidden_mw: float
    confidence: str
    firm_headroom_mw: float = 0
    probabilistic_headroom_mw: float = 0


class HeadroomResponse(BaseModel):
    total_p95: float
    hidden_mw: float
    total_firm: float
    timestamp: str
    top_gsps: list[GSP]


class QueueProject(BaseModel):
    id: str
    name: str
    request_mw: float
    developer: str
    state: str
    prob: float
    gsp: str
    months_in_queue: int


class ScenarioResult(BaseModel):
    total: int
    p10: float
    p50: float
    p90: float
    p99: float
    max_curtailment: float
    distribution: list[dict]
    binding_constraints: list[dict]


class TimeseriesPoint(BaseModel):
    timestamp: str
    demand_mw: Optional[float]
    wind_mw: Optional[float]
    solar_mw: Optional[float]
    gas_mw: Optional[float]
    nuclear_mw: Optional[float]
    carbon_intensity: Optional[float]


# ============================================================================
# Data Loading
# ============================================================================

def load_canonical() -> pd.DataFrame:
    """Load canonical timeseries data."""
    if not CANONICAL_PATH.exists():
        return pd.DataFrame()
    try:
        df = pd.read_parquet(CANONICAL_PATH)
        return df
    except Exception as e:
        print(f"Error loading canonical data: {e}")
        return pd.DataFrame()


def get_mock_gsps() -> list[GSP]:
    """Generate mock GSP data with hidden capacity estimates."""
    gsps = [
        GSP(
            id="didcot-400",
            name="Didcot 400kV GSP",
            voltage="400kV",
            region="South",
            hidden_mw=45,
            confidence="HIGH",
            firm_headroom_mw=120,
            probabilistic_headroom_mw=165,
        ),
        GSP(
            id="burwell-132",
            name="Burwell 132kV BSP",
            voltage="132kV",
            region="East",
            hidden_mw=37,
            confidence="MEDIUM",
            firm_headroom_mw=85,
            probabilistic_headroom_mw=122,
        ),
        GSP(
            id="manchester-bsp",
            name="Manchester BSP",
            voltage="132kV",
            region="North",
            hidden_mw=28,
            confidence="MEDIUM",
            firm_headroom_mw=60,
            probabilistic_headroom_mw=88,
        ),
        GSP(
            id="edinburgh-275",
            name="Edinburgh 275kV GSP",
            voltage="275kV",
            region="Scotland",
            hidden_mw=52,
            confidence="HIGH",
            firm_headroom_mw=95,
            probabilistic_headroom_mw=147,
        ),
        GSP(
            id="bristol-132",
            name="Bristol Avonmouth BSP",
            voltage="132kV",
            region="South West",
            hidden_mw=18,
            confidence="LOW",
            firm_headroom_mw=45,
            probabilistic_headroom_mw=63,
        ),
        GSP(
            id="cambridge-132",
            name="Cambridge 132kV BSP",
            voltage="132kV",
            region="East",
            hidden_mw=41,
            confidence="HIGH",
            firm_headroom_mw=70,
            probabilistic_headroom_mw=111,
        ),
        GSP(
            id="cardiff-275",
            name="Cardiff East 275kV",
            voltage="275kV",
            region="Wales",
            hidden_mw=33,
            confidence="MEDIUM",
            firm_headroom_mw=80,
            probabilistic_headroom_mw=113,
        ),
        GSP(
            id="london-400",
            name="West London 400kV",
            voltage="400kV",
            region="London",
            hidden_mw=12,
            confidence="LOW",
            firm_headroom_mw=25,
            probabilistic_headroom_mw=37,
        ),
    ]
    return gsps


def get_mock_queue() -> list[QueueProject]:
    """Generate mock connection queue data."""
    projects = [
        QueueProject(
            id="q001",
            name="Hypothetical Solar Farm",
            request_mw=50,
            developer="Acme Renewables",
            state="pre-application",
            prob=0.35,
            gsp="Didcot 400kV",
            months_in_queue=6,
        ),
        QueueProject(
            id="q002",
            name="AI Campus Cambridge",
            request_mw=150,
            developer="DeepCompute Ltd",
            state="connection offer",
            prob=0.78,
            gsp="Cambridge 132kV",
            months_in_queue=14,
        ),
        QueueProject(
            id="q003",
            name="GridScale Storage",
            request_mw=100,
            developer="BatteryCo UK",
            state="agreement signed",
            prob=0.92,
            gsp="Bristol Avonmouth",
            months_in_queue=24,
        ),
        QueueProject(
            id="q004",
            name="Manchester Data Hub",
            request_mw=200,
            developer="CloudNorth",
            state="pre-application",
            prob=0.45,
            gsp="Manchester BSP",
            months_in_queue=3,
        ),
        QueueProject(
            id="q005",
            name="Scottish Wind Extension",
            request_mw=80,
            developer="Highland Wind Ltd",
            state="connection offer",
            prob=0.65,
            gsp="Edinburgh 275kV",
            months_in_queue=18,
        ),
        QueueProject(
            id="q006",
            name="London Edge DC",
            request_mw=75,
            developer="MetroCompute",
            state="application submitted",
            prob=0.55,
            gsp="West London 400kV",
            months_in_queue=8,
        ),
        QueueProject(
            id="q007",
            name="Wales Green Hydrogen",
            request_mw=120,
            developer="H2Wales",
            state="pre-application",
            prob=0.28,
            gsp="Cardiff East 275kV",
            months_in_queue=2,
        ),
        QueueProject(
            id="q008",
            name="East Anglia BESS",
            request_mw=60,
            developer="StorageFirst",
            state="agreement signed",
            prob=0.88,
            gsp="Burwell 132kV",
            months_in_queue=30,
        ),
    ]
    return projects


# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/api/status")
async def status():
    """Health check endpoint."""
    canonical_exists = CANONICAL_PATH.exists()
    df = load_canonical()
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data_available": canonical_exists,
        "data_rows": len(df) if not df.empty else 0,
        "data_path": str(CANONICAL_PATH),
    }


@app.get("/api/headroom", response_model=HeadroomResponse)
async def get_headroom(
    substation: str = Query("all", description="Substation ID or 'all'"),
    region: Optional[str] = Query(None, description="Filter by region"),
):
    """
    Get system headroom snapshot.

    Returns total probabilistic headroom, hidden capacity estimates,
    and top candidate GSPs for new connections.
    """
    gsps = get_mock_gsps()

    # Filter by region if specified
    if region:
        gsps = [g for g in gsps if g.region.lower() == region.lower()]

    # Filter by specific substation
    if substation != "all":
        gsps = [g for g in gsps if g.id == substation or substation.lower() in g.name.lower()]

    # Calculate totals
    total_hidden = sum(g.hidden_mw for g in gsps)
    total_p95 = sum(g.probabilistic_headroom_mw for g in gsps)
    total_firm = sum(g.firm_headroom_mw for g in gsps)

    # Sort by hidden capacity
    gsps_sorted = sorted(gsps, key=lambda g: g.hidden_mw, reverse=True)

    return HeadroomResponse(
        total_p95=round(total_p95, 1),
        hidden_mw=round(total_hidden, 1),
        total_firm=round(total_firm, 1),
        timestamp=datetime.now(timezone.utc).isoformat(),
        top_gsps=gsps_sorted[:6],
    )


@app.get("/api/scenarios", response_model=ScenarioResult)
async def get_scenarios(
    site: str = Query("demo", description="Site ID for scenario analysis"),
    scenarios: int = Query(10000, description="Number of scenarios to simulate"),
):
    """
    Get scenario stress test results for a site.

    Returns curtailment distribution across simulated scenarios
    and binding constraint analysis.
    """
    # Simulate curtailment distribution (would be from actual PyPSA runs)
    np.random.seed(hash(site) % 2**32)

    # Generate realistic curtailment distribution (lognormal-ish)
    base_curtailment = np.random.exponential(scale=15, size=scenarios)
    curtailments = np.clip(base_curtailment, 0, 150)

    # Calculate percentiles
    p10 = float(np.percentile(curtailments, 10))
    p50 = float(np.percentile(curtailments, 50))
    p90 = float(np.percentile(curtailments, 90))
    p99 = float(np.percentile(curtailments, 99))
    max_curt = float(np.max(curtailments))

    # Create distribution buckets
    hist, edges = np.histogram(curtailments, bins=10)
    distribution = [
        {"bucket": f"{int(edges[i])}-{int(edges[i+1])} MW", "count": int(hist[i])}
        for i in range(len(hist))
    ]

    # Mock binding constraints
    binding_constraints = [
        {"constraint": "Burwell-Cambridge 132kV", "frequency": 0.67, "severity": "HIGH"},
        {"constraint": "Eaton Socon SGT", "frequency": 0.23, "severity": "MEDIUM"},
        {"constraint": "Voltage at Cambridge BSP", "frequency": 0.10, "severity": "LOW"},
    ]

    return ScenarioResult(
        total=scenarios,
        p10=round(p10, 1),
        p50=round(p50, 1),
        p90=round(p90, 1),
        p99=round(p99, 1),
        max_curtailment=round(max_curt, 1),
        distribution=distribution,
        binding_constraints=binding_constraints,
    )


@app.get("/api/queue")
async def get_queue(
    state: Optional[str] = Query(None, description="Filter by state"),
    min_mw: Optional[float] = Query(None, description="Minimum MW"),
    max_mw: Optional[float] = Query(None, description="Maximum MW"),
):
    """
    Get connection queue with attrition predictions.

    Returns projects in the queue with completion probability
    estimates from the ML attrition model.
    """
    projects = get_mock_queue()

    # Apply filters
    if state:
        projects = [p for p in projects if state.lower() in p.state.lower()]
    if min_mw is not None:
        projects = [p for p in projects if p.request_mw >= min_mw]
    if max_mw is not None:
        projects = [p for p in projects if p.request_mw <= max_mw]

    # Sort by probability (highest first)
    projects_sorted = sorted(projects, key=lambda p: p.prob, reverse=True)

    # Calculate summary stats
    total_mw = sum(p.request_mw for p in projects)
    expected_mw = sum(p.request_mw * p.prob for p in projects)
    avg_prob = sum(p.prob for p in projects) / len(projects) if projects else 0

    return {
        "projects": [p.model_dump() for p in projects_sorted],
        "summary": {
            "total_projects": len(projects),
            "total_requested_mw": total_mw,
            "expected_completion_mw": round(expected_mw, 1),
            "average_completion_prob": round(avg_prob, 2),
            "phantom_load_mw": round(total_mw - expected_mw, 1),
        }
    }


@app.get("/api/timeseries")
async def get_timeseries(
    start: Optional[str] = Query(None, description="Start timestamp ISO format"),
    end: Optional[str] = Query(None, description="End timestamp ISO format"),
    columns: Optional[str] = Query(None, description="Comma-separated column names"),
):
    """
    Get time series data from canonical.parquet.

    Returns grid data including demand, generation by fuel,
    and carbon intensity.
    """
    df = load_canonical()

    if df.empty:
        raise HTTPException(status_code=404, detail="No canonical data available. Run ingestion first.")

    # Filter by time range
    if start:
        start_ts = pd.Timestamp(start)
        df = df[df.index >= start_ts]
    if end:
        end_ts = pd.Timestamp(end)
        df = df[df.index <= end_ts]

    # Select columns
    if columns:
        cols = [c.strip() for c in columns.split(",")]
        available = [c for c in cols if c in df.columns]
        if available:
            df = df[available]

    # Convert to records
    df_reset = df.reset_index()
    df_reset.columns = ["timestamp" if c == df_reset.columns[0] else c for c in df_reset.columns]

    # Convert timestamps to ISO format
    if "timestamp" in df_reset.columns:
        df_reset["timestamp"] = df_reset["timestamp"].astype(str)

    # Replace NaN with None for JSON
    records = df_reset.replace({np.nan: None}).to_dict(orient="records")

    return {
        "data": records,
        "meta": {
            "rows": len(records),
            "columns": list(df.columns),
            "time_range": {
                "start": str(df.index.min()) if not df.empty else None,
                "end": str(df.index.max()) if not df.empty else None,
            }
        }
    }


@app.get("/api/generation")
async def get_generation():
    """
    Get current generation mix summary.

    Returns latest generation by fuel type from ingested data.
    """
    df = load_canonical()

    if df.empty:
        # Return mock data if no real data
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "generation": {
                "wind_mw": 15200,
                "gas_mw": 9500,
                "nuclear_mw": 4025,
                "solar_mw": 1200,
                "biomass_mw": 2100,
                "hydro_mw": 450,
                "imports_mw": 2800,
            },
            "total_mw": 35275,
            "carbon_intensity": 185,
            "source": "mock",
        }

    # Get latest row
    latest = df.iloc[-1]

    gen_cols = ["wind_mw", "gas_mw", "nuclear_mw", "solar_mw", "biomass_mw", "hydro_mw", "imports_mw"]
    generation = {}
    total = 0

    for col in gen_cols:
        if col in latest.index and pd.notna(latest[col]):
            val = float(latest[col])
            generation[col] = round(val, 1)
            total += val

    carbon = None
    if "carbon_intensity_gco2_kwh" in latest.index and pd.notna(latest["carbon_intensity_gco2_kwh"]):
        carbon = float(latest["carbon_intensity_gco2_kwh"])

    return {
        "timestamp": str(df.index[-1]),
        "generation": generation,
        "total_mw": round(total, 1),
        "carbon_intensity": round(carbon, 1) if carbon else None,
        "source": "canonical.parquet",
    }


@app.get("/api/flexibility")
async def get_flexibility(
    site: str = Query("demo", description="Site ID"),
    firm_mw: float = Query(50, description="Requested firm capacity"),
    flex_mw: float = Query(100, description="Requested flexible capacity"),
    bess_mwh: float = Query(50, description="On-site BESS capacity"),
):
    """
    Calculate FlexConnect options for a site.

    Returns available connection tiers, expected curtailment,
    and estimated time-to-power.
    """
    # Simple model: more BESS = less curtailment
    base_curtailment = 0.08  # 8% baseline
    bess_reduction = min(bess_mwh / 200, 0.06)  # Up to 6% reduction
    flex_ratio = flex_mw / (firm_mw + flex_mw + 0.001)

    expected_curtailment = base_curtailment - bess_reduction

    # Determine tier
    if expected_curtailment < 0.02:
        tier = "TIER 1: NEAR-FIRM"
        tier_desc = "Mission-critical with backup"
        months = 12
    elif expected_curtailment < 0.10:
        tier = "TIER 2: FLEXIBLE"
        tier_desc = "Workload-shiftable compute"
        months = 9
    else:
        tier = "TIER 3: INTERRUPTIBLE"
        tier_desc = "Training runs, batch processing"
        months = 6

    # Calculate effective capacity
    effective_mw = firm_mw + (flex_mw * (1 - expected_curtailment))

    return {
        "site": site,
        "request": {
            "firm_mw": firm_mw,
            "flex_mw": flex_mw,
            "bess_mwh": bess_mwh,
        },
        "result": {
            "tier": tier,
            "tier_description": tier_desc,
            "expected_curtailment_pct": round(expected_curtailment * 100, 2),
            "effective_capacity_mw": round(effective_mw, 1),
            "estimated_months_to_power": months,
            "traditional_months": 72,  # 6 years baseline
            "time_saved_months": 72 - months,
        },
        "recommendations": [
            f"BESS sizing adequate for {round(bess_mwh / flex_mw * 60, 0)} minutes of backup" if flex_mw > 0 else "Consider adding BESS",
            "Consider gas peaker for Capacity Market revenue" if flex_mw > 50 else None,
            "DSR contract recommended for Tier 2/3" if expected_curtailment > 0.02 else None,
        ],
    }


@app.get("/api/dno-performance")
async def get_dno_performance():
    """
    Get comparative DNO performance metrics.

    Returns metrics for regulator dashboard including
    queue velocity and MW accelerated by DNO.
    """
    dnos = [
        {
            "dno": "UKPN",
            "region": "East/SE/London",
            "mw_accelerated": 185,
            "queue_velocity_change": -22,
            "avg_time_to_offer_days": 95,
            "flex_connections_pct": 34,
        },
        {
            "dno": "WPD/NGED",
            "region": "Midlands/SW/Wales",
            "mw_accelerated": 142,
            "queue_velocity_change": -18,
            "avg_time_to_offer_days": 110,
            "flex_connections_pct": 28,
        },
        {
            "dno": "SSEN",
            "region": "Scotland/South",
            "mw_accelerated": 98,
            "queue_velocity_change": -15,
            "avg_time_to_offer_days": 125,
            "flex_connections_pct": 22,
        },
        {
            "dno": "NPG",
            "region": "North East/Yorkshire",
            "mw_accelerated": 67,
            "queue_velocity_change": -12,
            "avg_time_to_offer_days": 140,
            "flex_connections_pct": 18,
        },
        {
            "dno": "ENW",
            "region": "North West",
            "mw_accelerated": 45,
            "queue_velocity_change": -8,
            "avg_time_to_offer_days": 155,
            "flex_connections_pct": 15,
        },
    ]

    total_mw = sum(d["mw_accelerated"] for d in dnos)
    avg_velocity = sum(d["queue_velocity_change"] for d in dnos) / len(dnos)

    return {
        "dnos": dnos,
        "summary": {
            "total_mw_accelerated": total_mw,
            "avg_queue_velocity_change": round(avg_velocity, 1),
            "total_dnos": len(dnos),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# Run with: uvicorn api.main:app --reload --port 8000
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

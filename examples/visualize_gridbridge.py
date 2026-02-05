#!/usr/bin/env python3
"""
examples/visualize_gridbridge.py

Generate visualizations for GridBridge UK platform:
1. System architecture diagram
2. Data flow diagram
3. Grid data time series
4. PyPSA network topology
5. Data source coverage matrix

Usage:
    python examples/visualize_gridbridge.py --output out/figures
"""

import argparse
from pathlib import Path

import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.lines import Line2D
from matplotlib.patches import Circle, FancyBboxPatch

# Set style
plt.style.use("seaborn-v0_8-whitegrid")
plt.rcParams["figure.facecolor"] = "white"
plt.rcParams["axes.facecolor"] = "white"
plt.rcParams["font.family"] = "sans-serif"
plt.rcParams["font.size"] = 10


def create_architecture_diagram(output_path: Path):
    """Create system architecture diagram."""
    fig, ax = plt.subplots(1, 1, figsize=(16, 12))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    ax.set_title(
        "GridBridge UK - System Architecture", fontsize=18, fontweight="bold", pad=20
    )

    # Colors
    colors = {
        "ingest": "#3498db",  # Blue
        "model": "#2ecc71",  # Green
        "ai": "#9b59b6",  # Purple
        "optimize": "#e74c3c",  # Red
        "regulatory": "#f39c12",  # Orange
        "ui": "#1abc9c",  # Teal
        "data": "#95a5a6",  # Gray
    }

    def draw_box(x, y, w, h, label, color, sublabel=None):
        box = FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.02,rounding_size=0.5",
            facecolor=color,
            edgecolor="white",
            linewidth=2,
            alpha=0.9,
        )
        ax.add_patch(box)
        ax.text(
            x + w / 2,
            y + h / 2 + (1.5 if sublabel else 0),
            label,
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold",
            color="white",
        )
        if sublabel:
            ax.text(
                x + w / 2,
                y + h / 2 - 1.5,
                sublabel,
                ha="center",
                va="center",
                fontsize=8,
                color="white",
                alpha=0.9,
            )

    def draw_arrow(x1, y1, x2, y2, color="#333"):
        ax.annotate(
            "",
            xy=(x2, y2),
            xytext=(x1, y1),
            arrowprops=dict(arrowstyle="->", color=color, lw=1.5),
        )

    # Title box
    ax.text(
        50,
        97,
        "GRIDBRIDGE UK PLATFORM",
        ha="center",
        va="center",
        fontsize=16,
        fontweight="bold",
        color="#2c3e50",
    )
    ax.text(
        50,
        94,
        "AI-Powered Grid Connection Acceleration",
        ha="center",
        va="center",
        fontsize=10,
        color="#7f8c8d",
        style="italic",
    )

    # Layer 1: Data Sources (top)
    y_data = 82
    data_sources = [
        ("ESO/NESO\nData Portal", 8),
        ("Elexon\nBMRS", 24),
        ("DNO Capacity\nMaps", 40),
        ("Met Office\nWeather", 56),
        ("TEC\nRegister", 72),
        ("Outage\nSchedules", 88),
    ]
    for label, x in data_sources:
        draw_box(x - 6, y_data, 12, 8, label, colors["data"])

    ax.text(
        2,
        y_data + 4,
        "DATA\nSOURCES",
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold",
        color="#7f8c8d",
    )

    # Layer 2: Ingest Layer
    y_ingest = 68
    draw_box(
        15,
        y_ingest,
        70,
        8,
        "DATA INGESTION LAYER",
        colors["ingest"],
        "Schema Validation → Temporal Alignment → Spatial Mapping → Quality Flags",
    )

    # Arrows from data sources to ingest
    for _, x in data_sources:
        draw_arrow(x, y_data, x, y_ingest + 8, "#3498db")

    # Layer 3: Core Processing (three boxes)
    y_core = 50
    draw_box(
        10,
        y_core,
        24,
        12,
        "GRID MODEL\nLAYER",
        colors["model"],
        "AC Power Flow\nN-1/N-2 Analysis",
    )
    draw_box(
        38, y_core, 24, 12, "AI/ML\nENGINE", colors["ai"], "Forecasting\nScenario Gen"
    )
    draw_box(
        66,
        y_core,
        24,
        12,
        "OPTIMISATION\nENGINE",
        colors["optimize"],
        "MILP/Convex\nPareto Ranking",
    )

    # Arrows between core layers
    draw_arrow(34, y_core + 6, 38, y_core + 6, "#333")
    draw_arrow(62, y_core + 6, 66, y_core + 6, "#333")

    # Arrow from ingest to core
    draw_arrow(50, y_ingest, 50, y_core + 12, "#333")

    # Layer 4: Regulatory Layer
    y_reg = 36
    draw_box(
        15,
        y_reg,
        70,
        8,
        "REGULATORY CONSTRAINTS LAYER",
        colors["regulatory"],
        "Grid Code • SQSS • Distribution Code • Ofgem Licence Conditions",
    )

    # Arrow from core to regulatory
    draw_arrow(50, y_core, 50, y_reg + 8, "#333")

    # Layer 5: User Interfaces
    y_ui = 18
    draw_box(
        8,
        y_ui,
        25,
        12,
        "DEVELOPER\nPORTAL",
        colors["ui"],
        "Site Search\nConnection Options",
    )
    draw_box(
        37,
        y_ui,
        26,
        12,
        "NETWORK\nOPERATOR PORTAL",
        colors["ui"],
        "Queue Analytics\nFlexibility Mgmt",
    )
    draw_box(
        67,
        y_ui,
        25,
        12,
        "REGULATOR\nDASHBOARD",
        colors["ui"],
        "Capacity Metrics\nAudit Trail",
    )

    # Arrows from regulatory to UIs
    draw_arrow(30, y_reg, 20, y_ui + 12, "#333")
    draw_arrow(50, y_reg, 50, y_ui + 12, "#333")
    draw_arrow(70, y_reg, 80, y_ui + 12, "#333")

    # Legend
    legend_elements = [
        mpatches.Patch(facecolor=colors["data"], label="Data Sources"),
        mpatches.Patch(facecolor=colors["ingest"], label="Ingestion"),
        mpatches.Patch(facecolor=colors["model"], label="Physics Model"),
        mpatches.Patch(facecolor=colors["ai"], label="AI/ML"),
        mpatches.Patch(facecolor=colors["optimize"], label="Optimisation"),
        mpatches.Patch(facecolor=colors["regulatory"], label="Regulatory"),
        mpatches.Patch(facecolor=colors["ui"], label="User Interface"),
    ]
    ax.legend(handles=legend_elements, loc="lower right", ncol=4, fontsize=9)

    # Footer
    ax.text(
        50,
        2,
        "GridBridge UK © 2026 | Accelerating Grid Connections for AI Data Centres",
        ha="center",
        va="center",
        fontsize=9,
        color="#95a5a6",
    )

    plt.tight_layout()
    plt.savefig(
        output_path / "architecture_diagram.png",
        dpi=150,
        bbox_inches="tight",
        facecolor="white",
        edgecolor="none",
    )
    plt.close()
    print(f"Saved: {output_path / 'architecture_diagram.png'}")


def create_data_flow_diagram(output_path: Path):
    """Create data flow diagram showing the ingestion pipeline."""
    fig, ax = plt.subplots(1, 1, figsize=(14, 10))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    ax.set_title(
        "GridBridge UK - Data Flow & API Integration",
        fontsize=16,
        fontweight="bold",
        pad=20,
    )

    # API Sources (left side)
    apis = [
        (
            "Carbon Intensity API",
            "api.carbonintensity.org.uk",
            "30min",
            "FREE",
            "#27ae60",
        ),
        (
            "Elexon BMRS (Legacy)",
            "api.bmreports.com",
            "5min-30min",
            "API KEY",
            "#3498db",
        ),
        ("Elexon Insights", "data.elexon.co.uk", "30min", "FREE*", "#3498db"),
        ("ESO Data Portal", "data.nationalgrideso.com", "varies", "FREE", "#9b59b6"),
        (
            "Met Office DataPoint",
            "datapoint.metoffice.gov.uk",
            "1hr",
            "API KEY",
            "#e67e22",
        ),
        ("DNO Capacity Maps", "various DNO portals", "quarterly", "PUBLIC", "#95a5a6"),
    ]

    y_start = 85
    y_step = 12

    for i, (name, url, res, auth, color) in enumerate(apis):
        y = y_start - i * y_step
        # API box
        box = FancyBboxPatch(
            (2, y - 4),
            35,
            8,
            boxstyle="round,pad=0.02",
            facecolor=color,
            edgecolor="white",
            linewidth=2,
            alpha=0.85,
        )
        ax.add_patch(box)
        ax.text(
            19.5,
            y + 1,
            name,
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
            color="white",
        )
        ax.text(
            19.5,
            y - 2,
            url,
            ha="center",
            va="center",
            fontsize=7,
            color="white",
            alpha=0.9,
        )

        # Resolution & Auth badges
        ax.text(
            39,
            y + 1.5,
            res,
            ha="left",
            va="center",
            fontsize=8,
            bbox=dict(boxstyle="round", facecolor="#ecf0f1", edgecolor="none", pad=0.3),
        )
        ax.text(39, y - 1.5, auth, ha="left", va="center", fontsize=7, color="#7f8c8d")

        # Arrow to processing
        ax.annotate(
            "",
            xy=(52, 50),
            xytext=(37, y),
            arrowprops=dict(
                arrowstyle="->", color="#bdc3c7", lw=1, connectionstyle="arc3,rad=0.1"
            ),
        )

    # Central Processing Box
    proc_box = FancyBboxPatch(
        (52, 35),
        20,
        30,
        boxstyle="round,pad=0.02",
        facecolor="#2c3e50",
        edgecolor="#34495e",
        linewidth=3,
    )
    ax.add_patch(proc_box)
    ax.text(
        62,
        58,
        "INGEST",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        color="white",
    )
    ax.text(
        62, 54, "& CANONICALISE", ha="center", va="center", fontsize=9, color="#bdc3c7"
    )

    # Processing steps
    steps = [
        "Fetch API",
        "Parse Response",
        "Validate Schema",
        "Align Time",
        "Quality Check",
        "Merge Sources",
    ]
    for i, step in enumerate(steps):
        ax.text(
            62,
            49 - i * 3,
            f"→ {step}",
            ha="center",
            va="center",
            fontsize=8,
            color="#ecf0f1",
        )

    # Output files (right side)
    outputs = [
        ("canonical.parquet", "Unified timeseries\n30-min settlement", "#27ae60"),
        ("pypsa_snapshot.nc", "Network model\n+ power flow results", "#3498db"),
        ("audit/*.json", "Audit trail\nw/ data hashes", "#e74c3c"),
    ]

    y_out = 65
    for i, (name, desc, color) in enumerate(outputs):
        y = y_out - i * 18
        box = FancyBboxPatch(
            (77, y - 5),
            20,
            10,
            boxstyle="round,pad=0.02",
            facecolor=color,
            edgecolor="white",
            linewidth=2,
            alpha=0.9,
        )
        ax.add_patch(box)
        ax.text(
            87,
            y + 2,
            name,
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
            color="white",
        )
        ax.text(
            87,
            y - 2,
            desc,
            ha="center",
            va="center",
            fontsize=7,
            color="white",
            alpha=0.9,
        )

        # Arrow from processing
        ax.annotate(
            "",
            xy=(77, y),
            xytext=(72, 50),
            arrowprops=dict(arrowstyle="->", color=color, lw=2),
        )

    # BMRS Report codes reference
    ax.text(
        50,
        8,
        "BMRS Report Codes: ROLSYSDEM (demand) | FUELHH (generation) | FREQ (frequency) | B1770/B1780 (prices)",
        ha="center",
        va="center",
        fontsize=8,
        color="#7f8c8d",
        bbox=dict(boxstyle="round", facecolor="#f8f9fa", edgecolor="#dee2e6", pad=0.5),
    )

    ax.text(
        50,
        3,
        "Data Sources: Elexon BMRS © Elexon Limited | Carbon Intensity API © National Grid ESO",
        ha="center",
        va="center",
        fontsize=7,
        color="#adb5bd",
    )

    plt.tight_layout()
    plt.savefig(
        output_path / "data_flow_diagram.png",
        dpi=150,
        bbox_inches="tight",
        facecolor="white",
        edgecolor="none",
    )
    plt.close()
    print(f"Saved: {output_path / 'data_flow_diagram.png'}")


def create_timeseries_plot(canonical_path: Path, output_path: Path):
    """Create time series visualization of ingested grid data."""
    if not canonical_path.exists():
        print(f"Skipping timeseries plot: {canonical_path} not found")
        return

    df = pd.read_parquet(canonical_path)

    fig, axes = plt.subplots(3, 1, figsize=(14, 10), sharex=True)
    fig.suptitle(
        "GridBridge UK - GB Grid Data (Real-time Ingestion)",
        fontsize=14,
        fontweight="bold",
    )

    # Plot 1: Generation Mix
    ax1 = axes[0]
    gen_cols = ["wind_mw", "gas_mw", "nuclear_mw", "biomass_mw", "solar_mw"]
    available_cols = [c for c in gen_cols if c in df.columns and df[c].notna().any()]

    if available_cols:
        colors_gen = ["#3498db", "#e74c3c", "#9b59b6", "#27ae60", "#f1c40f"]
        df_plot = df[available_cols].fillna(0) / 1000  # Convert to GW
        ax1.stackplot(
            df_plot.index,
            df_plot.T,
            labels=[c.replace("_mw", "").upper() for c in available_cols],
            colors=colors_gen[: len(available_cols)],
            alpha=0.8,
        )
        ax1.set_ylabel("Generation (GW)", fontsize=10)
        ax1.legend(loc="upper left", ncol=5, fontsize=8)
        ax1.set_title("Generation Mix by Fuel Type", fontsize=11, fontweight="bold")
        ax1.set_ylim(bottom=0)

    # Plot 2: Individual generation traces
    ax2 = axes[1]
    if "wind_mw" in df.columns:
        ax2.plot(
            df.index, df["wind_mw"] / 1000, label="Wind", color="#3498db", linewidth=1.5
        )
    if "gas_mw" in df.columns:
        ax2.plot(
            df.index,
            df["gas_mw"] / 1000,
            label="Gas (CCGT)",
            color="#e74c3c",
            linewidth=1.5,
        )
    if "nuclear_mw" in df.columns:
        ax2.plot(
            df.index,
            df["nuclear_mw"] / 1000,
            label="Nuclear",
            color="#9b59b6",
            linewidth=1.5,
        )
    ax2.set_ylabel("Generation (GW)", fontsize=10)
    ax2.legend(loc="upper right", ncol=3, fontsize=8)
    ax2.set_title("Major Generation Sources", fontsize=11, fontweight="bold")
    ax2.grid(True, alpha=0.3)

    # Plot 3: Carbon Intensity
    ax3 = axes[2]
    if (
        "carbon_intensity_gco2_kwh" in df.columns
        and df["carbon_intensity_gco2_kwh"].notna().any()
    ):
        ax3.fill_between(
            df.index, df["carbon_intensity_gco2_kwh"], alpha=0.3, color="#2ecc71"
        )
        ax3.plot(
            df.index, df["carbon_intensity_gco2_kwh"], color="#27ae60", linewidth=1.5
        )
        ax3.set_ylabel("Carbon Intensity\n(gCO₂/kWh)", fontsize=10)
        ax3.set_title("Grid Carbon Intensity", fontsize=11, fontweight="bold")
    else:
        ax3.text(
            0.5,
            0.5,
            "Carbon intensity data not available",
            ha="center",
            va="center",
            transform=ax3.transAxes,
            fontsize=12,
            color="#95a5a6",
        )

    ax3.set_xlabel("Time (UTC)", fontsize=10)

    # Format x-axis
    for ax in axes:
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(
        output_path / "timeseries_plot.png",
        dpi=150,
        bbox_inches="tight",
        facecolor="white",
        edgecolor="none",
    )
    plt.close()
    print(f"Saved: {output_path / 'timeseries_plot.png'}")


def create_network_diagram(output_path: Path, network_path: Path = None):
    """Create GB network topology diagram."""
    fig, ax = plt.subplots(1, 1, figsize=(10, 12))
    ax.set_xlim(-8, 4)
    ax.set_ylim(49, 59)
    ax.set_aspect("equal")
    ax.set_title(
        "GridBridge UK - Simplified GB Transmission Network\n(5-Zone Aggregation)",
        fontsize=14,
        fontweight="bold",
    )

    # Zone positions (approximate UK geography)
    zones = {
        "SCOT": {
            "pos": (-4.0, 56.5),
            "label": "SCOTLAND\n(SPT/SSEN-T)",
            "color": "#3498db",
        },
        "NORTH": {"pos": (-1.5, 54.5), "label": "NORTH\nENGLAND", "color": "#e74c3c"},
        "MIDL": {"pos": (-1.5, 52.5), "label": "MIDLANDS", "color": "#9b59b6"},
        "SOUTH": {"pos": (-3.5, 51.0), "label": "SOUTH &\nWALES", "color": "#27ae60"},
        "LON": {"pos": (0.5, 51.5), "label": "LONDON\n& SE", "color": "#f39c12"},
    }

    # Transmission lines
    lines = [
        ("SCOT", "NORTH", 3300, "B6 Boundary\n~3.3 GW"),
        ("NORTH", "MIDL", 10000, "~10 GW"),
        ("MIDL", "SOUTH", 10000, "~10 GW"),
        ("MIDL", "LON", 5000, "~5 GW"),
        ("SOUTH", "LON", 5000, "~5 GW"),
    ]

    # Draw lines first
    for z1, z2, capacity, label in lines:
        p1 = zones[z1]["pos"]
        p2 = zones[z2]["pos"]
        # Line thickness proportional to capacity
        lw = 2 + (capacity / 3000)
        ax.plot([p1[0], p2[0]], [p1[1], p2[1]], "k-", linewidth=lw, alpha=0.6, zorder=1)
        # Capacity label
        mid = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
        ax.text(
            mid[0] + 0.3,
            mid[1],
            label,
            fontsize=7,
            color="#555",
            ha="left",
            va="center",
            bbox=dict(
                boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.8
            ),
        )

    # Draw zones
    for zone, data in zones.items():
        x, y = data["pos"]
        circle = Circle(
            (x, y),
            0.8,
            facecolor=data["color"],
            edgecolor="white",
            linewidth=3,
            zorder=2,
            alpha=0.9,
        )
        ax.add_patch(circle)
        ax.text(
            x,
            y,
            zone,
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold",
            color="white",
            zorder=3,
        )
        ax.text(
            x, y - 1.3, data["label"], ha="center", va="top", fontsize=8, color="#333"
        )

    # Add generation mix annotations
    gen_mix = {
        "SCOT": "Wind 35%\nHydro 80%",
        "NORTH": "Wind 30%\nGas 25%\nNuclear 35%",
        "MIDL": "Gas 35%\nBiomass 40%",
        "SOUTH": "Nuclear 35%\nSolar 40%",
        "LON": "Gas 20%\nSolar 20%",
    }

    for zone, mix in gen_mix.items():
        x, y = zones[zone]["pos"]
        offset = 1.8 if zone in ["SCOT", "NORTH"] else -1.8
        ax.text(
            x + offset,
            y,
            mix,
            fontsize=7,
            color="#666",
            ha="left" if offset > 0 else "right",
            va="center",
            bbox=dict(
                boxstyle="round,pad=0.3", facecolor="#f8f9fa", edgecolor="#dee2e6"
            ),
        )

    # Add interconnectors
    interconnectors = [
        ((-6, 55.5), "Norway\nNSL 1.4GW", "#17a2b8"),
        ((-6, 51.5), "Ireland\nEWIC/Moyle", "#17a2b8"),
        ((2, 51.0), "France\nIFA 2GW", "#17a2b8"),
        ((2, 52.5), "Netherlands\nBritNed 1GW", "#17a2b8"),
        ((3, 51.5), "Belgium\nNemo 1GW", "#17a2b8"),
    ]

    for pos, label, color in interconnectors:
        ax.plot(pos[0], pos[1], "s", markersize=10, color=color, alpha=0.8)
        ax.text(
            pos[0], pos[1] - 0.6, label, fontsize=6, ha="center", va="top", color=color
        )

    # Legend
    legend_elements = [
        Line2D(
            [0],
            [0],
            marker="o",
            color="w",
            markerfacecolor="#666",
            markersize=12,
            label="GSP Zone",
        ),
        Line2D([0], [0], color="black", linewidth=3, label="Transmission (capacity)"),
        Line2D(
            [0],
            [0],
            marker="s",
            color="w",
            markerfacecolor="#17a2b8",
            markersize=10,
            label="Interconnector",
        ),
    ]
    ax.legend(handles=legend_elements, loc="lower left", fontsize=9)

    ax.set_xlabel("Longitude", fontsize=10)
    ax.set_ylabel("Latitude", fontsize=10)
    ax.grid(True, alpha=0.3)

    # Add note
    ax.text(
        0.5,
        0.02,
        "Note: Simplified 5-zone aggregation for demonstration. Full model uses ~400 GSPs.",
        transform=ax.transAxes,
        ha="center",
        fontsize=8,
        color="#95a5a6",
        style="italic",
    )

    plt.tight_layout()
    plt.savefig(
        output_path / "network_topology.png",
        dpi=150,
        bbox_inches="tight",
        facecolor="white",
        edgecolor="none",
    )
    plt.close()
    print(f"Saved: {output_path / 'network_topology.png'}")


def create_hidden_capacity_diagram(output_path: Path):
    """Create diagram explaining hidden capacity concept."""
    fig, axes = plt.subplots(1, 2, figsize=(14, 7))

    # Left: Waterfall chart showing capacity components
    ax1 = axes[0]
    ax1.set_title(
        "Hidden Capacity Breakdown\n(Example GSP)", fontsize=12, fontweight="bold"
    )

    categories = [
        "Physical\nRating",
        "Static\nPlanning",
        "Queue\nContracted",
        "Reported\nHeadroom",
        "Queue\nAttrition",
        "Dynamic\nRating",
        "Probabilistic\nN-1",
        "TRUE\nHeadroom",
    ]
    values = [500, -50, -200, 250, +80, +40, +30, 400]
    colors = [
        "#3498db",
        "#e74c3c",
        "#e74c3c",
        "#95a5a6",
        "#27ae60",
        "#27ae60",
        "#27ae60",
        "#2ecc71",
    ]

    cumulative = 0
    bars = []
    for i, (cat, val, color) in enumerate(zip(categories, values, colors)):
        if i == 0:
            bars.append(ax1.bar(i, val, color=color, edgecolor="white", linewidth=2))
            cumulative = val
        elif i == 3:  # Reported headroom - standalone
            bars.append(ax1.bar(i, 250, color=color, edgecolor="white", linewidth=2))
        elif i == 7:  # True headroom - standalone
            bars.append(ax1.bar(i, 400, color=color, edgecolor="white", linewidth=2))
        else:
            _bottom = cumulative if val < 0 else cumulative  # noqa: F841
            if val < 0:
                bars.append(
                    ax1.bar(
                        i,
                        val,
                        bottom=cumulative,
                        color=color,
                        edgecolor="white",
                        linewidth=2,
                    )
                )
                cumulative += val
            else:
                bars.append(
                    ax1.bar(
                        i,
                        val,
                        bottom=cumulative,
                        color=color,
                        edgecolor="white",
                        linewidth=2,
                    )
                )
                cumulative += val

        # Value labels
        if i not in [3, 7]:
            label_y = cumulative if i > 0 else val / 2
            ax1.text(
                i,
                label_y + 10,
                f"{val:+d} MW" if i > 0 else f"{val} MW",
                ha="center",
                va="bottom",
                fontsize=9,
                fontweight="bold",
            )

    ax1.set_xticks(range(len(categories)))
    ax1.set_xticklabels(categories, fontsize=8, rotation=0)
    ax1.set_ylabel("Capacity (MW)", fontsize=10)
    ax1.axhline(
        y=250,
        color="#e74c3c",
        linestyle="--",
        linewidth=2,
        alpha=0.7,
        label="Reported headroom",
    )
    ax1.axhline(
        y=400,
        color="#27ae60",
        linestyle="--",
        linewidth=2,
        alpha=0.7,
        label="True headroom",
    )
    ax1.legend(loc="upper right", fontsize=9)
    ax1.set_ylim(0, 550)
    ax1.grid(True, alpha=0.3, axis="y")

    # Add annotation
    ax1.annotate(
        "HIDDEN\nCAPACITY\n+150 MW",
        xy=(5, 320),
        xytext=(6.5, 450),
        fontsize=11,
        fontweight="bold",
        color="#27ae60",
        arrowprops=dict(arrowstyle="->", color="#27ae60", lw=2),
        bbox=dict(boxstyle="round", facecolor="#d5f4e6", edgecolor="#27ae60"),
    )

    # Right: Pie chart of hidden capacity sources
    ax2 = axes[1]
    ax2.set_title(
        "Sources of Hidden Capacity\n(UK Grid Average)", fontsize=12, fontweight="bold"
    )

    sources = [
        "Queue Attrition\n(40%)",
        "Dynamic Line\nRating (25%)",
        "Probabilistic\nN-1 (20%)",
        "Conservative\nForecasts (15%)",
    ]
    sizes = [40, 25, 20, 15]
    colors = ["#3498db", "#e74c3c", "#9b59b6", "#f39c12"]
    explode = (0.05, 0.05, 0.05, 0.05)

    wedges, texts, autotexts = ax2.pie(
        sizes,
        explode=explode,
        labels=sources,
        colors=colors,
        autopct="",
        startangle=90,
        wedgeprops=dict(edgecolor="white", linewidth=2),
    )

    for text in texts:
        text.set_fontsize(10)

    ax2.text(
        0,
        -1.4,
        "Typical UK GSP has 15-40% more usable capacity\nthan reported in static planning studies",
        ha="center",
        va="top",
        fontsize=9,
        color="#666",
        style="italic",
    )

    plt.tight_layout()
    plt.savefig(
        output_path / "hidden_capacity_diagram.png",
        dpi=150,
        bbox_inches="tight",
        facecolor="white",
        edgecolor="none",
    )
    plt.close()
    print(f"Saved: {output_path / 'hidden_capacity_diagram.png'}")


def create_flexibility_diagram(output_path: Path):
    """Create FlexConnect flexibility mechanism diagram."""
    fig, ax = plt.subplots(1, 1, figsize=(14, 8))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")
    ax.set_title(
        "FlexConnect UK - Flexibility Mechanism for Accelerated Connections",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )

    # Connection tiers
    tiers = [
        (
            "TIER 1: NEAR-FIRM",
            "<2% curtailment",
            "Mission-critical with backup",
            "#27ae60",
            85,
        ),
        (
            "TIER 2: FLEXIBLE",
            "2-10% curtailment",
            "Workload-shiftable compute",
            "#3498db",
            60,
        ),
        (
            "TIER 3: INTERRUPTIBLE",
            "10-30% curtailment",
            "Training runs, batch jobs",
            "#f39c12",
            35,
        ),
    ]

    for name, curtail, desc, color, y in tiers:
        box = FancyBboxPatch(
            (5, y - 8),
            40,
            16,
            boxstyle="round,pad=0.02",
            facecolor=color,
            edgecolor="white",
            linewidth=2,
            alpha=0.9,
        )
        ax.add_patch(box)
        ax.text(
            25,
            y + 3,
            name,
            ha="center",
            va="center",
            fontsize=11,
            fontweight="bold",
            color="white",
        )
        ax.text(25, y - 1, curtail, ha="center", va="center", fontsize=9, color="white")
        ax.text(
            25,
            y - 4,
            desc,
            ha="center",
            va="center",
            fontsize=8,
            color="white",
            alpha=0.9,
        )

    # Flexibility assets
    ax.text(
        72,
        92,
        "FLEXIBILITY ASSETS",
        ha="center",
        va="center",
        fontsize=12,
        fontweight="bold",
        color="#2c3e50",
    )

    assets = [
        ("BESS", "4hr UPS +\nFFR Revenue", "#9b59b6", 78),
        ("Gas/CHP", "Backup +\nCapacity Mkt", "#e74c3c", 58),
        ("DSR", "Load Shift +\nDemand Turn Up", "#17a2b8", 38),
    ]

    for name, desc, color, y in assets:
        box = FancyBboxPatch(
            (55, y - 6),
            34,
            12,
            boxstyle="round,pad=0.02",
            facecolor=color,
            edgecolor="white",
            linewidth=2,
            alpha=0.85,
        )
        ax.add_patch(box)
        ax.text(
            72,
            y + 2,
            name,
            ha="center",
            va="center",
            fontsize=10,
            fontweight="bold",
            color="white",
        )
        ax.text(
            72,
            y - 2,
            desc,
            ha="center",
            va="center",
            fontsize=8,
            color="white",
            alpha=0.9,
        )

    # Arrows connecting tiers to assets
    ax.annotate(
        "",
        xy=(55, 78),
        xytext=(45, 85),
        arrowprops=dict(arrowstyle="->", color="#bdc3c7", lw=1.5),
    )
    ax.annotate(
        "",
        xy=(55, 58),
        xytext=(45, 60),
        arrowprops=dict(arrowstyle="->", color="#bdc3c7", lw=1.5),
    )
    ax.annotate(
        "",
        xy=(55, 38),
        xytext=(45, 35),
        arrowprops=dict(arrowstyle="->", color="#bdc3c7", lw=1.5),
    )

    # Timeline comparison
    ax.text(
        50,
        18,
        "CONNECTION TIMELINE COMPARISON",
        ha="center",
        va="center",
        fontsize=11,
        fontweight="bold",
        color="#2c3e50",
    )

    # Traditional
    ax.add_patch(
        FancyBboxPatch(
            (10, 8),
            35,
            5,
            boxstyle="round,pad=0.01",
            facecolor="#e74c3c",
            edgecolor="white",
            linewidth=2,
        )
    )
    ax.text(
        27.5,
        10.5,
        "Traditional: 5-10 years",
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold",
        color="white",
    )

    # FlexConnect
    ax.add_patch(
        FancyBboxPatch(
            (55, 8),
            15,
            5,
            boxstyle="round,pad=0.01",
            facecolor="#27ae60",
            edgecolor="white",
            linewidth=2,
        )
    )
    ax.text(
        62.5,
        10.5,
        "FlexConnect: 6-18 months",
        ha="center",
        va="center",
        fontsize=9,
        fontweight="bold",
        color="white",
    )

    ax.text(
        85,
        10.5,
        "▶ 70-85%\nfaster",
        ha="center",
        va="center",
        fontsize=10,
        fontweight="bold",
        color="#27ae60",
    )

    plt.tight_layout()
    plt.savefig(
        output_path / "flexibility_diagram.png",
        dpi=150,
        bbox_inches="tight",
        facecolor="white",
        edgecolor="none",
    )
    plt.close()
    print(f"Saved: {output_path / 'flexibility_diagram.png'}")


def create_api_coverage_matrix(output_path: Path):
    """Create API data coverage matrix."""
    fig, ax = plt.subplots(1, 1, figsize=(12, 8))

    # Data types vs sources
    data_types = [
        "System Demand",
        "Generation by Fuel",
        "System Frequency",
        "Imbalance Price",
        "Carbon Intensity",
        "Weather/Temperature",
        "Outage Schedule",
        "Queue Data",
        "Capacity Maps",
        "Fault Levels",
    ]

    sources = [
        "Carbon\nIntensity",
        "Elexon\nBMRS",
        "Elexon\nInsights",
        "ESO\nPortal",
        "Met\nOffice",
        "DNO\nMaps",
    ]

    # Coverage matrix (0=none, 1=partial, 2=full)
    coverage = np.array(
        [
            [1, 2, 2, 2, 0, 0],  # Demand
            [2, 2, 2, 1, 0, 0],  # Generation
            [0, 2, 0, 2, 0, 0],  # Frequency
            [0, 2, 2, 0, 0, 0],  # Imbalance
            [2, 0, 0, 0, 0, 0],  # Carbon
            [0, 1, 0, 0, 2, 0],  # Weather
            [0, 0, 0, 2, 0, 0],  # Outage
            [0, 0, 0, 2, 0, 0],  # Queue
            [0, 0, 0, 0, 0, 2],  # Capacity
            [0, 0, 0, 1, 0, 1],  # Fault
        ]
    )

    # Create heatmap
    cmap = plt.cm.RdYlGn
    _im = ax.imshow(coverage, cmap=cmap, aspect="auto", vmin=0, vmax=2)  # noqa: F841

    # Labels
    ax.set_xticks(range(len(sources)))
    ax.set_xticklabels(sources, fontsize=10)
    ax.set_yticks(range(len(data_types)))
    ax.set_yticklabels(data_types, fontsize=10)

    # Add text annotations
    for i in range(len(data_types)):
        for j in range(len(sources)):
            val = coverage[i, j]
            text = ["✗", "◐", "✓"][val]
            color = ["#c0392b", "#f39c12", "#27ae60"][val]
            ax.text(
                j,
                i,
                text,
                ha="center",
                va="center",
                fontsize=14,
                color=color,
                fontweight="bold",
            )

    ax.set_title(
        "GridBridge UK - Data Source Coverage Matrix",
        fontsize=14,
        fontweight="bold",
        pad=20,
    )

    # Legend
    legend_elements = [
        mpatches.Patch(facecolor="#27ae60", label="Full Coverage (✓)"),
        mpatches.Patch(facecolor="#f39c12", label="Partial Coverage (◐)"),
        mpatches.Patch(facecolor="#c0392b", label="Not Available (✗)"),
    ]
    ax.legend(
        handles=legend_elements, loc="upper right", bbox_to_anchor=(1.15, 1), fontsize=9
    )

    # Grid
    ax.set_xticks(np.arange(-0.5, len(sources), 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(data_types), 1), minor=True)
    ax.grid(which="minor", color="white", linewidth=2)

    plt.tight_layout()
    plt.savefig(
        output_path / "api_coverage_matrix.png",
        dpi=150,
        bbox_inches="tight",
        facecolor="white",
        edgecolor="none",
    )
    plt.close()
    print(f"Saved: {output_path / 'api_coverage_matrix.png'}")


def main(args):
    output_path = Path(args.output)
    output_path.mkdir(parents=True, exist_ok=True)

    print("Generating GridBridge UK visualizations...")
    print("=" * 50)

    # Generate all diagrams
    create_architecture_diagram(output_path)
    create_data_flow_diagram(output_path)
    create_network_diagram(output_path)
    create_hidden_capacity_diagram(output_path)
    create_flexibility_diagram(output_path)
    create_api_coverage_matrix(output_path)

    # Generate timeseries if data exists
    canonical_path = Path(args.data) / "canonical.parquet"
    create_timeseries_plot(canonical_path, output_path)

    print("=" * 50)
    print(f"All visualizations saved to: {output_path}")
    print("\nGenerated files:")
    for f in sorted(output_path.glob("*.png")):
        print(f"  - {f.name}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate GridBridge UK visualizations"
    )
    parser.add_argument(
        "--output", default="out/figures", help="Output directory for figures"
    )
    parser.add_argument(
        "--data", default="out", help="Data directory containing canonical.parquet"
    )
    args = parser.parse_args()
    main(args)

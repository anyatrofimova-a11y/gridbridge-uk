"""Smoke tests for ingestion pipeline."""

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest

# Add examples to path
sys.path.insert(0, str(Path(__file__).parent.parent / "examples"))

from ingest_real_data import (
    canonicalize_to_schema,
    compute_data_hash,
    fetch_carbon_intensity_generation,
)


class TestCanonicalization:
    """Test data canonicalisation logic."""

    def test_empty_inputs_returns_standard_columns(self):
        """Empty inputs should still produce standard schema."""
        result = canonicalize_to_schema(
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
        )
        assert "demand_mw" in result.columns
        assert "wind_mw" in result.columns
        assert "solar_mw" in result.columns

    def test_demand_passthrough(self):
        """Demand values should pass through unchanged."""
        idx = pd.date_range("2025-01-01", periods=3, freq="30min", tz="UTC")
        demand = pd.DataFrame({"demand_mw": [100, 200, 300]}, index=idx)

        result = canonicalize_to_schema(
            pd.DataFrame(),
            pd.DataFrame(),
            demand,
            pd.DataFrame(),
            pd.DataFrame(),
        )

        assert list(result["demand_mw"]) == [100, 200, 300]

    def test_duplicate_timestamps_removed(self):
        """Duplicate timestamps should be deduplicated."""
        idx = pd.DatetimeIndex([
            "2025-01-01 00:00:00+00:00",
            "2025-01-01 00:00:00+00:00",
            "2025-01-01 00:30:00+00:00",
        ])
        demand = pd.DataFrame({"demand_mw": [100, 150, 200]}, index=idx)

        result = canonicalize_to_schema(
            pd.DataFrame(),
            pd.DataFrame(),
            demand,
            pd.DataFrame(),
            pd.DataFrame(),
        )

        assert len(result) == 2  # Duplicates removed


class TestDataHash:
    """Test audit hash computation."""

    def test_deterministic_hash(self):
        """Same data should produce same hash."""
        df = pd.DataFrame({"a": [1, 2, 3], "b": [4, 5, 6]})
        hash1 = compute_data_hash(df)
        hash2 = compute_data_hash(df)
        assert hash1 == hash2

    def test_different_data_different_hash(self):
        """Different data should produce different hash."""
        df1 = pd.DataFrame({"a": [1, 2, 3]})
        df2 = pd.DataFrame({"a": [1, 2, 4]})
        assert compute_data_hash(df1) != compute_data_hash(df2)

    def test_hash_length(self):
        """Hash should be truncated to 16 characters."""
        df = pd.DataFrame({"a": [1, 2, 3]})
        hash_val = compute_data_hash(df)
        assert len(hash_val) == 16


class TestSchemaValidation:
    """Test canonical schema requirements."""

    def test_standard_columns_present(self):
        """All standard columns should be present in output."""
        result = canonicalize_to_schema(
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
        )

        expected_cols = [
            "demand_mw", "wind_mw", "solar_mw", "gas_mw", "nuclear_mw",
            "coal_mw", "hydro_mw", "biomass_mw", "imports_mw",
            "carbon_intensity_gco2_kwh", "system_price_gbp_mwh"
        ]

        for col in expected_cols:
            assert col in result.columns, f"Missing column: {col}"

    def test_column_order(self):
        """Standard columns should come first in output."""
        idx = pd.date_range("2025-01-01", periods=3, freq="30min", tz="UTC")
        demand = pd.DataFrame({"demand_mw": [100, 200, 300]}, index=idx)

        result = canonicalize_to_schema(
            pd.DataFrame(),
            pd.DataFrame(),
            demand,
            pd.DataFrame(),
            pd.DataFrame(),
        )

        assert result.columns[0] == "demand_mw"


class TestElexonFuelMapping:
    """Test Elexon fuel type mapping."""

    def test_ccgt_maps_to_gas(self):
        """CCGT fuel type should map to gas_mw."""
        idx = pd.date_range("2025-01-01", periods=3, freq="30min", tz="UTC")
        elexon_gen = pd.DataFrame({"CCGT": [1000, 1100, 1200]}, index=idx)

        result = canonicalize_to_schema(
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            elexon_gen,
            pd.DataFrame(),
        )

        assert "gas_mw" in result.columns
        assert list(result["gas_mw"]) == [1000, 1100, 1200]

    def test_imports_aggregated(self):
        """Import columns should be aggregated."""
        idx = pd.date_range("2025-01-01", periods=2, freq="30min", tz="UTC")
        elexon_gen = pd.DataFrame({
            "INTFR": [500, 600],
            "INTIRL": [200, 300],
            "INTNED": [100, 100],
        }, index=idx)

        result = canonicalize_to_schema(
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            elexon_gen,
            pd.DataFrame(),
        )

        assert "imports_mw" in result.columns
        assert list(result["imports_mw"]) == [800, 1000]


@pytest.mark.integration
class TestAPIIntegration:
    """Integration tests against real APIs (skipped in CI by default)."""

    def test_carbon_intensity_api_responds(self):
        """Carbon Intensity API should return data for recent dates."""
        from datetime import timedelta

        start = datetime(2025, 1, 15, tzinfo=timezone.utc)
        end = start + timedelta(days=1)

        df = fetch_carbon_intensity_generation(start, end)

        # Should get ~48 half-hourly records
        assert len(df) >= 40, f"Expected >=40 rows, got {len(df)}"
        assert "wind_pct" in df.columns or len(df.columns) > 0


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_dataframe_handling(self):
        """Empty dataframes should not cause errors."""
        result = canonicalize_to_schema(
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
        )

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 0

    def test_nan_handling(self):
        """NaN values should be preserved, not dropped."""
        idx = pd.date_range("2025-01-01", periods=3, freq="30min", tz="UTC")
        demand = pd.DataFrame({"demand_mw": [100, float('nan'), 300]}, index=idx)

        result = canonicalize_to_schema(
            pd.DataFrame(),
            pd.DataFrame(),
            demand,
            pd.DataFrame(),
            pd.DataFrame(),
        )

        assert len(result) == 3
        assert pd.isna(result["demand_mw"].iloc[1])

"""Simulate one-day behind-the-meter battery peak shaving with energy checks."""

from __future__ import annotations

import csv
import json
import random
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DATA_PATH = ROOT / "data" / "hourly_load.csv"
DISPATCH_PATH = ROOT / "results" / "dispatch.csv"
REPORT_PATH = ROOT / "results" / "report.json"
SEED = 39
CAPACITY_KWH = 24.0
MIN_SOC_KWH = 2.0
MAX_SOC_KWH = 22.0
INITIAL_SOC_KWH = 12.0
MAX_POWER_KW = 7.0
CHARGE_EFFICIENCY = 0.95
DISCHARGE_EFFICIENCY = 0.95
PEAK_TARGET_KW = 31.0
CHARGE_HOURS = set(range(6))


def generate_load(seed: int = SEED) -> list[dict[str, float | int | str]]:
    rng = random.Random(seed)
    rows = []
    for hour in range(24):
        overnight = 14.0 if hour < 6 else 0.0
        morning = 8.0 if 7 <= hour <= 9 else 0.0
        evening = 17.0 if 17 <= hour <= 20 else 0.0
        midday = 5.0 if 11 <= hour <= 14 else 0.0
        load = 18.0 + morning + evening + midday - overnight + rng.uniform(-0.6, 0.6)
        rows.append({"hour": hour, "load_kw": round(load, 4), "scenario": "synthetic"})
    return rows


def dispatch(
    load_rows: list[dict[str, float | int | str]],
    *,
    capacity_kwh: float = CAPACITY_KWH,
    min_soc_kwh: float = MIN_SOC_KWH,
    max_soc_kwh: float = MAX_SOC_KWH,
    initial_soc_kwh: float = INITIAL_SOC_KWH,
    max_power_kw: float = MAX_POWER_KW,
    charge_efficiency: float = CHARGE_EFFICIENCY,
    discharge_efficiency: float = DISCHARGE_EFFICIENCY,
    peak_target_kw: float = PEAK_TARGET_KW,
    charge_hours: set[int] | None = None,
) -> list[dict[str, float | int]]:
    if not 0 <= min_soc_kwh <= initial_soc_kwh <= max_soc_kwh <= capacity_kwh:
        raise ValueError("SoC values must satisfy 0 <= minimum <= initial <= maximum <= capacity")
    if max_power_kw < 0 or not 0 < charge_efficiency <= 1 or not 0 < discharge_efficiency <= 1:
        raise ValueError("Power must be non-negative and efficiencies must be in (0, 1]")
    charging_periods = CHARGE_HOURS if charge_hours is None else charge_hours
    soc = initial_soc_kwh
    rows: list[dict[str, float | int]] = []
    for item in load_rows:
        hour = int(item["hour"])
        load = float(item["load_kw"])
        soc_before = soc
        charge_kw = 0.0
        discharge_kw = 0.0
        if hour in charging_periods and soc < max_soc_kwh:
            charge_kw = min(max_power_kw, (max_soc_kwh - soc) / charge_efficiency)
            soc += charge_kw * charge_efficiency
        elif load > peak_target_kw and soc > min_soc_kwh:
            discharge_kw = min(max_power_kw, load - peak_target_kw, (soc - min_soc_kwh) * discharge_efficiency)
            soc -= discharge_kw / discharge_efficiency
        grid_import = load + charge_kw - discharge_kw
        expected_soc = soc_before + charge_kw * charge_efficiency - discharge_kw / discharge_efficiency
        rows.append(
            {
                "hour": hour,
                "load_kw": load,
                "charge_kw": charge_kw,
                "discharge_kw": discharge_kw,
                "grid_import_kw": grid_import,
                "soc_before_kwh": soc_before,
                "soc_after_kwh": soc,
                "soc_balance_residual_kwh": soc - expected_soc,
            }
        )
    return rows


def evaluate(load_rows: list[dict[str, float | int | str]], dispatch_rows: list[dict[str, float | int]]) -> dict[str, object]:
    if len(load_rows) != 24 or len(dispatch_rows) != 24:
        raise ValueError("This demo expects exactly 24 hourly intervals")
    load_peak = max(float(row["load_kw"]) for row in load_rows)
    grid_peak = max(float(row["grid_import_kw"]) for row in dispatch_rows)
    charge_total = sum(float(row["charge_kw"]) for row in dispatch_rows)
    discharge_total = sum(float(row["discharge_kw"]) for row in dispatch_rows)
    charge_loss = charge_total * (1.0 - CHARGE_EFFICIENCY)
    discharge_loss = discharge_total * (1.0 / DISCHARGE_EFFICIENCY - 1.0)
    residual = max(abs(float(row["soc_balance_residual_kwh"])) for row in dispatch_rows)
    initial = float(dispatch_rows[0]["soc_before_kwh"])
    final = float(dispatch_rows[-1]["soc_after_kwh"])
    total_grid = sum(float(row["grid_import_kw"]) for row in dispatch_rows)
    total_load = sum(float(row["load_kw"]) for row in load_rows)
    energy_residual = (charge_total - discharge_total) - (final - initial) - (charge_loss + discharge_loss)
    return {
        "project": "battery-dispatch-sim",
        "data_kind": "deterministic_synthetic",
        "seed": SEED,
        "interval_hours": 1,
        "capacity_kwh": CAPACITY_KWH,
        "soc_limits_kwh": {"minimum": MIN_SOC_KWH, "maximum": MAX_SOC_KWH},
        "max_charge_or_discharge_kw": MAX_POWER_KW,
        "charge_efficiency": CHARGE_EFFICIENCY,
        "discharge_efficiency": DISCHARGE_EFFICIENCY,
        "load_peak_kw": round(load_peak, 4),
        "grid_import_peak_kw": round(grid_peak, 4),
        "peak_reduction_kw": round(load_peak - grid_peak, 4),
        "load_energy_kwh": round(total_load, 4),
        "grid_import_energy_kwh": round(total_grid, 4),
        "battery_charge_input_kwh": round(charge_total, 4),
        "battery_discharge_output_kwh": round(discharge_total, 4),
        "estimated_conversion_losses_kwh": round(charge_loss + discharge_loss, 6),
        "initial_soc_kwh": initial,
        "final_soc_kwh": round(final, 6),
        "max_soc_balance_residual_kwh": round(residual, 10),
        "energy_conservation_residual_kwh": round(energy_residual, 10),
        "limitations": [
            "The hourly load and all battery parameters are illustrative synthetic inputs.",
            "No degradation, tariff, reserve requirement, inverter dynamics, or uncertainty is modeled.",
            "Peak reduction is a simulator result, not a verified site saving or dispatch recommendation.",
        ],
    }


def write_outputs() -> dict[str, object]:
    loads = generate_load()
    results = dispatch(loads)
    report = evaluate(loads, results)
    DATA_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with DATA_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(loads[0]))
        writer.writeheader()
        writer.writerows(loads)
    with DISPATCH_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(results[0]))
        writer.writeheader()
        writer.writerows(results)
    REPORT_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return report


def main() -> None:
    report = write_outputs()
    print(f"Peak: {report['load_peak_kw']:.2f} -> {report['grid_import_peak_kw']:.2f} kW")
    print(f"Peak reduction: {report['peak_reduction_kw']:.2f} kW; conversion loss: {report['estimated_conversion_losses_kwh']:.3f} kWh")
    print(f"Energy-balance residual: {report['energy_conservation_residual_kwh']:.2e} kWh")
    print(f"Wrote {DATA_PATH.relative_to(ROOT)}, {DISPATCH_PATH.relative_to(ROOT)} and {REPORT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

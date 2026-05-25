"""Electrical aggregates aligned with report_generator / dashboard JS."""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional


def reactive_power_var(apparent_va: float, power_factor: float) -> float:
    s = apparent_va or 0.0
    pf = max(0.0, min(1.0, power_factor or 0.0))
    if s <= 0 or pf <= 0:
        return 0.0
    return s * math.sin(math.acos(pf))


def _float(row: Dict[str, Any], key: str, default: float = 0.0) -> float:
    v = row.get(key)
    if v is None:
        return default
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def aggregate_rows_three_pzem(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    total_active = 0.0
    total_apparent = 0.0
    total_reactive = 0.0
    total_energy = 0.0

    for r in rows:
        v = _float(r, "voltage")
        i_ = _float(r, "current")
        p = _float(r, "power")
        pf = _float(r, "power_factor", 1.0)
        pf = max(0.0, min(1.0, pf))
        apparent = v * i_
        total_active += p
        total_apparent += apparent
        total_reactive += reactive_power_var(apparent, pf)
        total_energy += _float(r, "energy")

    pf_sys = (total_active / total_apparent) if total_apparent > 0 else 0.0
    return {
        "total_active_power_w": round(total_active, 2),
        "total_apparent_power_va": round(total_apparent, 2),
        "total_reactive_power_var": round(total_reactive, 2),
        "total_reactive_power_kvar": round(total_reactive / 1000.0, 4),
        "system_power_factor": round(pf_sys, 4),
        "total_energy_kwh": round(total_energy, 3),
    }


def aggregate_rows_single_meter(rows: List[Dict[str, Any]]) -> Dict[str, Any]:
    if not rows:
        return {
            "active_power_w": 0.0,
            "apparent_power_va": 0.0,
            "reactive_power_var": 0.0,
            "reactive_power_kvar": 0.0,
            "power_factor": 0.0,
            "energy_kwh": 0.0,
        }
    r = rows[0]
    v = _float(r, "voltage")
    i_ = _float(r, "current")
    p = _float(r, "power")
    pf = max(0.0, min(1.0, _float(r, "power_factor", 1.0)))
    apparent = v * i_
    q = reactive_power_var(apparent, pf)
    return {
        "active_power_w": round(p, 2),
        "apparent_power_va": round(apparent, 2),
        "reactive_power_var": round(q, 2),
        "reactive_power_kvar": round(q / 1000.0, 4),
        "power_factor": round(pf, 4),
        "energy_kwh": round(_float(r, "energy"), 3),
    }


def derive_phase_from_row(row: Dict[str, Any]) -> Optional[str]:
    da = str(row.get("device_address") or "")
    if da.upper().endswith("-R"):
        return "R"
    if da.upper().endswith("-S"):
        return "S"
    if da.upper().endswith("-T"):
        return "T"
    name = (row.get("device_name") or "").upper()
    for ph in ("R", "S", "T"):
        if f"PHASE {ph}" in name or f"-{ph}" in name:
            return ph
    return None

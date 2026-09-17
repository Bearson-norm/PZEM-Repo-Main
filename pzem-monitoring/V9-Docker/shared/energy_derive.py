"""
Broker-side wrap/reset classification and window kWh derivation.

Firmware v1.2.0 does not send accumulated_energy_kwh. Ignore leftover v1.1.0
keys and derive from energy_first / energy_last / calibration only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

WRAP_REGISTER_MAX = 9999.99
WRAP_NEAR_RAW = 9000.0
WRAP_LOW_RAW = 100.0
DEFAULT_SCALE = 1.0
DEFAULT_OFFSET = 0.0


@dataclass(frozen=True)
class WrapThresholds:
    scale: float
    offset: float
    wrap_kwh: float
    wrap_near_kwh: float
    wrap_low_kwh: float


@dataclass(frozen=True)
class DerivedWindow:
    accumulated_energy_kwh: Optional[float]
    energy_method: str
    energy_event: str
    energy_scale: float
    energy_offset: float


def _as_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def parse_calibration(data: Optional[Dict[str, Any]]) -> Tuple[float, float]:
    """Read compile-time scale/offset already applied on the device."""
    payload = data if isinstance(data, dict) else {}
    cal = payload.get("calibration")
    if not isinstance(cal, dict):
        cal = {}
    scale = _as_float(cal.get("energy_scale"))
    offset = _as_float(cal.get("energy_offset"))
    return (
        scale if scale is not None else DEFAULT_SCALE,
        offset if offset is not None else DEFAULT_OFFSET,
    )


def wrap_thresholds(
    scale: float = DEFAULT_SCALE, offset: float = DEFAULT_OFFSET
) -> WrapThresholds:
    return WrapThresholds(
        scale=scale,
        offset=offset,
        wrap_kwh=WRAP_REGISTER_MAX * scale + offset,
        wrap_near_kwh=WRAP_NEAR_RAW * scale + offset,
        wrap_low_kwh=WRAP_LOW_RAW * scale + offset,
    )


def is_wrap_registers(
    first: float,
    last: float,
    scale: float = DEFAULT_SCALE,
    offset: float = DEFAULT_OFFSET,
) -> bool:
    thresholds = wrap_thresholds(scale, offset)
    return last < first and first >= thresholds.wrap_near_kwh and last <= thresholds.wrap_low_kwh


def is_reset_registers(
    first: float,
    last: float,
    scale: float = DEFAULT_SCALE,
    offset: float = DEFAULT_OFFSET,
) -> bool:
    return last < first and not is_wrap_registers(first, last, scale, offset)


def wrap_consumption(
    first: float,
    last: float,
    scale: float = DEFAULT_SCALE,
    offset: float = DEFAULT_OFFSET,
) -> float:
    """(wrap_kwh - first) + (last - offset)."""
    thresholds = wrap_thresholds(scale, offset)
    return (thresholds.wrap_kwh - first) + (last - offset)


def firmware_event_hint(value: Any) -> Optional[str]:
    if value is None or value == "":
        return None
    text = str(value).strip().lower()
    return text or None


def derive_window_kwh(
    energy_first: Optional[float],
    energy_last: Optional[float],
    firmware_event: Any = None,
    scale: float = DEFAULT_SCALE,
    offset: float = DEFAULT_OFFSET,
) -> DerivedWindow:
    """
    Classify wrap/reset independently, then derive window consumption.

    energy_event on the result is the classified value (none|wrap|reset).
    energy_method is broker-derived: delta|wrap|reset|untrusted.
    Payload accumulated_energy_kwh / energy_method are never read here.
    """
    hint = firmware_event_hint(firmware_event)
    wrap = (
        is_wrap_registers(energy_first, energy_last, scale, offset)
        if energy_first is not None and energy_last is not None
        else False
    )
    reset = (
        is_reset_registers(energy_first, energy_last, scale, offset)
        if energy_first is not None and energy_last is not None
        else False
    )

    if energy_first is None or energy_last is None:
        return DerivedWindow(
            accumulated_energy_kwh=None,
            energy_method="untrusted",
            energy_event="none",
            energy_scale=scale,
            energy_offset=offset,
        )

    if reset or (hint == "reset" and not wrap):
        return DerivedWindow(
            accumulated_energy_kwh=None,
            energy_method="reset",
            energy_event="reset",
            energy_scale=scale,
            energy_offset=offset,
        )

    if energy_last >= energy_first:
        return DerivedWindow(
            accumulated_energy_kwh=energy_last - energy_first,
            energy_method="delta",
            energy_event="none",
            energy_scale=scale,
            energy_offset=offset,
        )

    if wrap or hint == "wrap":
        return DerivedWindow(
            accumulated_energy_kwh=wrap_consumption(
                energy_first, energy_last, scale, offset
            ),
            energy_method="wrap",
            energy_event="wrap",
            energy_scale=scale,
            energy_offset=offset,
        )

    return DerivedWindow(
        accumulated_energy_kwh=None,
        energy_method="untrusted",
        energy_event="none",
        energy_scale=scale,
        energy_offset=offset,
    )

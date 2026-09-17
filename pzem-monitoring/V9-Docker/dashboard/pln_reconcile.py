"""
PLN invoice kWh reconciliation from 3-phase PZEM meter registers.

Pure functions — no Flask, no tariff / rupiah math.
Firmware remains the source of the hardware register; this module only
applies T0→T1 register-delta, wrap, and reset-wipe rules.
Window kWh is derived on ingest; never sum windows across a hardware reset.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

from shared.energy_derive import (
    DEFAULT_OFFSET,
    DEFAULT_SCALE,
    is_reset_registers,
    is_wrap_registers,
    wrap_consumption,
)

PHASES = ("R", "S", "T")
DEFAULT_GAP_MINUTES = 20
ERROR_ALERT_PCT = 5.0


@dataclass
class MeterRow:
    phase: str
    meter_energy_kwh: float
    period_end_unix: int
    time_synced: bool = True
    energy_event: Optional[str] = None
    energy_scale: Optional[float] = None
    energy_offset: Optional[float] = None


@dataclass
class EnergyEvent:
    phase: str
    event_type: str
    period_end_unix: int


@dataclass
class PhaseResult:
    phase: str
    start_kwh: Optional[float] = None
    end_kwh: Optional[float] = None
    start_period_end_unix: Optional[int] = None
    end_period_end_unix: Optional[int] = None
    phase_kwh: Optional[float] = None
    method: str = "none"
    quality: str = "incomplete"
    suffix_kwh: Optional[float] = None
    suffix_start_unix: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ReconcileResult:
    phases: Dict[str, PhaseResult] = field(default_factory=dict)
    total_kwh: Optional[float] = None
    invoice_kwh: Optional[float] = None
    error_pct: Optional[float] = None
    quality: str = "incomplete"
    pln_register_t0: Optional[float] = None
    pln_register_t1: Optional[float] = None
    meter_sum_t0: Optional[float] = None
    meter_sum_t1: Optional[float] = None
    offset_t0: Optional[float] = None
    offset_t1: Optional[float] = None
    flags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "phases": {k: v.to_dict() for k, v in self.phases.items()},
            "total_kwh": self.total_kwh,
            "invoice_kwh": self.invoice_kwh,
            "error_pct": self.error_pct,
            "quality": self.quality,
            "pln_register_t0": self.pln_register_t0,
            "pln_register_t1": self.pln_register_t1,
            "meter_sum_t0": self.meter_sum_t0,
            "meter_sum_t1": self.meter_sum_t1,
            "offset_t0": self.offset_t0,
            "offset_t1": self.offset_t1,
            "flags": list(self.flags),
        }


def _as_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _as_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return True if value else False
    if value in (1, "1", "true", "True", "yes"):
        return True
    return False


def meter_row_from_mapping(phase: str, row: Dict[str, Any]) -> Optional[MeterRow]:
    energy = _as_float(
        row.get("meter_energy_kwh")
        if row.get("meter_energy_kwh") is not None
        else row.get("energy")
    )
    period_end = _as_int(row.get("period_end_unix"))
    if energy is None or period_end is None:
        return None
    return MeterRow(
        phase=str(phase).upper(),
        meter_energy_kwh=energy,
        period_end_unix=period_end,
        time_synced=_as_bool(row.get("time_synced")),
        energy_event=(str(row["energy_event"]).strip().lower() if row.get("energy_event") else None),
        energy_scale=_as_float(row.get("energy_scale")),
        energy_offset=_as_float(row.get("energy_offset")),
    )


def is_usable_bound(row: MeterRow) -> bool:
    return bool(row.time_synced) and row.period_end_unix > 0


def pick_start_register(rows: Sequence[MeterRow], t0_unix: int) -> Optional[MeterRow]:
    """First synced register at or just after T0."""
    candidates = [
        r for r in rows if is_usable_bound(r) and r.period_end_unix >= t0_unix
    ]
    if not candidates:
        return None
    return min(candidates, key=lambda r: r.period_end_unix)


def pick_end_register(rows: Sequence[MeterRow], t1_unix: int) -> Optional[MeterRow]:
    """Last synced register at or just before T1."""
    candidates = [
        r for r in rows if is_usable_bound(r) and r.period_end_unix <= t1_unix
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda r: r.period_end_unix)


def events_in_window(
    events: Iterable[EnergyEvent], t0_unix: int, t1_unix: int, event_type: str
) -> List[EnergyEvent]:
    return [
        e
        for e in events
        if e.event_type == event_type
        and e.period_end_unix is not None
        and t0_unix < e.period_end_unix <= t1_unix
    ]


def wrap_kwh(
    start: float,
    end: float,
    scale: float = DEFAULT_SCALE,
    offset: float = DEFAULT_OFFSET,
) -> float:
    return wrap_consumption(start, end, scale, offset)


def _calibration_of(
    *rows: Optional[MeterRow],
    default_scale: float = DEFAULT_SCALE,
    default_offset: float = DEFAULT_OFFSET,
) -> Tuple[float, float]:
    scale = default_scale
    offset = default_offset
    for row in rows:
        if row is None:
            continue
        if row.energy_scale is not None:
            scale = float(row.energy_scale)
            break
    for row in rows:
        if row is None:
            continue
        if row.energy_offset is not None:
            offset = float(row.energy_offset)
            break
    return scale, offset


def find_reset_unix(
    rows: Sequence[MeterRow],
    events: Sequence[EnergyEvent],
    t0_unix: int,
    t1_unix: int,
    scale: float,
    offset: float,
) -> Optional[int]:
    """Latest reset in (T0, T1] from events or independent register drops."""
    times: List[int] = []
    for event in events_in_window(events, t0_unix, t1_unix, "reset"):
        times.append(int(event.period_end_unix))
    usable = sorted(
        [
            r
            for r in rows
            if is_usable_bound(r) and t0_unix <= r.period_end_unix <= t1_unix
        ],
        key=lambda r: r.period_end_unix,
    )
    for prev, curr in zip(usable, usable[1:]):
        sc, off = _calibration_of(
            curr, prev, default_scale=scale, default_offset=offset
        )
        if is_reset_registers(prev.meter_energy_kwh, curr.meter_energy_kwh, sc, off):
            times.append(int(curr.period_end_unix))
        if (curr.energy_event or "").strip().lower() == "reset":
            times.append(int(curr.period_end_unix))
    return max(times) if times else None


def compute_suffix(
    rows: Sequence[MeterRow],
    reset_unix: int,
    t1_unix: int,
) -> Tuple[Optional[float], Optional[int]]:
    """
    Informational new series after the reset window. Not a T0→T1 bill.
    First time_synced snapshot strictly after the reset window, through T1.
    """
    after = [
        r
        for r in rows
        if is_usable_bound(r) and reset_unix < r.period_end_unix <= t1_unix
    ]
    if not after:
        return None, None
    start_row = min(after, key=lambda r: r.period_end_unix)
    end_row = pick_end_register(rows, t1_unix)
    if end_row is None or end_row.period_end_unix < start_row.period_end_unix:
        return None, start_row.period_end_unix
    scale, offset = _calibration_of(start_row, end_row)
    start = float(start_row.meter_energy_kwh)
    end = float(end_row.meter_energy_kwh)
    suffix_start = int(start_row.period_end_unix)
    if end >= start:
        return end - start, suffix_start
    if is_wrap_registers(start, end, scale, offset):
        return wrap_consumption(start, end, scale, offset), suffix_start
    return None, suffix_start


def reconcile_phase(
    phase: str,
    rows: Sequence[MeterRow],
    events: Sequence[EnergyEvent],
    t0_unix: int,
    t1_unix: int,
) -> PhaseResult:
    result = PhaseResult(phase=phase)
    start_row = pick_start_register(rows, t0_unix)
    end_row = pick_end_register(rows, t1_unix)

    if start_row is None or end_row is None or start_row.period_end_unix > t1_unix:
        result.quality = "incomplete"
        result.method = "none"
        if start_row is not None and start_row.period_end_unix <= t1_unix:
            result.start_kwh = start_row.meter_energy_kwh
            result.start_period_end_unix = start_row.period_end_unix
        if end_row is not None:
            result.end_kwh = end_row.meter_energy_kwh
            result.end_period_end_unix = end_row.period_end_unix
        return result

    start = float(start_row.meter_energy_kwh)
    end = float(end_row.meter_energy_kwh)
    result.start_kwh = start
    result.end_kwh = end
    result.start_period_end_unix = start_row.period_end_unix
    result.end_period_end_unix = end_row.period_end_unix
    scale, offset = _calibration_of(start_row, end_row)

    wrap_ev = events_in_window(events, t0_unix, t1_unix, "wrap")
    reset_ev = events_in_window(events, t0_unix, t1_unix, "reset")
    last_reset = find_reset_unix(rows, events, t0_unix, t1_unix, scale, offset)
    independent_reset = is_reset_registers(start, end, scale, offset)

    if last_reset is not None or reset_ev or independent_reset:
        result.phase_kwh = None
        result.method = "reset_wipe"
        result.quality = "degraded"
        reset_at = last_reset
        if reset_at is None and reset_ev:
            reset_at = max(int(e.period_end_unix) for e in reset_ev)
        if reset_at is None:
            reset_at = int(end_row.period_end_unix)
        suffix_kwh, suffix_start = compute_suffix(rows, reset_at, t1_unix)
        result.suffix_kwh = suffix_kwh
        result.suffix_start_unix = suffix_start
        return result

    if end >= start:
        result.phase_kwh = end - start
        result.method = "register_delta"
        result.quality = "ok"
        return result

    if wrap_ev or is_wrap_registers(start, end, scale, offset):
        result.phase_kwh = wrap_kwh(start, end, scale, offset)
        result.method = "wrap"
        result.quality = "ok"
        return result

    result.method = "none"
    result.quality = "untrusted"
    return result


def _round4(value: Optional[float]) -> Optional[float]:
    if value is None:
        return None
    return round(float(value), 4)


def reconcile_period(
    phase_rows: Dict[str, Sequence[MeterRow]],
    phase_events: Optional[Dict[str, Sequence[EnergyEvent]]] = None,
    t0_unix: int = 0,
    t1_unix: int = 0,
    invoice_kwh: Optional[float] = None,
    pln_register_t0: Optional[float] = None,
    pln_register_t1: Optional[float] = None,
) -> ReconcileResult:
    """
    Compare 3-phase register consumption between T0 and T1 to invoice kWh.
    Never multiplies one phase by 3. Does not apply rupiah tariffs.
    A hardware reset wipes that phase's T0→T1 bill (suffix is informational only).
    """
    phase_events = phase_events or {}
    result = ReconcileResult(
        invoice_kwh=_round4(invoice_kwh),
        pln_register_t0=_round4(pln_register_t0),
        pln_register_t1=_round4(pln_register_t1),
    )
    flags: List[str] = []

    for phase in PHASES:
        rows = list(phase_rows.get(phase) or [])
        events = list(phase_events.get(phase) or [])
        for row in rows:
            if row.energy_event in ("wrap", "reset"):
                events.append(
                    EnergyEvent(
                        phase=phase,
                        event_type=row.energy_event,
                        period_end_unix=row.period_end_unix,
                    )
                )
        phase_result = reconcile_phase(phase, rows, events, t0_unix, t1_unix)
        if phase_result.phase_kwh is not None:
            phase_result.phase_kwh = _round4(phase_result.phase_kwh)
        if phase_result.suffix_kwh is not None:
            phase_result.suffix_kwh = _round4(phase_result.suffix_kwh)
        result.phases[phase] = phase_result
        if phase_result.quality == "incomplete":
            flags.append(f"missing_phase:{phase}")
        elif phase_result.quality == "untrusted":
            flags.append(f"untrusted:{phase}")
        elif phase_result.quality == "degraded":
            flags.append(f"reset:{phase}")
        if phase_result.method == "wrap":
            flags.append(f"wrap:{phase}")

    qualities = [result.phases[p].quality for p in PHASES]
    if "incomplete" in qualities:
        result.quality = "incomplete"
    elif "untrusted" in qualities:
        result.quality = "untrusted"
    elif "degraded" in qualities:
        result.quality = "degraded"
    else:
        result.quality = "ok"

    complete_kwh = [result.phases[p].phase_kwh for p in PHASES]
    if all(v is not None for v in complete_kwh):
        result.total_kwh = _round4(sum(complete_kwh))  # type: ignore[arg-type]
        if invoice_kwh not in (None, 0, 0.0):
            result.error_pct = _round4(
                abs(result.total_kwh - float(invoice_kwh)) / float(invoice_kwh) * 100.0
            )
            if result.error_pct is not None and result.error_pct > ERROR_ALERT_PCT:
                flags.append("error_gt_5")

    start_regs = [result.phases[p].start_kwh for p in PHASES]
    end_regs = [result.phases[p].end_kwh for p in PHASES]
    if all(v is not None for v in start_regs):
        result.meter_sum_t0 = _round4(sum(start_regs))  # type: ignore[arg-type]
        if pln_register_t0 is not None:
            result.offset_t0 = _round4(float(pln_register_t0) - result.meter_sum_t0)
    if all(v is not None for v in end_regs):
        result.meter_sum_t1 = _round4(sum(end_regs))  # type: ignore[arg-type]
        if pln_register_t1 is not None:
            result.offset_t1 = _round4(float(pln_register_t1) - result.meter_sum_t1)

    result.flags = flags
    return result


def detect_phase_gaps(
    latest_by_phase: Dict[str, Optional[datetime]],
    now: datetime,
    gap_minutes: int = DEFAULT_GAP_MINUTES,
) -> List[str]:
    """Phases with no row for > N minutes while a sibling is still live."""
    live: List[str] = []
    stale: List[str] = []
    threshold = timedelta(minutes=gap_minutes)
    for phase in PHASES:
        seen = latest_by_phase.get(phase)
        if seen is None:
            stale.append(phase)
            continue
        if seen.tzinfo is None:
            seen = seen.replace(tzinfo=timezone.utc)
        now_cmp = now if now.tzinfo else now.replace(tzinfo=timezone.utc)
        if now_cmp - seen <= threshold:
            live.append(phase)
        else:
            stale.append(phase)
    if not live:
        return []
    return stale


def to_unix(dt: datetime) -> int:
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return int(dt.timestamp())

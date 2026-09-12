"""
PLN invoice kWh reconciliation from 3-phase PZEM meter registers.

Pure functions — no Flask, no tariff / rupiah math.
Firmware remains the source of the hardware register; this module only
applies T0→T1 register-delta, wrap, and degraded reset rules.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence

PHASES = ("R", "S", "T")
WRAP_REGISTER_MAX = 9999.99
WRAP_START_MIN = 9000.0
WRAP_END_MAX = 100.0
VALID_ACCUM_METHODS = frozenset({"counter_delta", "power_integration"})
DEFAULT_GAP_MINUTES = 20
ERROR_ALERT_PCT = 5.0


@dataclass
class MeterRow:
    phase: str
    meter_energy_kwh: float
    period_end_unix: int
    time_synced: bool = True
    accumulated_energy_kwh: Optional[float] = None
    energy_method: Optional[str] = None
    energy_event: Optional[str] = None


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
        return value
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
        accumulated_energy_kwh=_as_float(row.get("accumulated_energy_kwh")),
        energy_method=(str(row["energy_method"]).strip().lower() if row.get("energy_method") else None),
        energy_event=(str(row["energy_event"]).strip().lower() if row.get("energy_event") else None),
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


def is_wrap(start: float, end: float, wrap_events: Sequence[EnergyEvent]) -> bool:
    if wrap_events:
        return True
    return start >= WRAP_START_MIN and end <= WRAP_END_MAX


def wrap_kwh(start: float, end: float) -> float:
    return (WRAP_REGISTER_MAX - start) + end


def sum_accumulated(rows: Sequence[MeterRow], t0_unix: int, t1_unix: int) -> Optional[float]:
    total = 0.0
    counted = False
    for row in rows:
        if not (t0_unix < row.period_end_unix <= t1_unix):
            continue
        method = (row.energy_method or "").strip().lower()
        if method not in VALID_ACCUM_METHODS:
            continue
        if row.accumulated_energy_kwh is None:
            continue
        total += float(row.accumulated_energy_kwh)
        counted = True
    return total if counted else None


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

    wrap_ev = events_in_window(events, t0_unix, t1_unix, "wrap")
    reset_ev = events_in_window(events, t0_unix, t1_unix, "reset")

    if end >= start:
        result.phase_kwh = end - start
        result.method = "register_delta"
        result.quality = "ok"
        return result

    if is_wrap(start, end, wrap_ev):
        result.phase_kwh = wrap_kwh(start, end)
        result.method = "wrap"
        result.quality = "ok"
        return result

    if reset_ev:
        accumulated = sum_accumulated(rows, t0_unix, t1_unix)
        result.phase_kwh = accumulated
        result.method = "accumulated"
        result.quality = "degraded" if accumulated is not None else "untrusted"
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
        # Events encoded on the rows themselves also count
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

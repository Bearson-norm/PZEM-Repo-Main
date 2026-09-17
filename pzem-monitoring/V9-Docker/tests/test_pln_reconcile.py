from pln_reconcile import (
    EnergyEvent,
    MeterRow,
    detect_phase_gaps,
    reconcile_period,
    wrap_kwh,
)
from datetime import datetime, timedelta, timezone


def _row(phase, energy, ts, **kwargs):
    return MeterRow(
        phase=phase,
        meter_energy_kwh=energy,
        period_end_unix=ts,
        time_synced=kwargs.get("time_synced", True),
        energy_event=kwargs.get("energy_event"),
        energy_scale=kwargs.get("energy_scale"),
        energy_offset=kwargs.get("energy_offset"),
    )


def test_wrap_formula():
    assert round(wrap_kwh(9999.90, 0.20), 2) == 0.29


def test_wrap_9999_90_to_0_20():
    t0, t1 = 1_700_000_000, 1_700_000_000 + 3600
    rows = {
        "R": [
            _row("R", 9999.90, t0, energy_event="wrap"),
            _row("R", 0.20, t1, energy_event="wrap"),
        ],
        "S": [_row("S", 10.0, t0), _row("S", 12.0, t1)],
        "T": [_row("T", 20.0, t0), _row("T", 21.0, t1)],
    }
    events = {
        "R": [EnergyEvent("R", "wrap", t1)],
        "S": [],
        "T": [],
    }
    result = reconcile_period(rows, events, t0, t1, invoice_kwh=3.29)
    assert result.phases["R"].method == "wrap"
    assert result.phases["R"].quality == "ok"
    assert abs(result.phases["R"].phase_kwh - 0.29) < 0.001
    assert abs(result.phases["S"].phase_kwh - 2.0) < 0.001
    assert abs(result.phases["T"].phase_kwh - 1.0) < 0.001
    assert abs(result.total_kwh - 3.29) < 0.01
    assert "wrap:R" in result.flags


def test_wrap_heuristic_without_event():
    t0, t1 = 100, 200
    rows = {
        "R": [_row("R", 9999.50, t0), _row("R", 0.10, t1)],
        "S": [_row("S", 1.0, t0), _row("S", 1.0, t1)],
        "T": [_row("T", 1.0, t0), _row("T", 1.0, t1)],
    }
    result = reconcile_period(rows, {}, t0, t1)
    assert result.phases["R"].method == "wrap"
    assert abs(result.phases["R"].phase_kwh - ((9999.99 - 9999.50) + 0.10)) < 0.001


def test_calibrated_wrap_scale_not_one():
    t0, t1 = 100, 200
    scale, offset = 2.0, 0.0
    start, end = 18000.0, 50.0
    expected = wrap_kwh(start, end, scale, offset)
    rows = {
        "R": [
            _row("R", start, t0, energy_scale=scale, energy_offset=offset),
            _row("R", end, t1, energy_scale=scale, energy_offset=offset),
        ],
        "S": [_row("S", 1.0, t0), _row("S", 1.0, t1)],
        "T": [_row("T", 1.0, t0), _row("T", 1.0, t1)],
    }
    result = reconcile_period(rows, {}, t0, t1)
    assert result.phases["R"].method == "wrap"
    assert abs(result.phases["R"].phase_kwh - expected) < 0.001
    assert abs(expected - ((9999.99 * scale - start) + end)) < 0.001


def test_reset_wipes_series_no_window_sum():
    t0, t1 = 100, 400
    rows = {
        "R": [
            _row("R", 150.0, t0),
            _row("R", 0.5, 250, energy_event="reset"),
            _row("R", 0.9, t1),
        ],
        "S": [_row("S", 10.0, t0), _row("S", 11.0, t1)],
        "T": [_row("T", 20.0, t0), _row("T", 20.5, t1)],
    }
    events = {"R": [EnergyEvent("R", "reset", 250)], "S": [], "T": []}
    result = reconcile_period(rows, events, t0, t1, invoice_kwh=4.4)
    assert result.phases["R"].method == "reset_wipe"
    assert result.phases["R"].quality == "degraded"
    assert result.phases["R"].phase_kwh is None
    assert result.total_kwh is None
    assert result.error_pct is None
    assert result.quality == "degraded"
    assert "reset:R" in result.flags


def test_reset_does_not_use_end_minus_start():
    t0, t1 = 100, 200
    rows = {
        "R": [
            _row("R", 150.0, t0),
            _row("R", 0.5, t1, energy_event="reset"),
        ],
        "S": [_row("S", 1.0, t0), _row("S", 1.0, t1)],
        "T": [_row("T", 1.0, t0), _row("T", 1.0, t1)],
    }
    result = reconcile_period(rows, {"R": [EnergyEvent("R", "reset", t1)]}, t0, t1)
    assert result.phases["R"].phase_kwh is None
    assert result.phases["R"].phase_kwh != (0.5 - 150.0)
    assert result.phases["R"].method == "reset_wipe"


def test_reset_suffix_not_included_in_total():
    t0, t1 = 100, 400
    rows = {
        "R": [
            _row("R", 150.0, t0),
            _row("R", 0.5, 250, energy_event="reset"),
            _row("R", 0.5, 260),
            _row("R", 1.2, t1),
        ],
        "S": [_row("S", 10.0, t0), _row("S", 11.0, t1)],
        "T": [_row("T", 20.0, t0), _row("T", 20.5, t1)],
    }
    result = reconcile_period(
        rows, {"R": [EnergyEvent("R", "reset", 250)]}, t0, t1, invoice_kwh=10
    )
    assert result.phases["R"].phase_kwh is None
    assert result.total_kwh is None
    assert abs(result.phases["R"].suffix_kwh - 0.7) < 0.001
    assert result.phases["R"].suffix_start_unix == 260


def test_drop_not_near_wrap_is_reset_wipe_not_negative_delta():
    t0, t1 = 100, 200
    rows = {
        "R": [_row("R", 500.0, t0), _row("R", 10.0, t1)],
        "S": [_row("S", 1.0, t0), _row("S", 1.0, t1)],
        "T": [_row("T", 1.0, t0), _row("T", 1.0, t1)],
    }
    result = reconcile_period(rows, {}, t0, t1)
    assert result.phases["R"].method == "reset_wipe"
    assert result.phases["R"].quality == "degraded"
    assert result.phases["R"].phase_kwh is None
    assert result.quality == "degraded"


def test_missing_s_phase_incomplete_no_invented_data():
    t0, t1 = 100, 200
    rows = {
        "R": [_row("R", 10.0, t0), _row("R", 12.0, t1)],
        "S": [],
        "T": [_row("T", 5.0, t0), _row("T", 6.0, t1)],
    }
    result = reconcile_period(rows, {}, t0, t1, invoice_kwh=10)
    assert result.phases["S"].quality == "incomplete"
    assert result.phases["S"].phase_kwh is None
    assert result.quality == "incomplete"
    assert result.total_kwh is None
    assert result.error_pct is None
    assert "missing_phase:S" in result.flags


def test_unsynced_unix_zero_excluded_from_bounds():
    t0, t1 = 100, 200
    rows = {
        "R": [
            _row("R", 10.0, 0, time_synced=False),
            _row("R", 11.0, t0),
            _row("R", 13.0, t1),
        ],
        "S": [_row("S", 1.0, t0), _row("S", 1.0, t1)],
        "T": [_row("T", 1.0, t0), _row("T", 1.0, t1)],
    }
    result = reconcile_period(rows, {}, t0, t1)
    assert result.phases["R"].start_kwh == 11.0
    assert result.phases["R"].end_kwh == 13.0
    assert abs(result.phases["R"].phase_kwh - 2.0) < 0.001


def test_normal_path_uses_register_delta_not_window_sum():
    t0, t1 = 100, 400
    rows = {
        "R": [
            _row("R", 100.0, t0),
            _row("R", 105.0, 250),
            _row("R", 110.0, t1),
        ],
        "S": [_row("S", 200.0, t0), _row("S", 205.0, t1)],
        "T": [_row("T", 300.0, t0), _row("T", 302.0, t1)],
    }
    result = reconcile_period(rows, {}, t0, t1, invoice_kwh=17.0)
    assert result.phases["R"].method == "register_delta"
    assert abs(result.phases["R"].phase_kwh - 10.0) < 0.001
    assert abs(result.total_kwh - 17.0) < 0.001
    assert result.error_pct == 0.0
    assert result.quality == "ok"


def test_three_phases_summed_never_times_three():
    t0, t1 = 100, 200
    rows = {
        "R": [_row("R", 1.0, t0), _row("R", 2.0, t1)],
        "S": [_row("S", 1.0, t0), _row("S", 2.0, t1)],
        "T": [_row("T", 1.0, t0), _row("T", 2.0, t1)],
    }
    result = reconcile_period(rows, {}, t0, t1)
    assert abs(result.total_kwh - 3.0) < 0.001
    assert result.total_kwh != 1.0 * 3 * 3


def test_invoice_omitted_skips_error_pct():
    t0, t1 = 100, 200
    rows = {
        "R": [_row("R", 1.0, t0), _row("R", 2.0, t1)],
        "S": [_row("S", 1.0, t0), _row("S", 2.0, t1)],
        "T": [_row("T", 1.0, t0), _row("T", 2.0, t1)],
    }
    result = reconcile_period(rows, {}, t0, t1)
    assert result.total_kwh == 3.0
    assert result.error_pct is None


def test_error_pct_above_5_is_reported_not_fudged():
    t0, t1 = 100, 200
    rows = {
        "R": [_row("R", 0.0, t0), _row("R", 10.0, t1)],
        "S": [_row("S", 0.0, t0), _row("S", 10.0, t1)],
        "T": [_row("T", 0.0, t0), _row("T", 10.0, t1)],
    }
    result = reconcile_period(rows, {}, t0, t1, invoice_kwh=20.0)
    assert result.total_kwh == 30.0
    assert abs(result.error_pct - 50.0) < 0.01
    assert "error_gt_5" in result.flags


def test_pln_register_offset():
    t0, t1 = 100, 200
    rows = {
        "R": [_row("R", 10.0, t0), _row("R", 11.0, t1)],
        "S": [_row("S", 20.0, t0), _row("S", 21.0, t1)],
        "T": [_row("T", 30.0, t0), _row("T", 31.0, t1)],
    }
    result = reconcile_period(
        rows, {}, t0, t1, pln_register_t0=100.0, pln_register_t1=103.0
    )
    assert result.meter_sum_t0 == 60.0
    assert result.meter_sum_t1 == 63.0
    assert result.offset_t0 == 40.0
    assert result.offset_t1 == 40.0


def test_gap_only_when_sibling_live():
    now = datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc)
    latest = {
        "R": now - timedelta(minutes=2),
        "S": now - timedelta(minutes=45),
        "T": now - timedelta(minutes=1),
    }
    assert detect_phase_gaps(latest, now, gap_minutes=20) == ["S"]


def test_gap_none_when_all_stale():
    now = datetime(2026, 3, 1, 12, 0, tzinfo=timezone.utc)
    latest = {
        "R": now - timedelta(hours=2),
        "S": now - timedelta(hours=2),
        "T": now - timedelta(hours=2),
    }
    assert detect_phase_gaps(latest, now, gap_minutes=20) == []

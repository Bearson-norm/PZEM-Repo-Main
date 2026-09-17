"""APIs and operator page for PLN invoice kWh matching (not rupiah)."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, List, Optional

import pytz
from flask import Blueprint, current_app, jsonify, render_template, request
from psycopg2.extras import Json, RealDictCursor

from pln_reconcile import (
    DEFAULT_GAP_MINUTES,
    EnergyEvent,
    PHASES,
    detect_phase_gaps,
    meter_row_from_mapping,
    reconcile_period,
    to_unix,
)

logger = logging.getLogger(__name__)
JAKARTA = pytz.timezone("Asia/Jakarta")

pln_match_bp = Blueprint("pln_match", __name__)


def _db():
    return current_app.config["DB_MANAGER"]


def _gap_minutes() -> int:
    try:
        return int(os.getenv("PLN_GAP_MINUTES", DEFAULT_GAP_MINUTES))
    except (TypeError, ValueError):
        return DEFAULT_GAP_MINUTES


def _jsonable(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            value = pytz.UTC.localize(value)
        return value.astimezone(JAKARTA).isoformat()
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    return value


def _parse_read_at(raw: Any) -> datetime:
    if isinstance(raw, datetime):
        dt = raw
    else:
        text = str(raw or "").strip()
        if not text:
            raise ValueError("read_at is required")
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            dt = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ValueError("read_at must be ISO-8601") from exc
    if dt.tzinfo is None:
        dt = JAKARTA.localize(dt)
    return dt.astimezone(timezone.utc)


def _reading_row(row: Dict[str, Any]) -> Dict[str, Any]:
    return _jsonable(dict(row))


@pln_match_bp.route("/pln-match")
def pln_match_page():
    return render_template("pln_bill_match.html")


@pln_match_bp.route("/api/pln-buildings", methods=["GET"])
def list_buildings():
    try:
        with _db().pool_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT building FROM (
                        SELECT DISTINCT building AS building FROM pzem_data
                        WHERE building IS NOT NULL AND TRIM(building) <> ''
                        UNION
                        SELECT DISTINCT location FROM pzem_devices
                        WHERE location IS NOT NULL AND TRIM(location) <> ''
                        UNION
                        SELECT DISTINCT building FROM pln_readings
                        WHERE building IS NOT NULL AND TRIM(building) <> ''
                    ) s
                    ORDER BY building
                    """
                )
                buildings = [r[0] for r in cur.fetchall()]
        return jsonify({"buildings": buildings})
    except Exception as e:
        logger.exception("list_buildings: %s", e)
        return jsonify({"error": str(e)}), 500


@pln_match_bp.route("/api/pln-readings", methods=["GET"])
def list_readings():
    building = (request.args.get("building") or "").strip()
    try:
        with _db().pool_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if building:
                    cur.execute(
                        """
                        SELECT id, building, read_at, pln_register_kwh, invoice_kwh, notes, created_at
                        FROM pln_readings
                        WHERE building = %s
                        ORDER BY read_at DESC
                        """,
                        (building,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT id, building, read_at, pln_register_kwh, invoice_kwh, notes, created_at
                        FROM pln_readings
                        ORDER BY read_at DESC
                        LIMIT 200
                        """
                    )
                rows = [_reading_row(dict(r)) for r in cur.fetchall()]
        return jsonify({"readings": rows})
    except Exception as e:
        logger.exception("list_readings: %s", e)
        return jsonify({"error": str(e)}), 500


@pln_match_bp.route("/api/pln-readings", methods=["POST"])
def create_reading():
    body = request.get_json(silent=True) or {}
    building = str(body.get("building") or "").strip()
    if not building:
        return jsonify({"error": "building is required"}), 400
    try:
        read_at = _parse_read_at(body.get("read_at"))
        pln_register = float(body.get("pln_register_kwh"))
    except (TypeError, ValueError) as exc:
        return jsonify({"error": str(exc)}), 400
    invoice = body.get("invoice_kwh")
    invoice_kwh = None if invoice in (None, "") else float(invoice)
    notes = body.get("notes")
    notes = str(notes).strip() if notes not in (None, "") else None

    try:
        with _db().pool_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO pln_readings (building, read_at, pln_register_kwh, invoice_kwh, notes)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id, building, read_at, pln_register_kwh, invoice_kwh, notes, created_at
                    """,
                    (building, read_at, pln_register, invoice_kwh, notes),
                )
                created = dict(cur.fetchone())
                prev = _previous_reading(cur, building, created["id"], created["read_at"])
            conn.commit()
            recon = None
            if prev:
                recon = _run_and_store(conn, building, prev, created)
        payload = {"reading": _reading_row(created)}
        if recon:
            payload["reconciliation"] = recon
        return jsonify(payload), 201
    except Exception as e:
        logger.exception("create_reading: %s", e)
        return jsonify({"error": str(e)}), 500


@pln_match_bp.route("/api/pln-readings/<int:reading_id>", methods=["DELETE"])
def delete_reading(reading_id: int):
    try:
        with _db().pool_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM pln_readings WHERE id = %s RETURNING id", (reading_id,))
                deleted = cur.fetchone()
            conn.commit()
        if not deleted:
            return jsonify({"error": "not found"}), 404
        return jsonify({"ok": True, "id": reading_id})
    except Exception as e:
        logger.exception("delete_reading: %s", e)
        return jsonify({"error": str(e)}), 500


@pln_match_bp.route("/api/pln-reconcile", methods=["GET"])
def get_reconcile():
    building = (request.args.get("building") or "").strip()
    try:
        with _db().pool_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                if building:
                    cur.execute(
                        """
                        SELECT * FROM pln_reconciliations
                        WHERE building = %s
                        ORDER BY created_at DESC
                        LIMIT 20
                        """,
                        (building,),
                    )
                else:
                    cur.execute(
                        """
                        SELECT * FROM pln_reconciliations
                        ORDER BY created_at DESC
                        LIMIT 20
                        """
                    )
                rows = [_jsonable(dict(r)) for r in cur.fetchall()]
        return jsonify({"reconciliations": rows})
    except Exception as e:
        logger.exception("get_reconcile: %s", e)
        return jsonify({"error": str(e)}), 500


@pln_match_bp.route("/api/pln-reconcile", methods=["POST"])
def post_reconcile():
    body = request.get_json(silent=True) or {}
    building = str(body.get("building") or "").strip()
    try:
        with _db().pool_connection() as conn:
            t0, t1 = _resolve_pair(conn, body, building)
            if t0["building"] != t1["building"]:
                return jsonify({"error": "readings must belong to the same building"}), 400
            building = t0["building"]
            stored = _run_and_store(conn, building, t0, t1)
        return jsonify(stored)
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400
    except Exception as e:
        logger.exception("post_reconcile: %s", e)
        return jsonify({"error": str(e)}), 500


@pln_match_bp.route("/api/pln-quality", methods=["GET"])
def get_quality():
    building = (request.args.get("building") or "").strip()
    gap_minutes = _gap_minutes()
    now = datetime.now(timezone.utc)
    try:
        with _db().pool_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                buildings = [building] if building else _distinct_buildings(cur)
                report = []
                for bld in buildings:
                    latest = _latest_phase_times(cur, bld)
                    gaps = detect_phase_gaps(latest, now, gap_minutes)
                    events = _recent_events(cur, bld)
                    last_reading = _latest_reading(cur, bld)
                    unsynced = []
                    missing = []
                    if last_reading:
                        t_unix = to_unix(last_reading["read_at"])
                        for phase in PHASES:
                            bound = _bound_at_or_after(cur, bld, phase, t_unix)
                            if bound is None:
                                missing.append(phase)
                            elif not bound.get("time_synced"):
                                unsynced.append(phase)
                    heartbeats = _heartbeats(cur, bld)
                    report.append(
                        {
                            "building": bld,
                            "gaps": gaps,
                            "wraps": [e for e in events if e["event_type"] == "wrap"],
                            "resets": [e for e in events if e["event_type"] == "reset"],
                            "unsynced_at_reading": unsynced,
                            "missing_phase_at_reading": missing,
                            "latest_by_phase": {
                                p: (_jsonable(latest[p]) if latest.get(p) else None)
                                for p in PHASES
                            },
                            "heartbeats": heartbeats,
                            "gap_minutes": gap_minutes,
                        }
                    )
        return jsonify({"quality": report})
    except Exception as e:
        logger.exception("get_quality: %s", e)
        return jsonify({"error": str(e)}), 500


def _resolve_pair(conn, body: Dict[str, Any], building: str):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        t0_id = body.get("t0_id")
        t1_id = body.get("t1_id")
        if t0_id and t1_id:
            t0 = _get_reading(cur, int(t0_id))
            t1 = _get_reading(cur, int(t1_id))
            return t0, t1
        if body.get("t0_read_at") and body.get("t1_read_at"):
            if not building:
                raise ValueError("building is required when using read_at")
            t0 = _get_reading_at(cur, building, _parse_read_at(body["t0_read_at"]))
            t1 = _get_reading_at(cur, building, _parse_read_at(body["t1_read_at"]))
            return t0, t1
        if building:
            cur.execute(
                """
                SELECT id, building, read_at, pln_register_kwh, invoice_kwh, notes
                FROM pln_readings
                WHERE building = %s
                ORDER BY read_at DESC
                LIMIT 2
                """,
                (building,),
            )
            rows = [dict(r) for r in cur.fetchall()]
            if len(rows) < 2:
                raise ValueError("need at least two readings for this building")
            t1, t0 = rows[0], rows[1]
            return t0, t1
    raise ValueError("provide t0_id and t1_id, or building")


def _get_reading(cur, reading_id: int) -> Dict[str, Any]:
    cur.execute(
        """
        SELECT id, building, read_at, pln_register_kwh, invoice_kwh, notes
        FROM pln_readings WHERE id = %s
        """,
        (reading_id,),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError(f"reading {reading_id} not found")
    return dict(row)


def _get_reading_at(cur, building: str, read_at: datetime) -> Dict[str, Any]:
    cur.execute(
        """
        SELECT id, building, read_at, pln_register_kwh, invoice_kwh, notes
        FROM pln_readings
        WHERE building = %s AND read_at = %s
        """,
        (building, read_at),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError("reading not found for that building / read_at")
    return dict(row)


def _previous_reading(cur, building: str, current_id: int, read_at: datetime):
    cur.execute(
        """
        SELECT id, building, read_at, pln_register_kwh, invoice_kwh, notes
        FROM pln_readings
        WHERE building = %s AND read_at < %s AND id <> %s
        ORDER BY read_at DESC
        LIMIT 1
        """,
        (building, read_at, current_id),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def _aware(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return pytz.UTC.localize(dt)
    return dt


def _run_and_store(conn, building: str, t0: Dict[str, Any], t1: Dict[str, Any]) -> Dict[str, Any]:
    t0_at = _aware(t0["read_at"])
    t1_at = _aware(t1["read_at"])
    if t1_at <= t0_at:
        raise ValueError("T1 must be after T0")
    t0_unix = to_unix(t0_at)
    t1_unix = to_unix(t1_at)

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        phase_rows: Dict[str, List] = {}
        phase_events: Dict[str, List] = {}
        for phase in PHASES:
            cur.execute(
                """
                SELECT meter_energy_kwh, energy, period_end_unix, time_synced,
                       energy_event, energy_scale, energy_offset
                FROM pzem_data
                WHERE building = %s AND UPPER(phase) = %s
                  AND period_end_unix IS NOT NULL
                ORDER BY period_end_unix ASC
                """,
                (building, phase),
            )
            rows = []
            for raw in cur.fetchall():
                mapped = meter_row_from_mapping(phase, dict(raw))
                if mapped:
                    rows.append(mapped)
            phase_rows[phase] = rows
            cur.execute(
                """
                SELECT phase, event_type, period_end_unix
                FROM pzem_energy_events
                WHERE building = %s AND UPPER(phase) = %s
                  AND period_end_unix > %s AND period_end_unix <= %s
                """,
                (building, phase, t0_unix, t1_unix),
            )
            phase_events[phase] = [
                EnergyEvent(
                    phase=phase,
                    event_type=str(r["event_type"]),
                    period_end_unix=int(r["period_end_unix"]),
                )
                for r in cur.fetchall()
                if r.get("period_end_unix")
            ]

        result = reconcile_period(
            phase_rows,
            phase_events,
            t0_unix,
            t1_unix,
            invoice_kwh=_as_opt_float(t1.get("invoice_kwh")),
            pln_register_t0=_as_opt_float(t0.get("pln_register_kwh")),
            pln_register_t1=_as_opt_float(t1.get("pln_register_kwh")),
        )
        payload = result.to_dict()
        cur.execute(
            """
            INSERT INTO pln_reconciliations (
                building, t0_reading_id, t1_reading_id, quality,
                total_kwh, invoice_kwh, error_pct,
                meter_sum_t0, meter_sum_t1, pln_register_t0, pln_register_t1,
                offset_t0, offset_t1, phases_json, flags_json
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            ON CONFLICT (t0_reading_id, t1_reading_id) DO UPDATE SET
                quality = EXCLUDED.quality,
                total_kwh = EXCLUDED.total_kwh,
                invoice_kwh = EXCLUDED.invoice_kwh,
                error_pct = EXCLUDED.error_pct,
                meter_sum_t0 = EXCLUDED.meter_sum_t0,
                meter_sum_t1 = EXCLUDED.meter_sum_t1,
                pln_register_t0 = EXCLUDED.pln_register_t0,
                pln_register_t1 = EXCLUDED.pln_register_t1,
                offset_t0 = EXCLUDED.offset_t0,
                offset_t1 = EXCLUDED.offset_t1,
                phases_json = EXCLUDED.phases_json,
                flags_json = EXCLUDED.flags_json,
                created_at = CURRENT_TIMESTAMP
            RETURNING *
            """,
            (
                building,
                t0["id"],
                t1["id"],
                result.quality,
                result.total_kwh,
                result.invoice_kwh,
                result.error_pct,
                result.meter_sum_t0,
                result.meter_sum_t1,
                result.pln_register_t0,
                result.pln_register_t1,
                result.offset_t0,
                result.offset_t1,
                Json(payload["phases"]),
                Json(payload["flags"]),
            ),
        )
        stored = dict(cur.fetchone())
    conn.commit()
    out = _jsonable(stored)
    out["t0"] = _reading_row(t0)
    out["t1"] = _reading_row(t1)
    return out


def _as_opt_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    return float(value)


def _distinct_buildings(cur) -> List[str]:
    cur.execute(
        """
        SELECT DISTINCT building FROM pzem_data
        WHERE building IS NOT NULL AND TRIM(building) <> ''
        ORDER BY building
        """
    )
    return [r["building"] for r in cur.fetchall()]


def _latest_phase_times(cur, building: str) -> Dict[str, Optional[datetime]]:
    latest: Dict[str, Optional[datetime]] = {p: None for p in PHASES}
    cur.execute(
        """
        SELECT UPPER(phase) AS phase, MAX(created_at) AS last_seen
        FROM pzem_data
        WHERE building = %s AND phase IS NOT NULL
        GROUP BY UPPER(phase)
        """,
        (building,),
    )
    for row in cur.fetchall():
        phase = str(row["phase"] or "").upper()
        if phase in latest:
            latest[phase] = row["last_seen"]
    return latest


def _recent_events(cur, building: str) -> List[Dict[str, Any]]:
    cur.execute(
        """
        SELECT phase, event_type, period_end_unix, meter_energy_kwh, created_at
        FROM pzem_energy_events
        WHERE building = %s
        ORDER BY COALESCE(period_end_unix, 0) DESC
        LIMIT 50
        """,
        (building,),
    )
    return [_jsonable(dict(r)) for r in cur.fetchall()]


def _latest_reading(cur, building: str):
    cur.execute(
        """
        SELECT id, building, read_at, pln_register_kwh, invoice_kwh
        FROM pln_readings
        WHERE building = %s
        ORDER BY read_at DESC
        LIMIT 1
        """,
        (building,),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def _bound_at_or_after(cur, building: str, phase: str, t_unix: int):
    cur.execute(
        """
        SELECT meter_energy_kwh, period_end_unix, time_synced
        FROM pzem_data
        WHERE building = %s AND UPPER(phase) = %s
          AND period_end_unix >= %s AND period_end_unix > 0
        ORDER BY period_end_unix ASC
        LIMIT 1
        """,
        (building, phase, t_unix),
    )
    row = cur.fetchone()
    return dict(row) if row else None


def _heartbeats(cur, building: str) -> List[Dict[str, Any]]:
    cur.execute(
        """
        SELECT building, phase, pzem_connected, buffer_count, pzem_read_errors, seen_at
        FROM pzem_device_heartbeat
        WHERE building = %s
        ORDER BY phase
        """,
        (building,),
    )
    return [_jsonable(dict(r)) for r in cur.fetchall()]

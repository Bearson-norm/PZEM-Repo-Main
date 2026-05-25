"""Canvas snapshot: filter latest pzem_data per canvas_definitions.config."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from psycopg2.extras import RealDictCursor

from electric_formulas import (
    aggregate_rows_single_meter,
    aggregate_rows_three_pzem,
    derive_phase_from_row,
)

logger = logging.getLogger(__name__)


def _cfg_list(cfg: Dict[str, Any], key: str) -> List[Any]:
    v = cfg.get(key) or []
    if isinstance(v, str) and v.strip():
        return [v.strip()]
    if not isinstance(v, list):
        return []
    return v


def _tunnel_names_from_block(block: Dict[str, Any]) -> List[str]:
    """Nama tunnel = mqtt_bridge_configs.name (satu tunnel per baris bridge)."""
    raw = block.get("tunnel_names")
    if raw is None:
        return []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    return [str(x).strip() for x in raw if x is not None and str(x).strip()]


def resolve_tunnel_names_to_ids(
    conn, names: List[str]
) -> tuple[List[int], List[str]]:
    """Return (ids ordered by names given, missing_names)."""
    if not names:
        return [], []
    names = [n.strip() for n in names if n and str(n).strip()]
    if not names:
        return [], []
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            "SELECT id, name FROM mqtt_bridge_configs WHERE name = ANY(%s)",
            (names,),
        )
        found = {row["name"]: int(row["id"]) for row in cur.fetchall()}
    ids: List[int] = []
    missing: List[str] = []
    for n in names:
        if n in found:
            ids.append(found[n])
        else:
            missing.append(n)
    return ids, missing


def effective_bridge_ids(
    conn, block: Dict[str, Any]
) -> tuple[Optional[List[int]], List[str]]:
    """
    Gabungkan mqtt_bridge_config_ids eksplisit + resolusi tunnel_names.
    Jika tidak ada filter bridge sama sekali → (None, []).
    Jika tunnel_names diminta tapi semua invalid → ([], missing) untuk kosongkan hasil.
    """
    explicit = []
    for x in _cfg_list(block, "mqtt_bridge_config_ids"):
        try:
            explicit.append(int(x))
        except (TypeError, ValueError):
            continue
    tnames = _tunnel_names_from_block(block)
    resolved, missing = resolve_tunnel_names_to_ids(conn, tnames)
    merged: List[int] = []
    seen = set()
    for i in explicit + resolved:
        if i not in seen:
            seen.add(i)
            merged.append(i)
    if tnames and not resolved:
        return [], missing
    if missing:
        logger.warning("Canvas tunnel_names tidak ditemukan di DB: %s", missing)
    if merged:
        return merged, missing
    if explicit:
        return explicit, missing
    return None, missing


def _phase_ok(row: Dict[str, Any], phases: List[str]) -> bool:
    if not phases:
        return True
    ph = derive_phase_from_row(row)
    if ph is None:
        return True
    return ph.upper() in {p.upper() for p in phases}


def fetch_latest_filtered_rows(
    conn,
    mqtt_bridge_config_ids: Optional[List[int]] = None,
    buildings: Optional[List[str]] = None,
    device_addresses: Optional[List[str]] = None,
) -> List[Dict[str, Any]]:
    """Distinct ON device_address latest row, optional filters.

    mqtt_bridge_config_ids:
      None → tanpa filter bridge
      [] → tidak ada baris yang cocok (mis. nama tunnel tidak ada)
      [id,...] → filter IN ids
    """
    buildings = buildings or []
    device_addresses = device_addresses or []

    base = """
    SELECT DISTINCT ON (d.device_address)
        d.device_address,
        d.voltage,
        d.current,
        d.power,
        d.energy,
        d.frequency,
        d.power_factor,
        d.created_at,
        d.mqtt_bridge_config_id,
        m.name AS bridge_name,
        COALESCE(dm.location, 'Unknown') AS location,
        COALESCE(dm.device_name, 'Device ' || d.device_address) AS device_name
    FROM pzem_data d
    LEFT JOIN mqtt_bridge_configs m ON d.mqtt_bridge_config_id = m.id
    LEFT JOIN pzem_devices dm ON d.device_address = dm.device_address
    WHERE 1 = 1
    """
    params: List[Any] = []

    if mqtt_bridge_config_ids is not None:
        if len(mqtt_bridge_config_ids) == 0:
            base += " AND FALSE"
        else:
            base += " AND d.mqtt_bridge_config_id = ANY(%s)"
            params.append(mqtt_bridge_config_ids)

    if buildings:
        base += " AND dm.location = ANY(%s)"
        params.append(buildings)

    if device_addresses:
        base += " AND d.device_address = ANY(%s)"
        params.append(device_addresses)

    base += " ORDER BY d.device_address, d.created_at DESC"

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(base, params)
        rows = cur.fetchall()
    return [dict(r) for r in rows]


def _serialize_row(r: Dict[str, Any]) -> Dict[str, Any]:
    def dt(x):
        if isinstance(x, datetime):
            return x.isoformat()
        return x

    return {
        "device_address": r.get("device_address"),
        "voltage": float(r["voltage"]) if r.get("voltage") is not None else None,
        "current": float(r["current"]) if r.get("current") is not None else None,
        "power": float(r["power"]) if r.get("power") is not None else None,
        "energy": float(r["energy"]) if r.get("energy") is not None else None,
        "frequency": float(r["frequency"]) if r.get("frequency") is not None else None,
        "power_factor": float(r["power_factor"]) if r.get("power_factor") is not None else None,
        "mqtt_bridge_config_id": r.get("mqtt_bridge_config_id"),
        "bridge_name": r.get("bridge_name"),
        "location": r.get("location"),
        "device_name": r.get("device_name"),
        "phase": derive_phase_from_row(r),
        "created_at": dt(r.get("created_at")),
    }


def build_snapshot(db_manager, canvas_row: Dict[str, Any]) -> Dict[str, Any]:
    """Build API response dict for one canvas definition."""
    cid = canvas_row["id"]
    cname = canvas_row["name"]
    ctype = canvas_row["type"]
    cfg = canvas_row.get("config") or {}
    if isinstance(cfg, str):
        import json

        cfg = json.loads(cfg)

    display = cfg.get("display") or {}
    formula = cfg.get("formula_profile") or "three_pzem_sum"
    all_warnings: List[str] = []

    with db_manager.pool_connection() as conn:
        if ctype == "compare_buildings":
            comp = cfg.get("compare") or {}
            side_a = comp.get("a") or {}
            side_b = comp.get("b") or {}
            ids_a, miss_a = effective_bridge_ids(conn, side_a)
            ids_b, miss_b = effective_bridge_ids(conn, side_b)
            for m in miss_a:
                all_warnings.append(f"Tunnel tidak ditemukan (sisi A): {m}")
            for m in miss_b:
                all_warnings.append(f"Tunnel tidak ditemukan (sisi B): {m}")
            rows_a = fetch_latest_filtered_rows(
                conn,
                ids_a,
                _cfg_list(side_a, "buildings") or None,
                _cfg_list(side_a, "device_addresses") or None,
            )
            rows_b = fetch_latest_filtered_rows(
                conn,
                ids_b,
                _cfg_list(side_b, "buildings") or None,
                _cfg_list(side_b, "device_addresses") or None,
            )
            phases_a = _cfg_list(side_a, "phases")
            phases_b = _cfg_list(side_b, "phases")
            rows_a = [r for r in rows_a if _phase_ok(r, phases_a)]
            rows_b = [r for r in rows_b if _phase_ok(r, phases_b)]

            fa = (
                side_a.get("formula_profile")
                or formula
                or "three_pzem_sum"
            )
            fb = (
                side_b.get("formula_profile")
                or formula
                or "three_pzem_sum"
            )
            if str(fa).lower() in ("auto", ""):
                agg_a = (
                    aggregate_rows_three_pzem(rows_a)
                    if len(rows_a) > 1
                    else aggregate_rows_single_meter(rows_a)
                )
            elif "three" in str(fa):
                agg_a = aggregate_rows_three_pzem(rows_a)
            else:
                agg_a = aggregate_rows_single_meter(rows_a)
            if str(fb).lower() in ("auto", ""):
                agg_b = (
                    aggregate_rows_three_pzem(rows_b)
                    if len(rows_b) > 1
                    else aggregate_rows_single_meter(rows_b)
                )
            elif "three" in str(fb):
                agg_b = aggregate_rows_three_pzem(rows_b)
            else:
                agg_b = aggregate_rows_single_meter(rows_b)

            return {
                "canvas_id": cid,
                "canvas_name": cname,
                "type": ctype,
                "as_of": datetime.utcnow().isoformat() + "Z",
                "display": display,
                "warnings": all_warnings,
                "compare": {
                    "a": {
                        "sources": [_serialize_row(r) for r in rows_a],
                        "aggregates": agg_a,
                        "tunnel_names": _tunnel_names_from_block(side_a),
                        "label": (display.get("labels") or {}).get("a", "A"),
                    },
                    "b": {
                        "sources": [_serialize_row(r) for r in rows_b],
                        "aggregates": agg_b,
                        "tunnel_names": _tunnel_names_from_block(side_b),
                        "label": (display.get("labels") or {}).get("b", "B"),
                    },
                },
            }

        ids_main, miss_main = effective_bridge_ids(conn, cfg)
        for m in miss_main:
            all_warnings.append(f"Tunnel tidak ditemukan: {m}")
        rows = fetch_latest_filtered_rows(
            conn,
            ids_main,
            _cfg_list(cfg, "buildings") or None,
            _cfg_list(cfg, "device_addresses") or None,
        )
        phases = _cfg_list(cfg, "phases")
        rows = [r for r in rows if _phase_ok(r, phases)]

        if str(formula).lower() in ("auto", ""):
            aggregates = (
                aggregate_rows_three_pzem(rows)
                if len(rows) > 1
                else aggregate_rows_single_meter(rows)
            )
        elif "single" in str(formula):
            aggregates = aggregate_rows_single_meter(rows)
        else:
            aggregates = aggregate_rows_three_pzem(rows)

        return {
            "canvas_id": cid,
            "canvas_name": cname,
            "type": ctype,
            "as_of": datetime.utcnow().isoformat() + "Z",
            "display": display,
            "warnings": all_warnings,
            "tunnel_names": _tunnel_names_from_block(cfg),
            "sources": [_serialize_row(r) for r in rows],
            "aggregates": aggregates,
        }


_CHART_PERIOD_CONFIG = {
    "hour": {
        "interval": "1 hour",
        "group_by": "DATE_TRUNC('minute', created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Jakarta')",
        "max_points": 60,
    },
    "day": {
        "interval": "1 day",
        "group_by": "DATE_TRUNC('minute', created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Jakarta')",
        "max_points": 96,
    },
    "week": {
        "interval": "1 week",
        "group_by": "DATE_TRUNC('hour', created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Jakarta')",
        "max_points": 168,
    },
    "month": {
        "interval": "1 month",
        "group_by": "DATE_TRUNC('hour', created_at AT TIME ZONE 'UTC' AT TIME ZONE 'Asia/Jakarta')",
        "max_points": 120,
    },
}

_VALID_CHART_METRICS = frozenset({"power", "voltage", "current", "energy"})


def _parse_canvas_config(cfg: Any) -> Dict[str, Any]:
    if isinstance(cfg, str):
        import json

        try:
            return json.loads(cfg)
        except json.JSONDecodeError:
            return {}
    return cfg or {}


def _chart_metric_sql(metric: str) -> str:
    if metric == "energy":
        return "MAX(energy) - MIN(energy)"
    return f"AVG({metric})"


def fetch_device_chart_series(
    conn,
    device_address: str,
    period: str,
    metric: str,
    mqtt_bridge_config_ids: Optional[List[int]] = None,
) -> List[Dict[str, Any]]:
    """Aggregated time series for one device, optionally filtered by bridge."""
    period = (period or "hour").strip().lower()
    if period not in _CHART_PERIOD_CONFIG:
        period = "hour"
    metric = (metric or "power").strip().lower()
    if metric not in _VALID_CHART_METRICS:
        metric = "power"

    config = _CHART_PERIOD_CONFIG[period]
    metric_expr = _chart_metric_sql(metric)

    query = f"""
    SELECT
        {config['group_by']} AS time_period,
        {metric_expr} AS value,
        COUNT(*) AS sample_count
    FROM pzem_data
    WHERE device_address = %s
    AND created_at >= NOW() - INTERVAL '{config['interval']}'
    """
    params: List[Any] = [device_address]

    if mqtt_bridge_config_ids is not None:
        if len(mqtt_bridge_config_ids) == 0:
            return []
        query += " AND mqtt_bridge_config_id = ANY(%s)"
        params.append(mqtt_bridge_config_ids)

    query += """
    GROUP BY time_period
    HAVING COUNT(*) > 0
    ORDER BY time_period ASC
    """

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(query, params)
        rows = cur.fetchall()

    data = [dict(r) for r in rows]
    if len(data) > config["max_points"]:
        step = max(1, len(data) // config["max_points"])
        data = data[::step][: config["max_points"]]

    out: List[Dict[str, Any]] = []
    for row in data:
        tp = row.get("time_period")
        val = row.get("value")
        out.append(
            {
                "time_period": tp.isoformat() if isinstance(tp, datetime) else tp,
                "value": float(val) if val is not None else None,
            }
        )
    return out


def _sum_series_by_time(series_list: List[List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    buckets: Dict[str, float] = {}
    for pts in series_list:
        for p in pts:
            t = p.get("time_period")
            v = p.get("value")
            if t is None or v is None:
                continue
            buckets[t] = buckets.get(t, 0.0) + float(v)
    return [
        {"time_period": t, "value": round(v, 4)}
        for t, v in sorted(buckets.items())
    ]


def _series_for_rows(
    conn, rows: List[Dict[str, Any]], period: str, metric: str
) -> List[Dict[str, Any]]:
    series = []
    for r in rows:
        dev = r.get("device_address")
        if not dev:
            continue
        bridge_id = r.get("mqtt_bridge_config_id")
        bridge_ids = [int(bridge_id)] if bridge_id is not None else None
        pts = fetch_device_chart_series(
            conn, dev, period, metric, bridge_ids
        )
        ph = derive_phase_from_row(r)
        label_parts = []
        if ph:
            label_parts.append(f"Fasa {ph}")
        label_parts.append(r.get("device_name") or dev)
        if r.get("bridge_name"):
            label_parts.append(f"({r['bridge_name']})")
        series.append(
            {
                "label": " — ".join(label_parts),
                "device_address": dev,
                "phase": ph,
                "bridge_name": r.get("bridge_name"),
                "points": pts,
            }
        )
    return series


def _chart_group(
    conn,
    block: Dict[str, Any],
    period: str,
    metric: str,
    label: str,
    key: str,
) -> Dict[str, Any]:
    ids, _miss = effective_bridge_ids(conn, block)
    rows = fetch_latest_filtered_rows(
        conn,
        ids,
        _cfg_list(block, "buildings") or None,
        _cfg_list(block, "device_addresses") or None,
    )
    phases = _cfg_list(block, "phases")
    rows = [r for r in rows if _phase_ok(r, phases)]
    series = _series_for_rows(conn, rows, period, metric)
    total = _sum_series_by_time([s["points"] for s in series]) if metric == "power" else []
    return {"key": key, "label": label, "series": series, "total": total}


def build_chart_data(
    db_manager,
    canvas_row: Dict[str, Any],
    period: str = "hour",
    metric: str = "power",
) -> Dict[str, Any]:
    """Chart series for devices in canvas scope."""
    cid = canvas_row["id"]
    cname = canvas_row["name"]
    ctype = canvas_row["type"]
    cfg = _parse_canvas_config(canvas_row.get("config"))
    period = (period or "hour").strip().lower()
    metric = (metric or "power").strip().lower()
    if metric not in _VALID_CHART_METRICS:
        metric = "power"

    groups: List[Dict[str, Any]] = []
    warnings: List[str] = []

    with db_manager.pool_connection() as conn:
        if ctype == "compare_buildings":
            comp = cfg.get("compare") or {}
            side_a = comp.get("a") or {}
            side_b = comp.get("b") or {}
            display = cfg.get("display") or {}
            labels = display.get("labels") or {}
            for m in effective_bridge_ids(conn, side_a)[1]:
                warnings.append(f"Tunnel tidak ditemukan (A): {m}")
            for m in effective_bridge_ids(conn, side_b)[1]:
                warnings.append(f"Tunnel tidak ditemukan (B): {m}")
            groups.append(
                _chart_group(
                    conn, side_a, period, metric, labels.get("a", "Sisi A"), "a"
                )
            )
            groups.append(
                _chart_group(
                    conn, side_b, period, metric, labels.get("b", "Sisi B"), "b"
                )
            )
        else:
            for m in effective_bridge_ids(conn, cfg)[1]:
                warnings.append(f"Tunnel tidak ditemukan: {m}")
            title = (cfg.get("display") or {}).get("title") or cname
            groups.append(_chart_group(conn, cfg, period, metric, title, "main"))

    return {
        "canvas_id": cid,
        "canvas_name": cname,
        "type": ctype,
        "period": period,
        "metric": metric,
        "warnings": warnings,
        "groups": groups,
    }


def get_canvas_by_id(db_manager, canvas_id: int) -> Optional[Dict[str, Any]]:
    with db_manager.pool_connection() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                SELECT id, name, type, config, poll_interval_seconds, enabled,
                       created_at, updated_at
                FROM canvas_definitions WHERE id = %s
                """,
                (canvas_id,),
            )
            row = cur.fetchone()
    return dict(row) if row else None

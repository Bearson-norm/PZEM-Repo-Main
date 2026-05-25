"""REST CRUD for mqtt_bridge_configs and canvas_definitions; canvas snapshot API."""
from __future__ import annotations

import json
import logging
from typing import Any, Dict

from flask import Blueprint, current_app, jsonify, request
from psycopg2.extras import Json, RealDictCursor

from canvas_service import build_chart_data, build_snapshot, get_canvas_by_id

logger = logging.getLogger(__name__)

config_bp = Blueprint("config_bp", __name__)


def _db():
    return current_app.config["DB_MANAGER"]


def _bridge_mgr():
    return current_app.config.get("BRIDGE_MANAGER")


def _serialize_canvas_row(r: Dict[str, Any]) -> Dict[str, Any]:
    d = dict(r)
    for k in ("created_at", "updated_at"):
        if d.get(k) is not None and hasattr(d[k], "isoformat"):
            d[k] = d[k].isoformat()
    return d


def _mask_bridge_row(row: Dict[str, Any]) -> Dict[str, Any]:
    r = dict(row)
    if "password_enc" in r:
        r["has_password"] = bool(r.get("password_enc"))
        del r["password_enc"]
    for k in ("created_at", "updated_at"):
        if r.get(k) is not None and hasattr(r[k], "isoformat"):
            r[k] = r[k].isoformat()
    return r


@config_bp.route("/api/mqtt-configs", methods=["GET"])
def list_mqtt_configs():
    try:
        with _db().pool_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, name, broker_host, broker_port, use_tls, username,
                           password_enc, topics, qos, enabled, last_connect_error,
                           created_at, updated_at
                    FROM mqtt_bridge_configs
                    ORDER BY id
                    """
                )
                rows = [dict(x) for x in cur.fetchall()]
        return jsonify([_mask_bridge_row(r) for r in rows])
    except Exception as e:
        logger.exception("list_mqtt_configs: %s", e)
        return jsonify({"error": str(e)}), 500


@config_bp.route("/api/mqtt-configs/<int:config_id>", methods=["GET"])
def get_mqtt_config(config_id: int):
    try:
        with _db().pool_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, name, broker_host, broker_port, use_tls, username,
                           password_enc, topics, qos, enabled, last_connect_error,
                           created_at, updated_at
                    FROM mqtt_bridge_configs WHERE id = %s
                    """,
                    (config_id,),
                )
                row = cur.fetchone()
        if not row:
            return jsonify({"error": "Not found"}), 404
        return jsonify(_mask_bridge_row(dict(row)))
    except Exception as e:
        logger.exception("get_mqtt_config: %s", e)
        return jsonify({"error": str(e)}), 500


@config_bp.route("/api/mqtt-configs", methods=["POST"])
def create_mqtt_config():
    try:
        body = request.get_json(force=True, silent=True) or {}
        name = body.get("name")
        host = body.get("broker_host")
        if not name or not host:
            return jsonify({"error": "name and broker_host required"}), 400
        topics = body.get("topics")
        if isinstance(topics, str):
            topics = json.loads(topics)
        if not isinstance(topics, list):
            topics = []
        pwd = body.get("password") or body.get("password_enc")
        if pwd is not None and str(pwd).strip() == "":
            pwd = None
        with _db().pool_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM mqtt_bridge_configs WHERE name = %s", (name,)
                )
                if cur.fetchone():
                    return (
                        jsonify(
                            {
                                "error": "Nama tunnel sudah dipakai; pilih nama unik untuk bridge ini."
                            }
                        ),
                        409,
                    )
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO mqtt_bridge_configs
                    (name, broker_host, broker_port, use_tls, username, password_enc,
                     topics, qos, enabled)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        name,
                        host,
                        int(body.get("broker_port") or 1883),
                        bool(body.get("use_tls")),
                        body.get("username") or None,
                        pwd or None,
                        Json(topics),
                        int(body.get("qos") or 1),
                        bool(body.get("enabled", True)),
                    ),
                )
                new_id = cur.fetchone()["id"]
            conn.commit()
        bm = _bridge_mgr()
        if bm:
            bm.reconcile_now()
        return jsonify({"id": new_id, "message": "created"}), 201
    except Exception as e:
        logger.exception("create_mqtt_config: %s", e)
        return jsonify({"error": str(e)}), 500


@config_bp.route("/api/mqtt-configs/<int:config_id>", methods=["PUT"])
def update_mqtt_config(config_id: int):
    try:
        body = request.get_json(force=True, silent=True) or {}
        with _db().pool_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT password_enc FROM mqtt_bridge_configs WHERE id = %s",
                    (config_id,),
                )
                existing = cur.fetchone()
                if not existing:
                    return jsonify({"error": "Not found"}), 404
                old_pwd = existing.get("password_enc")
                topics = body.get("topics")
                if topics is not None:
                    if isinstance(topics, str):
                        topics = json.loads(topics)
                    if not isinstance(topics, list):
                        topics = []
                pwd_in = body.get("password")
                if pwd_in is not None and str(pwd_in).strip() != "":
                    new_pwd = pwd_in
                else:
                    new_pwd = old_pwd
                sets = []
                params: list = []
                if "name" in body:
                    new_name = body["name"]
                    cur.execute(
                        """
                        SELECT id FROM mqtt_bridge_configs
                        WHERE name = %s AND id <> %s
                        """,
                        (new_name, config_id),
                    )
                    if cur.fetchone():
                        return (
                            jsonify(
                                {"error": "Nama tunnel sudah dipakai bridge lain."}
                            ),
                            409,
                        )
                    sets.append("name = %s")
                    params.append(new_name)
                if "broker_host" in body:
                    sets.append("broker_host = %s")
                    params.append(body["broker_host"])
                if "broker_port" in body:
                    sets.append("broker_port = %s")
                    params.append(int(body["broker_port"]))
                if "use_tls" in body:
                    sets.append("use_tls = %s")
                    params.append(bool(body["use_tls"]))
                if "username" in body:
                    sets.append("username = %s")
                    params.append(body["username"])
                if new_pwd is not None:
                    sets.append("password_enc = %s")
                    params.append(new_pwd)
                if topics is not None:
                    sets.append("topics = %s")
                    params.append(Json(topics))
                if "qos" in body:
                    sets.append("qos = %s")
                    params.append(int(body["qos"]))
                if "enabled" in body:
                    sets.append("enabled = %s")
                    params.append(bool(body["enabled"]))
                if not sets:
                    return jsonify({"message": "no changes"})
                sets.append("updated_at = CURRENT_TIMESTAMP")
                params.append(config_id)
                cur.execute(
                    f"UPDATE mqtt_bridge_configs SET {', '.join(sets)} WHERE id = %s",
                    params,
                )
            conn.commit()
        bm = _bridge_mgr()
        if bm:
            bm.reconcile_now()
        return jsonify({"message": "updated"})
    except Exception as e:
        logger.exception("update_mqtt_config: %s", e)
        return jsonify({"error": str(e)}), 500


@config_bp.route("/api/mqtt-configs/<int:config_id>", methods=["DELETE"])
def delete_mqtt_config(config_id: int):
    try:
        with _db().pool_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM mqtt_bridge_configs WHERE id = %s", (config_id,)
                )
            conn.commit()
        bm = _bridge_mgr()
        if bm:
            bm.reconcile_now()
        return jsonify({"message": "deleted"})
    except Exception as e:
        logger.exception("delete_mqtt_config: %s", e)
        return jsonify({"error": str(e)}), 500


@config_bp.route("/api/canvas-configs", methods=["GET"])
def list_canvas_configs():
    try:
        with _db().pool_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    SELECT id, name, type, config, poll_interval_seconds, enabled,
                           created_at, updated_at
                    FROM canvas_definitions
                    ORDER BY id
                    """
                )
                rows = [dict(r) for r in cur.fetchall()]
        return jsonify(rows)
    except Exception as e:
        logger.exception("list_canvas: %s", e)
        return jsonify({"error": str(e)}), 500


@config_bp.route("/api/canvas-configs/<int:canvas_id>", methods=["GET"])
def get_canvas_config(canvas_id: int):
    try:
        row = get_canvas_by_id(_db(), canvas_id)
        if not row:
            return jsonify({"error": "Not found"}), 404
        return jsonify(_serialize_canvas_row(row))
    except Exception as e:
        logger.exception("get_canvas: %s", e)
        return jsonify({"error": str(e)}), 500


@config_bp.route("/api/canvas-configs", methods=["POST"])
def create_canvas_config():
    try:
        body = request.get_json(force=True, silent=True) or {}
        name = body.get("name")
        ctype = body.get("type") or "three_phase_building"
        if not name:
            return jsonify({"error": "name required"}), 400
        cfg = body.get("config") or {}
        if isinstance(cfg, str):
            cfg = json.loads(cfg)
        poll = int(body.get("poll_interval_seconds") or 300)
        enabled = bool(body.get("enabled", True))
        with _db().pool_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """
                    INSERT INTO canvas_definitions
                    (name, type, config, poll_interval_seconds, enabled)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (name, ctype, Json(cfg), poll, enabled),
                )
                new_id = cur.fetchone()["id"]
            conn.commit()
        return jsonify({"id": new_id}), 201
    except Exception as e:
        logger.exception("create_canvas: %s", e)
        return jsonify({"error": str(e)}), 500


@config_bp.route("/api/canvas-configs/<int:canvas_id>", methods=["PUT"])
def update_canvas_config(canvas_id: int):
    try:
        body = request.get_json(force=True, silent=True) or {}
        with _db().pool_connection() as conn:
            with conn.cursor() as cur:
                sets = []
                params: list = []
                if "name" in body:
                    sets.append("name = %s")
                    params.append(body["name"])
                if "type" in body:
                    sets.append("type = %s")
                    params.append(body["type"])
                if "config" in body:
                    cfg = body["config"]
                    if isinstance(cfg, str):
                        cfg = json.loads(cfg)
                    sets.append("config = %s")
                    params.append(Json(cfg))
                if "poll_interval_seconds" in body:
                    sets.append("poll_interval_seconds = %s")
                    params.append(int(body["poll_interval_seconds"]))
                if "enabled" in body:
                    sets.append("enabled = %s")
                    params.append(bool(body["enabled"]))
                if not sets:
                    return jsonify({"message": "no changes"})
                sets.append("updated_at = CURRENT_TIMESTAMP")
                params.append(canvas_id)
                cur.execute(
                    f"UPDATE canvas_definitions SET {', '.join(sets)} WHERE id = %s",
                    params,
                )
                if cur.rowcount == 0:
                    return jsonify({"error": "Not found"}), 404
            conn.commit()
        return jsonify({"message": "updated"})
    except Exception as e:
        logger.exception("update_canvas: %s", e)
        return jsonify({"error": str(e)}), 500


@config_bp.route("/api/canvas-configs/<int:canvas_id>", methods=["DELETE"])
def delete_canvas_config(canvas_id: int):
    try:
        with _db().pool_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM canvas_definitions WHERE id = %s", (canvas_id,)
                )
            conn.commit()
        return jsonify({"message": "deleted"})
    except Exception as e:
        logger.exception("delete_canvas: %s", e)
        return jsonify({"error": str(e)}), 500


@config_bp.route("/api/canvas/<int:canvas_id>/snapshot", methods=["GET"])
def canvas_snapshot(canvas_id: int):
    try:
        row = get_canvas_by_id(_db(), canvas_id)
        if not row:
            return jsonify({"error": "Not found"}), 404
        if not row.get("enabled", True):
            return jsonify({"error": "Canvas disabled"}), 403
        snap = build_snapshot(_db(), row)
        return jsonify(snap)
    except Exception as e:
        logger.exception("canvas_snapshot: %s", e)
        return jsonify({"error": str(e)}), 500


@config_bp.route("/api/canvas/<int:canvas_id>/chart", methods=["GET"])
def canvas_chart(canvas_id: int):
    try:
        row = get_canvas_by_id(_db(), canvas_id)
        if not row:
            return jsonify({"error": "Not found"}), 404
        if not row.get("enabled", True):
            return jsonify({"error": "Canvas disabled"}), 403
        period = request.args.get("period", "hour")
        metric = request.args.get("metric", "power")
        data = build_chart_data(_db(), row, period=period, metric=metric)
        return jsonify(data)
    except Exception as e:
        logger.exception("canvas_chart: %s", e)
        return jsonify({"error": str(e)}), 500

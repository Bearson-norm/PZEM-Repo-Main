"""Dynamic MQTT subscribers from mqtt_bridge_configs rows (dashboard process)."""
from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Callable, Dict, List, Optional

import paho.mqtt.client as mqtt
from psycopg2.extras import RealDictCursor

from shared.pzem_ingest import (
    decode_json_payload,
    enrich_payload_from_topic,
    persist_pzem_reading,
    DEFAULT_DEVICE_BUILDING_MAP,
)

logger = logging.getLogger(__name__)


def _topics_list(raw: Any) -> List[str]:
    if raw is None:
        return []
    if isinstance(raw, list):
        return [str(t) for t in raw]
    if isinstance(raw, str):
        try:
            v = json.loads(raw)
            return [str(t) for t in v] if isinstance(v, list) else []
        except json.JSONDecodeError:
            return []
    return []


def _config_signature(cfg: Dict[str, Any]) -> tuple:
    return (
        cfg.get("broker_host"),
        int(cfg.get("broker_port") or 1883),
        bool(cfg.get("use_tls")),
        cfg.get("username") or "",
        cfg.get("password_enc") or "",
        tuple(_topics_list(cfg.get("topics"))),
        int(cfg.get("qos") or 1),
    )


def fetch_enabled_bridge_configs(conn) -> List[Dict[str, Any]]:
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT id, name, broker_host, broker_port, use_tls, username,
                   password_enc, topics, qos, enabled
            FROM mqtt_bridge_configs
            WHERE enabled = TRUE
            ORDER BY id
            """
        )
        return [dict(r) for r in cur.fetchall()]


def update_bridge_error(conn, bridge_id: int, err: Optional[str]):
    with conn.cursor() as cur:
        cur.execute(
            """
            UPDATE mqtt_bridge_configs
            SET last_connect_error = %s, updated_at = CURRENT_TIMESTAMP
            WHERE id = %s
            """,
            (err, bridge_id),
        )
    conn.commit()


class _BridgeWorker:
    def __init__(
        self,
        cfg: Dict[str, Any],
        db_connect: Callable[[], Any],
        putconn: Callable[[Any], None],
    ):
        self.cfg = cfg
        self.signature = _config_signature(cfg)
        self._db_connect = db_connect
        self._putconn = putconn
        self._client = None
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()
        if self._client:
            try:
                self._client.loop_stop()
                self._client.disconnect()
            except Exception:
                pass
            self._client = None
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)

    def _run(self):
        bid = self.cfg["id"]
        host = self.cfg["broker_host"]
        port = int(self.cfg["broker_port"] or 1883)
        use_tls = bool(self.cfg.get("use_tls"))
        user = self.cfg.get("username") or ""
        password = self.cfg.get("password_enc") or ""
        qos = int(self.cfg.get("qos") or 1)
        topics = _topics_list(self.cfg.get("topics"))
        if not topics:
            logger.warning("[BRIDGE %s] No topics configured; skipping connect", bid)
            self._report_error("No topics configured")
            return

        def on_connect(client, userdata, flags, reason_code, properties=None):
            rc = 0
            if reason_code is not None:
                rc = int(getattr(reason_code, "value", reason_code))
            if rc != 0:
                logger.error("[BRIDGE %s] connect failed rc=%s", bid, rc)
                self._report_error(f"MQTT connect rc={rc}")
                return
            self._report_error(None)
            for t in topics:
                try:
                    client.subscribe(t, qos)
                    logger.info("[BRIDGE %s] Subscribed %s QoS=%s", bid, t, qos)
                except Exception as e:
                    logger.error("[BRIDGE %s] subscribe %s: %s", bid, t, e)

        def on_message(client, userdata, msg):
            try:
                data = decode_json_payload(msg.payload)
                if not data:
                    return
                building, phase = enrich_payload_from_topic(
                    data, msg.topic, DEFAULT_DEVICE_BUILDING_MAP
                )
                conn = self._db_connect()
                try:
                    cur = conn.cursor()
                    persist_pzem_reading(
                        cur,
                        data,
                        building,
                        phase,
                        bid,
                        DEFAULT_DEVICE_BUILDING_MAP,
                    )
                    conn.commit()
                    cur.close()
                except Exception:
                    try:
                        conn.rollback()
                    except Exception:
                        pass
                    raise
                finally:
                    self._putconn(conn)
            except Exception as e:
                logger.exception("[BRIDGE %s] on_message: %s", bid, e)

        while not self._stop.is_set():
            cl = None
            try:
                cl = mqtt.Client(
                    callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
                    client_id=f"pzem_bridge_{bid}",
                )
                cl.on_connect = on_connect
                cl.on_message = on_message
                if user:
                    cl.username_pw_set(user, password)
                if use_tls:
                    cl.tls_set()
                cl.connect(host, port, 60)
                cl.loop_start()
                self._client = cl
                while not self._stop.is_set():
                    time.sleep(0.5)
            except Exception as e:
                logger.exception("[BRIDGE %s] loop error: %s", bid, e)
                self._report_error(str(e))
                time.sleep(30)
            finally:
                if cl:
                    try:
                        cl.loop_stop()
                        cl.disconnect()
                    except Exception:
                        pass
                self._client = None
                if self._stop.is_set():
                    break

    def _report_error(self, err: Optional[str]):
        try:
            conn = self._db_connect()
            try:
                update_bridge_error(conn, self.cfg["id"], err)
            finally:
                self._putconn(conn)
        except Exception:
            pass


class MqttBridgeManager:
    """Starts one worker thread per enabled mqtt_bridge_configs row."""

    def __init__(self, db_manager):
        self._db = db_manager
        self._workers: Dict[int, _BridgeWorker] = {}
        self._lock = threading.Lock()
        self._scheduler: Optional[threading.Thread] = None
        self._stop_scheduler = threading.Event()

    def _get_conn(self):
        return self._db.pool.getconn()

    def _put_conn(self, conn):
        self._db.pool.putconn(conn)

    def start(self):
        if self._scheduler and self._scheduler.is_alive():
            return
        self._stop_scheduler.clear()
        self._scheduler = threading.Thread(target=self._reconcile_loop, daemon=True)
        self._scheduler.start()
        logger.info("[BRIDGE-MGR] Scheduler started")

    def stop(self):
        self._stop_scheduler.set()
        with self._lock:
            for w in list(self._workers.values()):
                w.stop()
            self._workers.clear()

    def reconcile_now(self):
        self._reconcile()

    def _reconcile_loop(self):
        while not self._stop_scheduler.is_set():
            try:
                self._reconcile()
            except Exception:
                logger.exception("[BRIDGE-MGR] reconcile")
            time.sleep(60)

    def _reconcile(self):
        conn = self._get_conn()
        try:
            rows = fetch_enabled_bridge_configs(conn)
            wanted = {int(r["id"]): r for r in rows}
        finally:
            self._put_conn(conn)

        with self._lock:
            for wid, w in list(self._workers.items()):
                if wid not in wanted:
                    logger.info("[BRIDGE-MGR] Stopping worker %s", wid)
                    w.stop()
                    del self._workers[wid]

            for wid, cfg in wanted.items():
                sig = _config_signature(cfg)
                existing = self._workers.get(wid)
                if existing and existing.signature != sig:
                    logger.info("[BRIDGE-MGR] Restart worker %s (config changed)", wid)
                    existing.stop()
                    del self._workers[wid]
                    existing = None
                if wid not in self._workers:
                    logger.info(
                        "[BRIDGE-MGR] Starting worker %s %s",
                        wid,
                        cfg.get("name"),
                    )
                    w = _BridgeWorker(cfg, self._get_conn, self._put_conn)
                    w.start()
                    self._workers[wid] = w

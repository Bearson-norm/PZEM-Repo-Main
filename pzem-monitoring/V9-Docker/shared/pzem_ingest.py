"""
Shared PZEM MQTT payload normalization and DB row preparation.
Used by mqtt/mqtt_client.py and dashboard MqttBridgeManager.
"""
from __future__ import annotations

import hashlib
import json
import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_DEVICE_BUILDING_MAP = {
    "1": {"building": "CKPG1", "phase": "R"},
    "2": {"building": "CKPG1", "phase": "S"},
    "3": {"building": "CKPG1", "phase": "T"},
}

DEFAULT_MQTT_TOPICS = [
    "energy/3phase/+/phase/+/data",
    "energy/3phase/+/+/phase/+/data",
    "energy/3phase/+/phase/+/status",
    "energy/3phase/+/+/phase/+/status",
    "energy/3phase/+/phase/+/heartbeat",
    "energy/3phase/+/+/phase/+/heartbeat",
    "energy/pzem/data",
]

BILLING_EVENTS = frozenset({"wrap", "reset"})
DEFAULT_GAP_MINUTES = 20


def parse_topic_building_phase(topic: str) -> Tuple[Optional[str], Optional[str], bool]:
    """Return building, phase, from_3phase_topic flag."""
    building = None
    phase = None
    from_3phase = False
    try:
        parts = topic.split("/")
        if topic.startswith("energy/3phase/"):
            if len(parts) >= 7:
                building = f"{parts[2]}-{parts[3]}"
                phase = parts[5].upper()
                from_3phase = True
            elif len(parts) >= 5:
                building = parts[2]
                phase = parts[4].upper()
                from_3phase = True
    except Exception as e:
        logger.warning("parse_topic_building_phase: %s", e)
    return building, phase, from_3phase


def topic_kind(topic: str) -> str:
    """Classify firmware topic suffix: data | status | heartbeat | other."""
    if not topic:
        return "other"
    suffix = topic.rstrip("/").rsplit("/", 1)[-1].lower()
    if suffix in ("data", "status", "heartbeat"):
        return suffix
    if topic == "energy/pzem/data":
        return "data"
    return "other"


def enrich_payload_from_topic(
    data: Dict[str, Any],
    topic: str,
    device_building_map: Optional[Dict[str, Dict[str, str]]] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Mutates data with device_address, building, phase per existing mqtt_client rules.
    Returns (building, phase) after enrichment.
    """
    device_building_map = device_building_map or DEFAULT_DEVICE_BUILDING_MAP
    building, phase, from_3phase = parse_topic_building_phase(topic)

    if from_3phase and building and phase:
        data["device_address"] = f"{building}-{phase}"
        data["building"] = building
        data["phase"] = phase
        data["phase_id"] = phase
    else:
        device_address = (
            data.get("device_address")
            or data.get("device_id")
            or data.get("pzem_address")
            or data.get("address")
        )
        if device_address and str(device_address).strip() in device_building_map:
            mapping = device_building_map[str(device_address).strip()]
            building = mapping["building"]
            phase = mapping["phase"]

    if building:
        data["building"] = building
    if phase:
        data["phase"] = phase
        data["phase_id"] = phase

    if not data.get("building") and data.get("building_id"):
        data["building"] = data["building_id"]
    if not data.get("phase") and data.get("phase_id"):
        data["phase"] = data["phase_id"]

    return data.get("building"), data.get("phase")


def safe_float(value: Any) -> Optional[float]:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def safe_int(value: Any) -> Optional[int]:
    if value is None or value == "":
        return None
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return None


def safe_bool(value: Any) -> Optional[bool]:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    text = str(value).strip().lower()
    if text in ("true", "1", "yes", "on"):
        return True
    if text in ("false", "0", "no", "off"):
        return False
    return None


def resolve_device_address(
    data: Dict[str, Any], building: Optional[str], phase: Optional[str]
) -> Optional[str]:
    if data.get("device_address"):
        return str(data.get("device_address")).strip()
    if data.get("device_id"):
        return str(data.get("device_id")).strip()
    if data.get("pzem_address"):
        return str(data.get("pzem_address")).strip()
    if data.get("address"):
        return str(data.get("address")).strip()
    if building and phase:
        return f"{building}-{phase}"
    return None


def compute_payload_hash(data: Dict[str, Any]) -> str:
    """SHA-256 of canonical JSON (firmware payload before topic enrichment)."""
    canonical = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def extract_metrics_for_db(
    data: Dict[str, Any], building: Optional[str], phase: Optional[str]
) -> Dict[str, Any]:
    """Flatten live metrics; billing energy prefers meter_energy_kwh / energy_last."""
    current = (
        data.get("current_data", {})
        if isinstance(data.get("current_data"), dict)
        else {}
    )

    device_address = resolve_device_address(data, building, phase)
    building = building or data.get("building") or data.get("building_id")
    phase = phase or data.get("phase") or data.get("phase_id")
    if building is not None:
        building = str(building).strip() or None
    if phase is not None:
        phase = str(phase).strip().upper() or None

    voltage = safe_float(
        data.get("voltage") or data.get("avg_voltage") or current.get("voltage")
    )
    current_a = safe_float(
        data.get("current") or data.get("avg_current") or current.get("current")
    )
    power = safe_float(
        data.get("power")
        or data.get("avg_power")
        or data.get("active_power")
        or current.get("active_power")
    )

    meter_energy_kwh = safe_float(data.get("meter_energy_kwh"))
    energy_last = safe_float(data.get("energy_last"))
    energy_first = safe_float(data.get("energy_first"))
    accumulated_energy_kwh = safe_float(data.get("accumulated_energy_kwh"))
    legacy_energy = safe_float(
        data.get("energy") or data.get("total_energy") or data.get("active_energy")
    )
    energy = meter_energy_kwh if meter_energy_kwh is not None else (
        energy_last if energy_last is not None else legacy_energy
    )
    if meter_energy_kwh is None and energy is not None:
        meter_energy_kwh = energy

    frequency = safe_float(
        data.get("frequency") or current.get("frequency") or 50.0
    )
    power_factor = safe_float(
        data.get("power_factor") or current.get("power_factor") or 1.0
    )
    wifi_rssi = safe_int(data.get("wifi_rssi"))
    device_timestamp = safe_int(
        data.get("timestamp_unix")
        or data.get("timestamp")
        or data.get("device_timestamp")
        or data.get("time")
    )
    sample_interval = safe_int(data.get("interval_minutes", 60))
    sample_count = safe_int(data.get("sample_count", 1))

    time_synced = safe_bool(data.get("time_synced"))
    period_start_unix = safe_int(data.get("period_start_unix"))
    period_end_unix = safe_int(data.get("period_end_unix"))
    if time_synced is False:
        if not period_start_unix:
            period_start_unix = 0
        if not period_end_unix:
            period_end_unix = 0

    energy_event = data.get("energy_event")
    if energy_event is not None:
        energy_event = str(energy_event).strip().lower() or None
    energy_method = data.get("energy_method")
    if energy_method is not None:
        energy_method = str(energy_method).strip().lower() or None

    device_id = data.get("device_id")
    if device_id is not None:
        device_id = str(device_id).strip() or None
    firmware_version = data.get("firmware_version")
    if firmware_version is not None:
        firmware_version = str(firmware_version).strip() or None

    return {
        "device_address": device_address,
        "building": building,
        "phase": phase,
        "device_id": device_id,
        "firmware_version": firmware_version,
        "voltage": voltage,
        "current": current_a,
        "power": power,
        "energy": energy,
        "frequency": frequency,
        "power_factor": power_factor,
        "wifi_rssi": wifi_rssi,
        "device_timestamp": device_timestamp,
        "sample_interval": sample_interval,
        "sample_count": sample_count,
        "time_synced": time_synced,
        "timestamp_unix": safe_int(data.get("timestamp_unix") or device_timestamp),
        "period_start_unix": period_start_unix,
        "period_end_unix": period_end_unix,
        "period_duration_ms": safe_int(data.get("period_duration_ms")),
        "is_retry": safe_bool(data.get("is_retry")),
        "meter_energy_kwh": meter_energy_kwh,
        "energy_first": energy_first,
        "energy_last": energy_last if energy_last is not None else meter_energy_kwh,
        "accumulated_energy_kwh": accumulated_energy_kwh,
        "energy_method": energy_method,
        "energy_event": energy_event,
    }


def decode_json_payload(raw: bytes) -> Optional[Dict[str, Any]]:
    try:
        text = raw.decode("utf-8")
        data = json.loads(text)
        if isinstance(data, dict):
            return data
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        logger.error("decode_json_payload: %s", e)
    return None


def upsert_device_metadata_sql():
    """SQL for pzem_devices upsert (params: device_address, device_name, location)."""
    return """
        INSERT INTO pzem_devices (device_address, device_name, location, last_seen, total_records)
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP, 1)
        ON CONFLICT (device_address)
        DO UPDATE SET
            device_name = COALESCE(EXCLUDED.device_name, pzem_devices.device_name),
            location = COALESCE(EXCLUDED.location, pzem_devices.location),
            last_seen = CURRENT_TIMESTAMP,
            total_records = pzem_devices.total_records + 1,
            updated_at = CURRENT_TIMESTAMP
    """


def touch_device_last_seen_sql():
    return """
        INSERT INTO pzem_devices (device_address, device_name, location, last_seen, total_records)
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP, 0)
        ON CONFLICT (device_address)
        DO UPDATE SET
            device_name = COALESCE(EXCLUDED.device_name, pzem_devices.device_name),
            location = COALESCE(EXCLUDED.location, pzem_devices.location),
            last_seen = CURRENT_TIMESTAMP,
            updated_at = CURRENT_TIMESTAMP
    """


def _device_name_location(
    building: Optional[str], phase: Optional[str]
) -> Tuple[Optional[str], Optional[str]]:
    device_name = None
    if building and phase:
        device_name = f"Phase {phase} - {building}"
    elif phase:
        device_name = f"Phase {phase}"
    elif building:
        device_name = f"Device {building}"
    return device_name, building if building else None


def persist_pzem_reading(
    cursor,
    data: Dict[str, Any],
    building: Optional[str],
    phase: Optional[str],
    mqtt_bridge_config_id: Optional[int],
    device_building_map: Optional[Dict[str, Dict[str, str]]] = None,
    payload_hash: Optional[str] = None,
) -> Optional[str]:
    """
    INSERT one row into pzem_data + upsert pzem_devices.
    Returns 'inserted', 'duplicate', or None when the row cannot be stored.
    Idempotent: same payload_hash or synced (building, phase, period_end_unix) is a no-op.
    cursor must belong to an open transaction.
    """
    device_building_map = device_building_map or DEFAULT_DEVICE_BUILDING_MAP
    row = extract_metrics_for_db(data, building, phase)
    device_address = row.get("device_address")
    if not device_address:
        return None
    device_address = str(device_address).strip()
    row["device_address"] = device_address

    if device_address in device_building_map:
        mapping = device_building_map[device_address]
        row["building"] = mapping["building"]
        row["phase"] = mapping["phase"]
    building = row.get("building")
    phase = row.get("phase")

    from_3phase = bool(data.get("building") and data.get("phase"))
    if from_3phase and (not building or not phase):
        logger.warning(
            "Dropping /data without building/phase (device_address=%s)", device_address
        )
        return None

    if payload_hash is None:
        payload_hash = compute_payload_hash(data)

    cursor.execute(
        """
        INSERT INTO pzem_data (
            device_address, voltage, current, power, energy, frequency,
            power_factor, wifi_rssi, device_timestamp, sample_interval,
            sample_count, device_status, data_quality, mqtt_bridge_config_id,
            building, phase, device_id, firmware_version,
            time_synced, timestamp_unix, period_start_unix, period_end_unix,
            period_duration_ms, is_retry,
            meter_energy_kwh, energy_first, energy_last, accumulated_energy_kwh,
            energy_method, energy_event, payload_json, payload_hash
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s
        )
        ON CONFLICT DO NOTHING
        RETURNING id
        """,
        (
            device_address,
            row["voltage"],
            row["current"],
            row["power"],
            row["energy"],
            row["frequency"],
            row["power_factor"],
            row["wifi_rssi"],
            row["device_timestamp"],
            row["sample_interval"],
            row["sample_count"],
            "online",
            "live",
            mqtt_bridge_config_id,
            building,
            phase,
            row["device_id"],
            row["firmware_version"],
            row["time_synced"],
            row["timestamp_unix"],
            row["period_start_unix"],
            row["period_end_unix"],
            row["period_duration_ms"],
            row["is_retry"],
            row["meter_energy_kwh"],
            row["energy_first"],
            row["energy_last"],
            row["accumulated_energy_kwh"],
            row["energy_method"],
            row["energy_event"],
            json.dumps(data, default=str),
            payload_hash,
        ),
    )
    inserted = cursor.fetchone()
    if not inserted:
        return "duplicate"

    device_name, location = _device_name_location(building, phase)
    cursor.execute(
        upsert_device_metadata_sql(), (device_address, device_name, location)
    )

    event = row.get("energy_event")
    if event in BILLING_EVENTS and building and phase:
        cursor.execute(
            """
            INSERT INTO pzem_energy_events (
                building, phase, event_type, period_end_unix,
                meter_energy_kwh, source_payload_hash
            ) VALUES (%s, %s, %s, %s, %s, %s)
            ON CONFLICT DO NOTHING
            """,
            (
                building,
                phase,
                event,
                row.get("period_end_unix"),
                row.get("meter_energy_kwh"),
                payload_hash,
            ),
        )
    return "inserted"


def persist_heartbeat(
    cursor,
    data: Dict[str, Any],
    building: Optional[str],
    phase: Optional[str],
) -> bool:
    if not building or not phase:
        logger.warning("Dropping heartbeat without building/phase")
        return False
    building = str(building).strip()
    phase = str(phase).strip().upper()
    device_address = resolve_device_address(data, building, phase)
    cursor.execute(
        """
        INSERT INTO pzem_device_heartbeat (
            building, phase, device_address, pzem_connected,
            buffer_count, pzem_read_errors, seen_at, payload_json
        ) VALUES (
            %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s::jsonb
        )
        ON CONFLICT (building, phase) DO UPDATE SET
            device_address = COALESCE(EXCLUDED.device_address, pzem_device_heartbeat.device_address),
            pzem_connected = EXCLUDED.pzem_connected,
            buffer_count = EXCLUDED.buffer_count,
            pzem_read_errors = EXCLUDED.pzem_read_errors,
            seen_at = CURRENT_TIMESTAMP,
            payload_json = EXCLUDED.payload_json
        """,
        (
            building,
            phase,
            device_address,
            safe_bool(data.get("pzem_connected")),
            safe_int(data.get("buffer_count")),
            safe_int(data.get("pzem_read_errors")),
            json.dumps(data, default=str),
        ),
    )
    if device_address:
        name, location = _device_name_location(building, phase)
        cursor.execute(
            touch_device_last_seen_sql(), (str(device_address).strip(), name, location)
        )
    return True


def persist_status(
    cursor,
    data: Dict[str, Any],
    building: Optional[str],
    phase: Optional[str],
) -> bool:
    device_address = resolve_device_address(data, building, phase)
    if not device_address:
        logger.warning("Dropping status without device identity")
        return False
    name, location = _device_name_location(building, phase)
    cursor.execute(
        touch_device_last_seen_sql(), (str(device_address).strip(), name, location)
    )
    logger.info(
        "status ack building=%s phase=%s device=%s keys=%s",
        building,
        phase,
        device_address,
        list(data.keys()),
    )
    return True


def persist_mqtt_message(
    cursor,
    topic: str,
    data: Dict[str, Any],
    mqtt_bridge_config_id: Optional[int] = None,
    device_building_map: Optional[Dict[str, Dict[str, str]]] = None,
) -> str:
    """
    Route one decoded MQTT JSON dict by topic suffix.
    Returns inserted | duplicate | heartbeat | status | ignored.
    """
    if not isinstance(data, dict):
        return "ignored"

    kind = topic_kind(topic)
    original = dict(data)
    payload_hash = compute_payload_hash(original)
    building, phase = enrich_payload_from_topic(data, topic, device_building_map)

    if kind == "heartbeat":
        ok = persist_heartbeat(cursor, data, building, phase)
        return "heartbeat" if ok else "ignored"
    if kind == "status":
        ok = persist_status(cursor, data, building, phase)
        return "status" if ok else "ignored"
    if kind != "data":
        logger.warning("Ignoring unsupported MQTT topic: %s", topic)
        return "ignored"

    result = persist_pzem_reading(
        cursor,
        data,
        building,
        phase,
        mqtt_bridge_config_id,
        device_building_map,
        payload_hash=payload_hash,
    )
    if result is None:
        return "ignored"
    return result

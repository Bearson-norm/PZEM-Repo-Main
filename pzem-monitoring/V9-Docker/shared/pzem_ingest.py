"""
Shared PZEM MQTT payload normalization and DB row preparation.
Used by mqtt/mqtt_client.py and dashboard MqttBridgeManager.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_DEVICE_BUILDING_MAP = {
    "1": {"building": "CKPG1", "phase": "R"},
    "2": {"building": "CKPG1", "phase": "S"},
    "3": {"building": "CKPG1", "phase": "T"},
}


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


def extract_metrics_for_db(
    data: Dict[str, Any], building: Optional[str], phase: Optional[str]
) -> Dict[str, Any]:
    """Flatten nested current_data; return keys needed for INSERT."""
    current = (
        data.get("current_data", {})
        if isinstance(data.get("current_data"), dict)
        else {}
    )

    device_address = resolve_device_address(data, building, phase)
    building = building or data.get("building") or data.get("building_id")
    phase = phase or data.get("phase") or data.get("phase_id")

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
    energy = safe_float(
        data.get("energy")
        or data.get("total_energy")
        or data.get("active_energy")
        or current.get("active_energy")
    )
    frequency = safe_float(
        data.get("frequency") or current.get("frequency") or 50.0
    )
    power_factor = safe_float(
        data.get("power_factor") or current.get("power_factor") or 1.0
    )
    wifi_rssi = safe_int(data.get("wifi_rssi"))
    device_timestamp = safe_int(
        data.get("timestamp") or data.get("device_timestamp") or data.get("time")
    )
    sample_interval = safe_int(data.get("interval_minutes", 60))
    sample_count = safe_int(data.get("sample_count", 1))

    return {
        "device_address": device_address,
        "building": building,
        "phase": phase,
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


def persist_pzem_reading(
    cursor,
    data: Dict[str, Any],
    building: Optional[str],
    phase: Optional[str],
    mqtt_bridge_config_id: Optional[int],
    device_building_map: Optional[Dict[str, Dict[str, str]]] = None,
) -> bool:
    """
    INSERT one row into pzem_data + upsert pzem_devices.
    cursor must belong to an open transaction.
    """
    device_building_map = device_building_map or DEFAULT_DEVICE_BUILDING_MAP
    row = extract_metrics_for_db(data, building, phase)
    device_address = row.get("device_address")
    if not device_address:
        return False
    device_address = str(device_address).strip()
    row["device_address"] = device_address

    if device_address in device_building_map:
        mapping = device_building_map[device_address]
        row["building"] = mapping["building"]
        row["phase"] = mapping["phase"]
    building = row.get("building")
    phase = row.get("phase")

    cursor.execute(
        """
        INSERT INTO pzem_data (
            device_address, voltage, current, power, energy, frequency,
            power_factor, wifi_rssi, device_timestamp, sample_interval,
            sample_count, device_status, data_quality, mqtt_bridge_config_id
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
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
        ),
    )

    device_name = None
    if building and phase:
        device_name = f"Phase {phase} - {building}"
    elif phase:
        device_name = f"Phase {phase}"
    elif building:
        device_name = f"Device {building}"
    location = building if building else None
    cursor.execute(
        upsert_device_metadata_sql(), (device_address, device_name, location)
    )
    return True

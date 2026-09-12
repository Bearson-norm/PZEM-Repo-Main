from shared.pzem_ingest import (
    compute_payload_hash,
    extract_metrics_for_db,
    persist_mqtt_message,
    persist_pzem_reading,
    topic_kind,
)


class FakeCursor:
    """In-memory uniqueness on payload_hash and synced (building, phase, period_end)."""

    def __init__(self):
        self.rows = []
        self.sqls = []
        self._last_fetch = None
        self.hashes = set()
        self.periods = set()

    def execute(self, sql, params=None):
        self.sqls.append(sql)
        text = " ".join(sql.split()).lower()
        if text.startswith("insert into pzem_data"):
            payload_hash = params[-1] if params else None
            building = params[14] if params and len(params) > 14 else None
            phase = params[15] if params and len(params) > 15 else None
            time_synced = params[18] if params and len(params) > 18 else None
            period_end = params[21] if params and len(params) > 21 else None
            period_key = None
            if time_synced and period_end and period_end > 0 and building and phase:
                period_key = (building, phase, period_end)
            if payload_hash in self.hashes or (period_key and period_key in self.periods):
                self._last_fetch = None
                return
            if payload_hash:
                self.hashes.add(payload_hash)
            if period_key:
                self.periods.add(period_key)
            self.rows.append(params)
            self._last_fetch = (len(self.rows),)
            return
        self._last_fetch = None

    def fetchone(self):
        return self._last_fetch


def _contract_payload(**overrides):
    data = {
        "firmware_version": "1.1.0",
        "device_id": "esp-r",
        "building": "CKPG1",
        "phase": "R",
        "meter_energy_kwh": 123.45,
        "energy_first": 123.40,
        "energy_last": 123.45,
        "accumulated_energy_kwh": 0.05,
        "energy_method": "counter_delta",
        "energy_event": "none",
        "time_synced": True,
        "timestamp_unix": 1_700_000_300,
        "period_start_unix": 1_700_000_000,
        "period_end_unix": 1_700_000_300,
        "period_duration_ms": 300000,
        "interval_minutes": 5,
        "sample_count": 60,
        "avg_voltage": 220.1,
        "avg_current": 1.2,
        "avg_power": 250.0,
        "is_retry": False,
    }
    data.update(overrides)
    return data


def test_topic_kind():
    assert topic_kind("energy/3phase/CKPG1/phase/R/data") == "data"
    assert topic_kind("energy/3phase/CKPG1/phase/R/status") == "status"
    assert topic_kind("energy/3phase/CKPG1/phase/R/heartbeat") == "heartbeat"
    assert topic_kind("energy/pzem/data") == "data"


def test_energy_prefers_meter_energy_kwh_not_current_data():
    data = {
        "meter_energy_kwh": 50.0,
        "energy_last": 49.9,
        "energy": 10.0,
        "current_data": {"active_energy": 999.0, "voltage": 220, "current": 1, "active_power": 200},
    }
    row = extract_metrics_for_db(data, "CKPG1", "R")
    assert row["energy"] == 50.0
    assert row["meter_energy_kwh"] == 50.0
    assert row["energy_last"] == 49.9


def test_energy_falls_back_to_energy_last_then_legacy():
    row = extract_metrics_for_db({"energy_last": 12.3}, "CKPG1", "R")
    assert row["energy"] == 12.3
    assert row["meter_energy_kwh"] == 12.3
    row2 = extract_metrics_for_db({"total_energy": 8.0}, "CKPG1", "R")
    assert row2["energy"] == 8.0


def test_payload_hash_stable_and_order_independent():
    a = compute_payload_hash({"b": 2, "a": 1})
    b = compute_payload_hash({"a": 1, "b": 2})
    assert a == b
    assert len(a) == 64


def test_late_replay_duplicate_is_noop():
    payload = _contract_payload()
    topic = "energy/3phase/CKPG1/phase/R/data"
    cur = FakeCursor()
    first = persist_mqtt_message(cur, topic, dict(payload))
    second = persist_mqtt_message(cur, topic, dict(payload))
    assert first == "inserted"
    assert second == "duplicate"
    assert len(cur.rows) == 1


def test_same_period_end_duplicate_is_noop():
    cur = FakeCursor()
    a = _contract_payload(meter_energy_kwh=10.0, is_retry=False)
    b = _contract_payload(meter_energy_kwh=10.0, is_retry=True, wifi_rssi=-70)
    first = persist_pzem_reading(cur, a, "CKPG1", "R", None)
    second = persist_pzem_reading(cur, b, "CKPG1", "R", None)
    assert first == "inserted"
    assert second == "duplicate"
    assert len(cur.rows) == 1


def test_heartbeat_routed_not_as_data():
    cur = FakeCursor()
    result = persist_mqtt_message(
        cur,
        "energy/3phase/CKPG1/phase/R/heartbeat",
        {"pzem_connected": True, "buffer_count": 2, "pzem_read_errors": 0},
    )
    assert result == "heartbeat"
    assert not any("insert into pzem_data" in sql.lower() for sql in cur.sqls)


def test_wrap_event_sql_emitted():
    cur = FakeCursor()
    persist_pzem_reading(
        cur,
        _contract_payload(energy_event="wrap", meter_energy_kwh=0.2),
        "CKPG1",
        "R",
        None,
    )
    joined = "\n".join(cur.sqls).lower()
    assert "pzem_energy_events" in joined

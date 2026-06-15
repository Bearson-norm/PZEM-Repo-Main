"""Load/save pengaturan tarif PLN dari database (prioritas) atau environment."""
from __future__ import annotations

import logging
import os
from typing import Any, Dict, Optional

import psycopg2

from pln_calculator import PLNTariffCalculator, calculate_pln_bill

logger = logging.getLogger(__name__)

VALID_TARIFF_CLASSES = frozenset({"R1", "R2", "B2", "I3"})

TARIFF_OPTIONS = [
    {
        "id": "R1",
        "label": "R1 — Rumah Tangga (≤ 2.200 VA)",
        "description": "Blok 0–900 kWh @ Rp 1.352, >900 kWh @ Rp 1.445. Abonemen Rp 11.000/bulan.",
        "needs_contracted_va": False,
    },
    {
        "id": "R2",
        "label": "R2 — Rumah Tangga Daya Besar (> 2.200 VA)",
        "description": "Blok 0–1.300 kWh @ Rp 1.352, >1.300 kWh @ Rp 1.445. Abonemen Rp 20.000/bulan.",
        "needs_contracted_va": False,
    },
    {
        "id": "B2",
        "label": "B2 — Bisnis B-2/TR (6.600 VA – 200 kVA)",
        "description": "Tarif flat Rp 1.444,7/kWh. Rekening Minimum = 40 jam × kVA × tarif.",
        "needs_contracted_va": True,
        "default_contracted_va": 53000,
        "va_min": 6600,
        "va_max": 200000,
    },
    {
        "id": "I3",
        "label": "I3 — Industri (tarif flat)",
        "description": "Tarif flat Rp 1.699/kWh. Abonemen Rp 40.000/bulan.",
        "needs_contracted_va": False,
    },
]

DEFAULT_SETTINGS: Dict[str, Any] = {
    "tariff_class": "B2",
    "contracted_va": 53000,
    "ppn_percent": 0.11,
}

DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "database": os.getenv("DB_NAME", "pzem_monitoring"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASS", "Admin123"),
    "connect_timeout": 5,
}


def _option_for(tariff_class: str) -> Dict[str, Any]:
    for opt in TARIFF_OPTIONS:
        if opt["id"] == tariff_class:
            return opt
    return {}


def settings_from_env() -> Dict[str, Any]:
    """Baca pengaturan dari environment variables."""
    tariff_class = os.getenv("PLN_TARIFF_CLASS", DEFAULT_SETTINGS["tariff_class"]).upper()
    if tariff_class not in VALID_TARIFF_CLASSES:
        tariff_class = DEFAULT_SETTINGS["tariff_class"]

    ppn_raw = os.getenv("PLN_PPN_PERCENT")
    ppn_percent = float(ppn_raw) if ppn_raw else DEFAULT_SETTINGS["ppn_percent"]

    contracted_va = None
    va_raw = os.getenv("PLN_CONTRACTED_VA")
    if va_raw:
        contracted_va = int(float(va_raw))
    elif _option_for(tariff_class).get("needs_contracted_va"):
        contracted_va = DEFAULT_SETTINGS["contracted_va"]

    return {
        "tariff_class": tariff_class,
        "contracted_va": contracted_va,
        "ppn_percent": ppn_percent,
        "source": "environment",
    }


def _normalize_settings(raw: Dict[str, Any]) -> Dict[str, Any]:
    tariff_class = str(raw.get("tariff_class", DEFAULT_SETTINGS["tariff_class"])).upper()
    if tariff_class not in VALID_TARIFF_CLASSES:
        raise ValueError(f"Golongan tarif tidak valid: {tariff_class}. Pilih: R1, R2, B2, I3")

    ppn_percent = float(raw.get("ppn_percent", DEFAULT_SETTINGS["ppn_percent"]))
    if ppn_percent > 1:
        ppn_percent = ppn_percent / 100.0
    if ppn_percent < 0 or ppn_percent > 1:
        raise ValueError("PPN harus antara 0% dan 100%")

    option = _option_for(tariff_class)
    contracted_va = raw.get("contracted_va")
    if option.get("needs_contracted_va"):
        if contracted_va is None or contracted_va == "":
            contracted_va = option.get("default_contracted_va", DEFAULT_SETTINGS["contracted_va"])
        contracted_va = int(float(contracted_va))
        va_min = int(option.get("va_min", 6600))
        va_max = int(option.get("va_max", 200000))
        if contracted_va < va_min or contracted_va > va_max:
            raise ValueError(f"Daya kontrak B2 harus antara {va_min:,} dan {va_max:,} VA")
    else:
        contracted_va = None

    return {
        "tariff_class": tariff_class,
        "contracted_va": contracted_va,
        "ppn_percent": ppn_percent,
    }


def _fetch_from_db(conn) -> Optional[Dict[str, Any]]:
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT tariff_class, contracted_va, ppn_percent, updated_at
            FROM pln_tariff_settings
            WHERE id = 1
            """
        )
        row = cur.fetchone()
    if not row:
        return None
    updated_at = row[3].isoformat() if row[3] is not None and hasattr(row[3], "isoformat") else None
    return {
        "tariff_class": row[0],
        "contracted_va": row[1],
        "ppn_percent": float(row[2]),
        "updated_at": updated_at,
        "source": "database",
    }


def load_settings(conn=None, db_manager=None) -> Dict[str, Any]:
    """Muat pengaturan: database → environment → default."""
    if db_manager is not None:
        with db_manager.pool_connection() as c:
            try:
                row = _fetch_from_db(c)
                if row:
                    return row
            except Exception as exc:
                logger.debug("load_settings via db_manager: %s", exc)

    if conn is not None:
        try:
            row = _fetch_from_db(conn)
            if row:
                return row
        except Exception as exc:
            logger.debug("load_settings via conn: %s", exc)

    try:
        with psycopg2.connect(**DB_CONFIG) as c:
            row = _fetch_from_db(c)
            if row:
                return row
    except Exception as exc:
        logger.debug("load_settings standalone: %s", exc)

    return settings_from_env()


def save_settings(settings: Dict[str, Any], conn=None, db_manager=None) -> Dict[str, Any]:
    """Simpan pengaturan ke database."""
    normalized = _normalize_settings(settings)

    sql = """
        INSERT INTO pln_tariff_settings (id, tariff_class, contracted_va, ppn_percent, updated_at)
        VALUES (1, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (id) DO UPDATE SET
            tariff_class = EXCLUDED.tariff_class,
            contracted_va = EXCLUDED.contracted_va,
            ppn_percent = EXCLUDED.ppn_percent,
            updated_at = CURRENT_TIMESTAMP
        RETURNING tariff_class, contracted_va, ppn_percent, updated_at
    """
    params = (
        normalized["tariff_class"],
        normalized["contracted_va"],
        normalized["ppn_percent"],
    )

    def _save(c):
        with c.cursor() as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
        c.commit()
        updated_at = row[3].isoformat() if row[3] is not None and hasattr(row[3], "isoformat") else None
        return {
            "tariff_class": row[0],
            "contracted_va": row[1],
            "ppn_percent": float(row[2]),
            "updated_at": updated_at,
            "source": "database",
        }

    if db_manager is not None:
        with db_manager.pool_connection() as c:
            return _save(c)
    if conn is not None:
        return _save(conn)

    with psycopg2.connect(**DB_CONFIG) as c:
        return _save(c)


def get_calculator(
    settings: Optional[Dict[str, Any]] = None,
    conn=None,
    db_manager=None,
    **overrides,
) -> PLNTariffCalculator:
    """Buat kalkulator dari pengaturan tersimpan."""
    base = dict(load_settings(conn=conn, db_manager=db_manager))
    base.update({k: v for k, v in overrides.items() if v is not None})
    normalized = _normalize_settings(base)
    return PLNTariffCalculator(
        tariff_class=normalized["tariff_class"],
        ppn_percent=normalized["ppn_percent"],
        contracted_va=normalized["contracted_va"],
    )


def calculate_bill_resolved(
    energy_kwh: float,
    conn=None,
    db_manager=None,
    **overrides,
) -> Dict[str, Any]:
    """Hitung tagihan menggunakan pengaturan tersimpan."""
    base = dict(load_settings(conn=conn, db_manager=db_manager))
    base.update({k: v for k, v in overrides.items() if v is not None})
    normalized = _normalize_settings(base)
    return calculate_pln_bill(
        energy_kwh,
        tariff_class=normalized["tariff_class"],
        ppn_percent=normalized["ppn_percent"],
        contracted_va=normalized["contracted_va"],
    )


def settings_payload(conn=None, db_manager=None) -> Dict[str, Any]:
    """Payload lengkap untuk API/UI."""
    settings = load_settings(conn=conn, db_manager=db_manager)
    calculator = get_calculator(settings=settings)
    info = calculator.get_tariff_info()
    return {
        "settings": {
            "tariff_class": settings["tariff_class"],
            "contracted_va": settings.get("contracted_va"),
            "ppn_percent": settings["ppn_percent"],
            "ppn_percent_display": round(settings["ppn_percent"] * 100, 2),
            "source": settings.get("source", "unknown"),
            "updated_at": settings.get("updated_at"),
        },
        "options": TARIFF_OPTIONS,
        "tariff_info": info,
    }

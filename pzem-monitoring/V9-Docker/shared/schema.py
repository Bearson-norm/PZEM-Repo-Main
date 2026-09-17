"""Load and apply shared SQL migrations (used by dashboard and mqtt-listener)."""
from __future__ import annotations

import logging
import os
from typing import List, Optional

logger = logging.getLogger(__name__)

_SQL_NAMES = (
    "004_pln_bill_match.sql",
    "005_firmware_v12_derive.sql",
)


def _schema_candidates(sql_name: str) -> List[str]:
    here = os.path.dirname(os.path.abspath(__file__))
    return [
        os.path.join(here, "sql", sql_name),
        os.path.join(here, "..", "dashboard", "migrations", sql_name),
        os.path.join(here, "migrations", sql_name),
    ]


def pln_bill_match_schema_path() -> Optional[str]:
    for path in _schema_candidates(_SQL_NAMES[0]):
        if os.path.isfile(path):
            return os.path.normpath(path)
    return None


def _schema_path(sql_name: str) -> Optional[str]:
    for path in _schema_candidates(sql_name):
        if os.path.isfile(path):
            return os.path.normpath(path)
    return None


def apply_pln_bill_match_schema(cursor) -> bool:
    """Execute PLN bill-match DDL (004 then 005). Returns True if any SQL ran."""
    applied = False
    for sql_name in _SQL_NAMES:
        path = _schema_path(sql_name)
        if not path:
            logger.warning("PLN schema file not found (%s)", sql_name)
            continue
        with open(path, "r", encoding="utf-8") as f:
            sql = f.read()
        cursor.execute(sql)
        logger.info("Applied PLN schema from %s", path)
        applied = True
    return applied

"""Load and apply shared SQL migrations (used by dashboard and mqtt-listener)."""
from __future__ import annotations

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_SQL_NAME = "004_pln_bill_match.sql"


def pln_bill_match_schema_path() -> Optional[str]:
    here = os.path.dirname(os.path.abspath(__file__))
    candidates = [
        os.path.join(here, "sql", _SQL_NAME),
        os.path.join(here, "..", "dashboard", "migrations", _SQL_NAME),
        os.path.join(here, "migrations", _SQL_NAME),
    ]
    for path in candidates:
        if os.path.isfile(path):
            return os.path.normpath(path)
    return None


def apply_pln_bill_match_schema(cursor) -> bool:
    """Execute 004 PLN bill-match DDL. Returns True if SQL was found and run."""
    path = pln_bill_match_schema_path()
    if not path:
        logger.warning("PLN bill-match schema file not found (%s)", _SQL_NAME)
        return False
    with open(path, "r", encoding="utf-8") as f:
        sql = f.read()
    cursor.execute(sql)
    logger.info("Applied PLN bill-match schema from %s", path)
    return True

"""Write cleaned tables to PostgreSQL. Loading the same hour twice is safe."""

import logging
import os

import pandas as pd
import polars as pl
from sqlalchemy import MetaData, Table, create_engine
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.engine import URL, Engine

from airquality import config

log = logging.getLogger(__name__)


def get_engine() -> Engine:
    """A connection pool built from the POSTGRES_* settings."""
    url = URL.create(
        "postgresql+psycopg2",
        username=config.require_env("POSTGRES_USER"),
        password=config.require_env("POSTGRES_PASSWORD"),
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5433")),
        database=os.getenv("POSTGRES_DB", "airquality"),
    )
    return create_engine(url, pool_pre_ping=True)


def to_records(table: pd.DataFrame | pl.DataFrame | list[dict]) -> list[dict]:
    """Rows as dictionaries, with every missing value turned into None.

    The database driver writes None as NULL. A pandas NaN would be stored as the
    number "NaN", which silently breaks averages later.
    """
    if isinstance(table, list):
        return table
    if isinstance(table, pl.DataFrame):
        return table.to_dicts()
    return table.astype(object).where(table.notna(), None).to_dict("records")


def upsert(
    table: pd.DataFrame | pl.DataFrame | list[dict],
    table_name: str,
    key_columns: list[str],
    engine: Engine,
    schema: str = "raw",
) -> int:
    """Insert rows; where the key already exists, overwrite the other columns.

    This is what makes the pipeline idempotent: re-running an hour, a day or a whole
    backfill leaves exactly one row per key.
    """
    rows = to_records(table)
    if not rows:
        log.info("%s.%s: nothing to load", schema, table_name)
        return 0

    target = Table(table_name, MetaData(), schema=schema, autoload_with=engine)
    statement = insert(target)
    updates = {name: statement.excluded[name] for name in rows[0] if name not in key_columns}
    if updates:
        statement = statement.on_conflict_do_update(index_elements=key_columns, set_=updates)
    else:
        statement = statement.on_conflict_do_nothing(index_elements=key_columns)

    with engine.begin() as connection:  # one transaction: all rows or none
        connection.execute(statement, rows)
    log.info("%s.%s: loaded %d rows", schema, table_name, len(rows))
    return len(rows)

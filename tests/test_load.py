"""Offline check for the loader: missing values must become NULL, never the text "NaN".

The idempotence check (load twice, count once) needs the running database, so it is
done by hand in the guide, not here.
"""

import pandas as pd
import polars as pl

from airquality.load.postgres import to_records


def test_pandas_nan_becomes_none_so_it_is_stored_as_null():
    table = pd.DataFrame({"sensor_id": [1, 2], "value": [10.5, float("nan")]})
    rows = to_records(table)
    assert rows[0]["value"] == 10.5
    assert rows[1]["value"] is None


def test_polars_rows_pass_through_unchanged():
    table = pl.DataFrame({"sensor_id": [1], "value": [None]})
    assert to_records(table) == [{"sensor_id": 1, "value": None}]

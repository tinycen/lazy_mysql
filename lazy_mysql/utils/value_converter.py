import json
import math
from datetime import date, datetime, time
from decimal import Decimal

import pandas as pd


def _is_missing_value(value):
    return (
        value is None
        or value is pd.NA
        or value is pd.NaT
        or (isinstance(value, float) and math.isnan(value))
    )


def _is_numpy_value(value):
    return type(value).__module__.split('.')[0] == 'numpy'


def _is_pandas_list_like(value):
    return (
        type(value).__module__.split('.')[0] == 'pandas'
        and hasattr(value, 'tolist')
        and not isinstance(value, (pd.Timestamp, pd.Timedelta))
    )





def _normalize_json_value(value):
    if _is_missing_value(value):
        return None

    if _is_numpy_value(value):
        if hasattr(value, 'item'):
            try:
                return _normalize_json_value(value.item())
            except ValueError:
                pass
        if hasattr(value, 'tolist'):
            return _normalize_json_value(value.tolist())

    if isinstance(value, pd.Timestamp):
        return value.isoformat(sep=' ')

    if isinstance(value, pd.Timedelta):
        return str(value)

    if isinstance(value, datetime):
        return value.isoformat(sep=' ')

    if isinstance(value, (date, time)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, (bytes, bytearray, memoryview)):
        return bytes(value).decode('utf-8', errors='replace')

    if _is_pandas_list_like(value):
        return _normalize_json_value(value.tolist())

    if isinstance(value, dict):
        return {key: _normalize_json_value(item) for key, item in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_normalize_json_value(item) for item in value]


    return value


def prepare_db_value(value):
    if _is_missing_value(value):
        return None

    if _is_numpy_value(value):
        if hasattr(value, 'item'):
            try:
                return prepare_db_value(value.item())
            except ValueError:
                pass
        if hasattr(value, 'tolist'):
            return prepare_db_value(value.tolist())

    if isinstance(value, pd.Timestamp):
        return value.to_pydatetime()

    if isinstance(value, pd.Timedelta):
        return str(value)

    if _is_pandas_list_like(value):
        return json.dumps(_normalize_json_value(value.tolist()), ensure_ascii=False)

    if isinstance(value, dict):

        return json.dumps(
            _normalize_json_value(value),
            ensure_ascii=False,
            sort_keys=False,
        )

    if isinstance(value, (list, tuple, set)):
        return json.dumps(_normalize_json_value(value), ensure_ascii=False)

    if isinstance(value, (bytearray, memoryview)):
        return bytes(value)

    return value


def prepare_db_row(row):
    return {field: prepare_db_value(value) for field, value in row.items()}

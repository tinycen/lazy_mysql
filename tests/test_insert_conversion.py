import json
import tempfile
from datetime import datetime

import pandas as pd

from lazy_mysql import insert, upsert
from lazy_mysql.crud.insert import _executemany_optimized, _bulk_insert_load_data
from lazy_mysql.utils.value_converter import prepare_db_value



class DummyExecutor:
    def __init__(self):
        self.calls = []
        self.closed = False

    def execute(self, sql, params=None, commit=False, self_close=False):
        self.calls.append({
            'sql': sql,
            'params': params,
            'commit': commit,
            'self_close': self_close,
        })

    def close(self):
        self.closed = True


def test_insert_single_record_auto_converts_python_values():
    executor = DummyExecutor()
    record = {
        'track_no': 'A001',
        'tags': ['urgent', 'fragile'],
        'payload': {'carrier': 'SF', 'retry': 1},
        'created_at': pd.Timestamp('2026-04-22 12:30:00'),
        'finished_at': pd.NaT,
    }

    inserted_count = insert(executor, 'logistics_track', record, commit=True)

    assert inserted_count == 1
    assert len(executor.calls) == 1

    params = executor.calls[0]['params']
    assert params[0] == 'A001'
    assert json.loads(params[1]) == ['urgent', 'fragile']
    assert json.loads(params[2]) == {'carrier': 'SF', 'retry': 1}
    assert params[3] == datetime(2026, 4, 22, 12, 30)
    assert params[4] is None


def test_insert_small_batch_auto_converts_python_values():
    executor = DummyExecutor()
    records = [
        {
            'track_no': 'A001',
            'tags': ['urgent', 'fragile'],
            'payload': {'carrier': 'SF', 'retry': 1},
            'created_at': pd.Timestamp('2026-04-22 12:30:00'),
            'finished_at': pd.NaT,
        }
    ]

    inserted_count = insert(executor, 'logistics_track', records, commit=True)

    assert inserted_count == 1
    assert len(executor.calls) == 1

    params = executor.calls[0]['params']
    assert len(params) == 1
    assert params[0][0] == 'A001'
    assert json.loads(params[0][1]) == ['urgent', 'fragile']
    assert json.loads(params[0][2]) == {'carrier': 'SF', 'retry': 1}
    assert params[0][3] == datetime(2026, 4, 22, 12, 30)
    assert params[0][4] is None



def test_optimized_insert_auto_converts_python_values():
    executor = DummyExecutor()
    records = [
        {
            'track_no': 'A001',
            'tags': ['urgent'],
            'created_at': pd.Timestamp('2026-04-22 12:30:00'),
            'finished_at': pd.NaT,
        },
        {
            'track_no': 'A002',
            'tags': ['signed'],
            'created_at': pd.Timestamp('2026-04-22 13:00:00'),
            'finished_at': pd.NA,
        },
    ]

    inserted_count = _executemany_optimized(
        executor,
        'logistics_track',
        records,
        commit=True,
        batch_size=1,
    )

    assert inserted_count == 2
    assert len(executor.calls) == 2

    first_batch = executor.calls[0]['params']
    second_batch = executor.calls[1]['params']

    assert json.loads(first_batch[0][1]) == ['urgent']
    assert first_batch[0][2] == datetime(2026, 4, 22, 12, 30)
    assert first_batch[0][3] is None

    assert json.loads(second_batch[0][1]) == ['signed']
    assert second_batch[0][2] == datetime(2026, 4, 22, 13, 0)
    assert second_batch[0][3] is None


def test_upsert_single_record_auto_converts_python_values():
    executor = DummyExecutor()
    record = {
        'id': 1,
        'tags': ['urgent'],
        'payload': {'carrier': 'SF'},
        'created_at': pd.Timestamp('2026-04-22 12:30:00'),
    }

    upserted_count = upsert(executor, 'logistics_track', record, commit=True)

    assert upserted_count == 1
    assert len(executor.calls) == 1

    params = executor.calls[0]['params']
    assert params[0] == 1
    assert json.loads(params[1]) == ['urgent']
    assert json.loads(params[2]) == {'carrier': 'SF'}
    assert params[3] == datetime(2026, 4, 22, 12, 30)


def test_upsert_batch_auto_converts_python_values():
    executor = DummyExecutor()
    records = [
        {
            'id': 1,
            'tags': ['urgent'],
            'payload': {'carrier': 'SF'},
            'created_at': pd.Timestamp('2026-04-22 12:30:00'),
        },
        {
            'id': 2,
            'tags': ['signed'],
            'payload': {'carrier': 'YTO'},
            'created_at': pd.Timestamp('2026-04-22 13:00:00'),
        },
    ]

    upserted_count = upsert(executor, 'logistics_track', records, commit=True)

    assert upserted_count == 2
    assert len(executor.calls) == 1

    params = executor.calls[0]['params']
    assert json.loads(params[0][1]) == ['urgent']
    assert json.loads(params[0][2]) == {'carrier': 'SF'}
    assert params[0][3] == datetime(2026, 4, 22, 12, 30)

    assert json.loads(params[1][1]) == ['signed']
    assert json.loads(params[1][2]) == {'carrier': 'YTO'}
    assert params[1][3] == datetime(2026, 4, 22, 13, 0)


def test_prepare_db_value_supports_pandas_list_like_values():
    index_value = prepare_db_value(pd.Index(['urgent', 'fragile']))
    array_value = prepare_db_value(pd.array([1, pd.NA], dtype='Int64'))

    assert isinstance(index_value, str)
    assert isinstance(array_value, str)
    assert json.loads(index_value) == ['urgent', 'fragile']
    assert json.loads(array_value) == [1, None]




def test_bulk_insert_load_data_puts_ignore_in_valid_position():

    executor = DummyExecutor()
    records = [
        {'id': 1, 'payload': {'carrier': 'SF'}},
        {'id': 2, 'payload': {'carrier': 'YTO'}},
    ]

    with tempfile.TemporaryDirectory() as temp_dir:
        inserted_count = _bulk_insert_load_data(
            executor,
            'logistics_track',
            records,
            skip_duplicate=True,
            commit=True,
            batch_size=10,
            temp_dir=temp_dir,
        )

    assert inserted_count == 2
    assert len(executor.calls) == 1
    sql = ' '.join(executor.calls[0]['sql'].split())
    assert 'LOAD DATA LOCAL INFILE' in sql
    assert 'IGNORE INTO TABLE logistics_track' in sql




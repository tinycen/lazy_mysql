import json
from datetime import datetime

import pandas as pd

from lazy_mysql.utils.update.batch_update import batch_update
from lazy_mysql.utils.update.update import update


class DummyCursor:
    def __init__(self):
        self.rowcount = 1


class DummyExecutor:
    def __init__(self):
        self.calls = []
        self.closed = False
        self.mycursor = DummyCursor()

    def execute(self, sql, params=None, commit=False, self_close=False):
        self.calls.append({
            'sql': sql,
            'params': params,
            'commit': commit,
            'self_close': self_close,
        })

    def close(self):
        self.closed = True


def test_update_uses_shared_value_converter():
    executor = DummyExecutor()

    update(
        executor,
        'logistics_track',
        {
            'tags': ['urgent', 'fragile'],
            'payload': {'carrier': 'SF', 'retry': 1},
            'updated_at': pd.Timestamp('2026-04-22 12:30:00'),
            'finished_at': pd.NaT,
        },
        {'id': 1},
        commit=True,
    )

    assert len(executor.calls) == 1
    params = executor.calls[0]['params']

    assert json.loads(params[0]) == ['urgent', 'fragile']
    assert json.loads(params[1]) == {'carrier': 'SF', 'retry': 1}
    assert params[2] == datetime(2026, 4, 22, 12, 30)
    assert params[3] is None
    assert params[4] == 1


def test_batch_update_uses_shared_value_converter_in_simple_case():
    executor = DummyExecutor()

    batch_update(
        executor,
        'logistics_track',
        [
            {
                'conditions': {'id': 1},
                'fields': {
                    'payload': {'carrier': 'SF'},
                    'updated_at': pd.Timestamp('2026-04-22 12:30:00'),
                    'finished_at': pd.NaT,
                },
            },
            {
                'conditions': {'id': 2},
                'fields': {
                    'payload': {'carrier': 'YTO'},
                    'updated_at': pd.Timestamp('2026-04-22 13:00:00'),
                    'finished_at': pd.NA,
                },
            },
        ],
        commit=True,
    )

    assert len(executor.calls) == 1
    params = executor.calls[0]['params']

    assert params[0] == 1
    assert json.loads(params[1]) == {'carrier': 'SF'}
    assert params[2] == 2
    assert json.loads(params[3]) == {'carrier': 'YTO'}

    assert params[4] == 1
    assert params[5] == datetime(2026, 4, 22, 12, 30)
    assert params[6] == 2
    assert params[7] == datetime(2026, 4, 22, 13, 0)

    assert params[8] == 1
    assert params[9] is None
    assert params[10] == 2
    assert params[11] is None

    assert params[12] == 1
    assert params[13] == 2


def test_batch_update_uses_shared_value_converter_in_complex_case():
    executor = DummyExecutor()

    batch_update(
        executor,
        'logistics_track',
        [
            {
                'conditions': {'order_id': 'A001', 'platform': 'Qoo10'},
                'fields': {
                    'payload': {'carrier': 'SF'},
                    'updated_at': pd.Timestamp('2026-04-22 12:30:00'),
                },
            },
            {
                'conditions': {'order_id': 'A002', 'platform': 'Shopify'},
                'fields': {
                    'payload': {'carrier': 'YTO'},
                    'updated_at': pd.Timestamp('2026-04-22 13:00:00'),
                },
            },
        ],
        commit=True,
    )

    assert len(executor.calls) == 1
    params = executor.calls[0]['params']

    assert params[0] == 'A001'
    assert params[1] == 'Qoo10'
    assert json.loads(params[2]) == {'carrier': 'SF'}
    assert params[3] == 'A002'
    assert params[4] == 'Shopify'
    assert json.loads(params[5]) == {'carrier': 'YTO'}

    assert params[6] == 'A001'
    assert params[7] == 'Qoo10'
    assert params[8] == datetime(2026, 4, 22, 12, 30)
    assert params[9] == 'A002'
    assert params[10] == 'Shopify'
    assert params[11] == datetime(2026, 4, 22, 13, 0)


def test_update_rejects_empty_conditions():
    executor = DummyExecutor()

    try:
        update(executor, 'logistics_track', {'status': 'done'}, {}, commit=True)
        raise AssertionError('expected ValueError for empty conditions')
    except ValueError as exc:
        assert str(exc) == 'conditions 不能为空，这会导致更新所有记录'

    assert executor.calls == []


def test_batch_update_rejects_empty_fields():
    executor = DummyExecutor()

    try:
        batch_update(
            executor,
            'logistics_track',
            [{'conditions': {'id': 1}, 'fields': {}}],
            commit=True,
        )
        raise AssertionError('expected ValueError for empty fields')
    except ValueError as exc:
        assert str(exc) == 'fields 不能为空'

    assert executor.calls == []


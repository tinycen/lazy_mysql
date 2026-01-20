"""
Tests for batch_update functionality
"""
import pytest
from lazy_mysql.utils.update.batch_update import (
    _build_complex_update_sql,
    _build_simple_update_sql,
    _check_simple_case
)
import pandas as pd


def test_complex_batch_update_parameter_order():
    """
    Test that parameters are in correct order for complex batch update
    
    The SQL should be:
    UPDATE table SET field = CASE WHEN cond1 = %s AND cond2 = %s THEN %s ...
    
    And params should be:
    (cond1_value, cond2_value, field_value, ...)
    NOT (field_value, cond1_value, cond2_value, ...)
    """
    update_list = [
        {
            'conditions': {'order_id': '1143212438', 'platform': 'Qoo10_ja', 'shop_name': 'shun_ni'},
            'fields': {'estimate_ship_at': '2026-01-22 23:59:59'}
        },
        {
            'conditions': {'order_id': '1143275182', 'platform': 'Qoo10_ja', 'shop_name': 'fortune_awaits'},
            'fields': {'estimate_ship_at': '2026-01-22 23:59:59'}
        }
    ]
    
    all_fields = ['estimate_ship_at']
    
    sql, params = _build_complex_update_sql('order_info', update_list, all_fields)
    
    # The SQL should contain WHEN conditions followed by THEN
    assert 'WHEN' in sql
    assert 'THEN' in sql
    assert 'CASE' in sql
    
    # Check parameter order
    # For the first WHEN clause, the parameters should be:
    # order_id, platform, shop_name (WHERE params), then estimate_ship_at (THEN value)
    
    # The params should start with the SET clause parameters
    # For first record: order_id='1143212438', platform='Qoo10_ja', shop_name='shun_ni', 
    # THEN estimate_ship_at='2026-01-22 23:59:59'
    
    # Extract SET clause params (before WHERE clause params)
    # Expected order in SET clause for each CASE WHEN:
    # WHERE params (order_id, platform, shop_name), THEN value (estimate_ship_at)
    
    # Total params: 
    # SET clause: 2 records * (3 WHERE params + 1 THEN value) = 8 params
    # WHERE clause: 2 records * 3 WHERE params = 6 params
    # Total: 14 params
    assert len(params) == 14
    
    # The first 4 params should be for the first CASE WHEN in SET clause:
    # order_id, platform, shop_name, estimate_ship_at
    assert params[0] == '1143212438', f"Expected order_id first, got {params[0]}"
    assert params[1] == 'Qoo10_ja', f"Expected platform second, got {params[1]}"
    assert params[2] == 'shun_ni', f"Expected shop_name third, got {params[2]}"
    assert params[3] == '2026-01-22 23:59:59', f"Expected estimate_ship_at fourth, got {params[3]}"
    
    # The next 4 params should be for the second CASE WHEN in SET clause:
    # order_id, platform, shop_name, estimate_ship_at
    assert params[4] == '1143275182'
    assert params[5] == 'Qoo10_ja'
    assert params[6] == 'fortune_awaits'
    assert params[7] == '2026-01-22 23:59:59'
    
    # The last 6 params are for the WHERE clause (2 records * 3 params each)
    assert params[8] == '1143212438'
    assert params[9] == 'Qoo10_ja'
    assert params[10] == 'shun_ni'
    assert params[11] == '1143275182'
    assert params[12] == 'Qoo10_ja'
    assert params[13] == 'fortune_awaits'


def test_simple_batch_update_parameter_order():
    """
    Test that parameters are in correct order for simple batch update (single condition field)
    """
    update_list = [
        {'conditions': {'id': 1}, 'fields': {'name': 'Alice', 'age': 25}},
        {'conditions': {'id': 2}, 'fields': {'name': 'Bob', 'age': 30}}
    ]
    
    all_fields = ['name', 'age']
    key_field = 'id'
    df_conditions = pd.DataFrame([item['conditions'] for item in update_list])
    
    sql, params = _build_simple_update_sql('users', update_list, all_fields, key_field, df_conditions)
    
    # SQL should use CASE key_field WHEN pattern
    assert 'CASE id' in sql
    assert 'WHEN' in sql
    assert 'THEN' in sql
    
    # Parameters should be in order:
    # SET clause: (key1, value1, key2, value2, ...) for each field
    # WHERE clause: (key1, key2, ...)
    
    # For name field: id=1, name='Alice', id=2, name='Bob'
    # For age field: id=1, age=25, id=2, age=30
    # WHERE IN: id=1, id=2
    
    # Total: 2 + 2 + 2 + 2 + 2 = 10 params
    assert len(params) == 10
    
    # First field (name) params
    assert params[0] == 1  # id for first WHEN
    assert params[1] == 'Alice'  # name value
    assert params[2] == 2  # id for second WHEN
    assert params[3] == 'Bob'  # name value
    
    # Second field (age) params
    assert params[4] == 1  # id for first WHEN
    assert params[5] == 25  # age value
    assert params[6] == 2  # id for second WHEN
    assert params[7] == 30  # age value
    
    # WHERE IN clause params
    assert params[8] == 1
    assert params[9] == 2


def test_check_simple_case():
    """Test the logic for detecting simple case (single condition field)"""
    # Single condition field - should be simple case
    df_simple = pd.DataFrame([{'id': 1}, {'id': 2}])
    is_simple, key_field = _check_simple_case(df_simple)
    assert is_simple is True
    assert key_field == 'id'
    
    # Multiple condition fields - should not be simple case
    df_complex = pd.DataFrame([
        {'id': 1, 'type': 'user'},
        {'id': 2, 'type': 'admin'}
    ])
    is_simple, key_field = _check_simple_case(df_complex)
    assert is_simple is False
    assert key_field is None
    
    # Single condition field with tuple values - should not be simple case
    df_tuple = pd.DataFrame([{'id': ('>', 1)}, {'id': ('>', 2)}])
    is_simple, key_field = _check_simple_case(df_tuple)
    assert is_simple is False
    assert key_field is None


if __name__ == '__main__':
    pytest.main([__file__, '-v'])

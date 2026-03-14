import copy


def _conditions_to_key(conditions):
    """
    将conditions字典转换为可哈希的元组键，用于比较conditions是否相同

    :param conditions: 条件字典
    :return: 可哈希的元组，格式为 ((key1, value1), (key2, value2), ...) 按key排序
    """
    def make_hashable(value):
        if isinstance(value, (list, tuple)):
            return tuple(make_hashable(v) for v in value)
        if isinstance(value, dict):
            return tuple(sorted((k, make_hashable(v)) for k, v in value.items()))
        return value

    return tuple(sorted((k, make_hashable(v)) for k, v in conditions.items()))


def merge_update_lists(*update_lists, on_conflict='error'):
    """
    合并多个update_list，根据conditions合并fields

    合并规则：
    1. 如果conditions完全相同（无论是否在同一个update_list内），则合并fields
    2. 如果fields中有重复字段但值相同，跳过该字段
    3. 如果fields中有重复字段但值不同，根据on_conflict参数处理

    :param update_lists: 一个或多个update_list
    :param on_conflict: 冲突处理策略：
        - 'error'：抛出异常（默认）
        - 'skip'：保留先出现的值
        - 'override'：使用后出现的值覆盖（同一列表内后面的条目覆盖前面的，
                      跨列表时后传入的列表覆盖先传入的）
    :return: 合并后的update_list，fields和conditions均为深拷贝，不影响原始数据

    :example:
        >>> list1 = [{'fields': {'name': '张三'}, 'conditions': {'id': 1}}]
        >>> list2 = [{'fields': {'age': 25}, 'conditions': {'id': 1}}]
        >>> merge_update_lists(list1, list2)
        [{'fields': {'name': '张三', 'age': 25}, 'conditions': {'id': 1}}]

        # 冲突示例
        >>> list3 = [{'fields': {'name': '李四'}, 'conditions': {'id': 1}}]
        >>> merge_update_lists(list1, list3)  # 抛出异常，因为name字段值不同
    """
    if not update_lists:
        return []

    merged = {}

    for update_list in update_lists:
        if not update_list:
            continue

        for item in update_list:
            if 'fields' not in item or 'conditions' not in item:
                raise ValueError("update_list 中每个元素必须包含 'fields' 和 'conditions'")

            conditions = item['conditions']
            fields = item['fields']
            cond_key = _conditions_to_key(conditions)

            if cond_key not in merged:
                merged[cond_key] = {
                    'fields': copy.deepcopy(fields),
                    'conditions': copy.deepcopy(conditions),
                }
            else:
                existing_fields = merged[cond_key]['fields']
                for field_name, field_value in fields.items():
                    if field_name not in existing_fields:
                        existing_fields[field_name] = copy.deepcopy(field_value)
                    elif existing_fields[field_name] == field_value:
                        continue
                    else:
                        if on_conflict == 'error':
                            raise ValueError(
                                f"字段 '{field_name}' 存在冲突: "
                                f"现有值 {repr(existing_fields[field_name])} 与新值 {repr(field_value)} 不同，"
                                f"conditions: {repr(conditions)}"
                            )
                        elif on_conflict == 'override':
                            existing_fields[field_name] = copy.deepcopy(field_value)
                        elif on_conflict == 'skip':
                            continue
                        else:
                            raise ValueError(f"未知的 on_conflict 策略: {repr(on_conflict)}")

    return list(merged.values())
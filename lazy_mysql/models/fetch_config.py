from pydantic import BaseModel, Field
from typing import TYPE_CHECKING, Any, Literal, Union

if TYPE_CHECKING:
    import pandas as pd

FetchMode = Literal["all", "oneTuple", "one"]
OutputFormat = Literal["", "list_1", "df", "df_dict", "dict"]

# 查询结果的基础数据形态（不含 show_count=True 时的 (数据, 数量) 包装）
QueryData = Union[
    list[tuple],      # all + ""（普通游标）
    list[Any],        # all + "list_1" / all + ""（dict_cursor）
    "pd.DataFrame",   # all + "df"
    list[dict],       # all + "df_dict" / all + ""（dict_cursor）
    tuple,            # oneTuple + ""
    dict,             # oneTuple + "dict" / "df_dict" / oneTuple + ""（dict_cursor）
    Any,              # fetch_mode="one"
    None,
]
# 完整查询返回类型：show_count=True 时为 (数据, 数量)
QueryResult = Union[QueryData, "tuple[QueryData, int]"]


class _FetchConfigBase(BaseModel):
    """FetchConfig 系列的公共基类：仅声明与返回形态无关的字段。

    ⚠️ fetch_mode / output_format 只在各叶子类中声明，刻意不在基类声明：
    子类用 Literal 收窄父类可读写字段会触发类型检查器的
    mutable-attribute override 规则（pyright: reportIncompatibleVariableOverride /
    pyrefly: bad-override-mutable-attribute），虽然对 pydantic 属误报
    （运行时由 Pydantic 校验兜底），但拆分声明可从根源规避，无需任何 ignore 注释。
    """

    data_label: list[str] | None = Field(default=None, description="数据标签，用于DataFrame的列名或字典的键名")
    show_count: bool = Field(default=False, description="是否显示查询结果数量")

    def to_dict(self) -> dict:
        """将模型转换为字典，用于兼容旧的字典方式"""
        return self.model_dump()


class FetchConfig(_FetchConfigBase):
    """获取配置类（通用形态），用于控制查询结果的返回格式和行为"""

    fetch_mode: FetchMode = Field(default="all", description="获取模式，控制返回数据的数量")
    output_format: OutputFormat = Field(
        default="",
        description=(
            "输出格式。⚠️ 当 executor 以 dict_cursor=True 初始化时，不支持 'list_1'、'df'、'df_dict'，"
            "仅支持 ''（dict_cursor 下返回字典列表）、'dict'（fetch_mode='oneTuple' 时），否则抛出 ValueError。"
        )
    )


# ---------------------------------------------------------------------------
# FetchConfig 字面量形态类：用于 @overload 精确收窄返回类型
# 用法：executor.select(..., fetch_config=FetchAllDf()) -> pandas.DataFrame
# 与 FetchConfig 平级（共同继承 _FetchConfigBase），字段类型互不覆写
# ---------------------------------------------------------------------------

class FetchAllTuples(_FetchConfigBase):
    """fetch_mode='all' + output_format='' → list[tuple]"""
    fetch_mode: Literal["all"] = "all"
    output_format: Literal[""] = ""


class FetchAllList1(_FetchConfigBase):
    """fetch_mode='all' + output_format='list_1' → list（提取每行第一个字段）"""
    fetch_mode: Literal["all"] = "all"
    output_format: Literal["list_1"] = "list_1"


class FetchAllDf(_FetchConfigBase):
    """fetch_mode='all' + output_format='df' → pandas.DataFrame"""
    fetch_mode: Literal["all"] = "all"
    output_format: Literal["df"] = "df"


class FetchAllDfDict(_FetchConfigBase):
    """fetch_mode='all' + output_format='df_dict' → list[dict]"""
    fetch_mode: Literal["all"] = "all"
    output_format: Literal["df_dict"] = "df_dict"


class FetchOneTuple(_FetchConfigBase):
    """fetch_mode='oneTuple' + output_format='' → tuple | None"""
    fetch_mode: Literal["oneTuple"] = "oneTuple"
    output_format: Literal[""] = ""


class FetchOneDict(_FetchConfigBase):
    """fetch_mode='oneTuple' + output_format='dict' 或 'df_dict' → dict | None
    （普通游标下需提供 data_label；dict_cursor 下直接返回字典游标结果）"""
    fetch_mode: Literal["oneTuple"] = "oneTuple"
    output_format: Literal["dict", "df_dict"] = "dict"


class FetchOne(_FetchConfigBase):
    """fetch_mode='one' → 单个值（Any | None）"""
    fetch_mode: Literal["one"] = "one"


# 所有可接受的 fetch_config 模型形态（用于实现签名与底层函数的参数标注）
FetchConfigLike = Union[
    FetchConfig, FetchAllTuples, FetchAllList1, FetchAllDf, FetchAllDfDict,
    FetchOneTuple, FetchOneDict, FetchOne,
]

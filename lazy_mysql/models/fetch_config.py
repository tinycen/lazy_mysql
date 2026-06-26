from pydantic import BaseModel, Field
from typing import List, Literal, Optional

FetchMode = Literal["all", "oneTuple", "one"]
OutputFormat = Literal["", "list_1", "df", "df_dict"]


class FetchConfig(BaseModel):
    """获取配置类，用于控制查询结果的返回格式和行为"""

    fetch_mode: FetchMode = Field(default="all", description="获取模式，控制返回数据的数量")
    output_format: OutputFormat = Field(default="", description="输出格式")
    data_label: Optional[List[str]] = Field(default=None, description="数据标签，用于DataFrame的列名或字典的键名")
    show_count: bool = Field(default=False, description="是否显示查询结果数量")

    def to_dict(self) -> dict:
        """将模型转换为字典，用于兼容旧的字典方式"""
        return {
            "fetch_mode": self.fetch_mode,
            "output_format": self.output_format,
            "data_label": self.data_label,
            "show_count": self.show_count,
        }

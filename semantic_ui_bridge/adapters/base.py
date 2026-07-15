"""BaseAdapter —— 自适应层的抽象基类"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class BaseAdapter(ABC):
    """所有平台适配器的统一接口。"""

    @abstractmethod
    async def connect(self, url: str, **kwargs: Any) -> None:
        """打开目标页面。"""

    @abstractmethod
    async def disconnect(self) -> None:
        """释放浏览器资源。"""

    @abstractmethod
    async def get_raw_tree(self) -> Dict[str, Any]:
        """返回平台原始语义树（CDP AX tree、AXAPI tree 等）。"""

    @abstractmethod
    async def execute_action(
        self, element_id: str, action: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """执行动作并返回影响范围或结果。"""

"""Semantic UI Bridge —— Protocol 层"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable, Dict, List, Optional

from src.core.models import Action, ActionResult, UIElement, UITree, UIRole
from src.core.errors import SUBTimeoutError

logger = logging.getLogger(__name__)


class SemanticUIBridge:
    """SUB.ui — Agent 的单一入口。"""

    def __init__(self, adapter: Any) -> None:
        # 延迟 import 避免循环依赖（adapter 可能需要 import models）
        self._adapter = adapter
        self._normalizer = None  # 延迟初始化

    # ------------------------------------------------------------------ #
    # 内部：懒初始化 normalizer
    # ------------------------------------------------------------------ #

    def _get_normalizer(self):
        if self._normalizer is None:
            # 延迟 import，避免模型层未 ready 时爆发
            from src.core.normalizer import Normalizer

            self._normalizer = Normalizer()
        return self._normalizer

    # ------------------------------------------------------------------ #
    # 核心 API
    # ------------------------------------------------------------------ #

    async def get_tree(
        self, focused_only: bool = False, **kwargs: Any
    ) -> UITree:
        """返回当前页面的完整语义 UI 树。"""
        if focused_only:
            # 使用 CDP PartialAXTree 缩小范围
            try:
                raw = await self._adapter.get_partial_tree(focused=True)
            except Exception:
                raw = {}
            if not raw:
                # fallback：取全量再裁剪
                raw = await self._adapter.get_raw_tree()
        else:
            raw = await self._adapter.get_raw_tree()

        norm = self._get_normalizer()
        raw["timestamp"] = time.time()  # 注入时间戳
        tree = norm.normalize_tree(raw)

        # 将原始元素 id 写回 UIElement.platform_data，保持向后兼容
        if not kwargs.get("_no_raw"):
            self._annotate_platform_ids(tree.root, raw)

        return tree

    async def find(
        self,
        role: Optional[UIRole] = None,
        label_contains: Optional[str] = None,
        states: Optional[List[str]] = None,
    ) -> List[UIElement]:
        """按条件搜索 UI 元素。"""
        tree = await self.get_tree()
        return self._search(tree.root, role=role, label_contains=label_contains, states=states)

    async def act(self, action: Action) -> ActionResult:
        """执行动作并返回结果树 + diffs。"""
        before = await self.get_tree()

        try:
            result = await self._adapter.execute_action(
                element_id=action.target,
                action=action.action,
                params=action.params or {},
            )
        except SUBTimeoutError:
            raise
        except Exception as exc:
            return ActionResult(
                success=False,
                action=action,
                error=str(exc),
            )

        after = await self.get_tree()
        diff = self._diff(before.root, after.root)
        return ActionResult(
            success=True,
            action=action,
            result_tree=after,
            diff=diff,
        )

    async def wait_for(
        self,
        condition: Callable[[UITree], bool],
        timeout: float = 30.0,
        poll_interval: float = 0.2,
    ) -> UITree:
        """轮询等待某条件满足，超时抛出 SUBTimeoutError。"""
        deadline = time.monotonic() + timeout
        while True:
            tree = await self.get_tree()
            try:
                if condition(tree):
                    return tree
            except Exception:
                pass
            if time.monotonic() >= deadline:
                raise SUBTimeoutError(
                    f"wait_for timeout after {timeout}s (condition unsatisfied)"
                )
            await asyncio.sleep(poll_interval)

    # ------------------------------------------------------------------ #
    # 内部：树操作工具
    # ------------------------------------------------------------------ #

    @staticmethod
    def _search(
        root: UIElement,
        role: Optional[UIRole] = None,
        label: Optional[str] = None,
        label_contains: Optional[str] = None,
        states: Optional[List[str]] = None,
    ) -> List[UIElement]:
        """递归搜索满足条件的节点。"""
        matched: List[UIElement] = []

        role_ok = (role is None) or (root.role == role)
        label_ok = True
        if label is not None:
            label_ok = (root.label == label)
        if label_contains is not None:
            label_ok = (root.label is not None and label_contains in root.label)
        states_ok = True
        if states:
            states_ok = set(states).issubset(set(root.states or []))

        if role_ok and label_ok and states_ok:
            matched.append(root)

        for child in root.children or []:
            matched.extend(
                SemanticUIBridge._search(
                    child,
                    role=role,
                    label=label,
                    label_contains=label_contains,
                    states=states,
                )
            )
        return matched

    @staticmethod
    def _diff(before: UIElement, after: UIElement) -> List[str]:
        """对比两棵子树，返回 diff 描述。"""
        diffs: List[str] = []
        if before.id != after.id:
            return [f"root_id_changed {before.id} -> {after.id}"]
        if before.value != after.value:
            diffs.append(f"value:{before.id} {before.value} -> {after.value}")
        if before.label != after.label:
            diffs.append(f"label:{before.id} {before.label} -> {after.label}")
        if set(before.states or []) != set(after.states or []):
            diffs.append(
                f"states:{before.id} {before.states} -> {after.states}"
            )
        if len(before.children or []) != len(after.children or []):
            diffs.append(
                f"children_count:{before.id} {len(before.children or [])} -> "
                f"{len(after.children or [])}"
            )
        b_ids = {c.id for c in before.children or []}
        a_ids = {c.id for c in after.children or []}
        added = a_ids - b_ids
        removed = b_ids - a_ids
        if added:
            diffs.append(f"added_children:{before.id} {sorted(added)}")
        if removed:
            diffs.append(f"removed_children:{before.id} {sorted(removed)}")

        b_map = {c.id: c for c in before.children or []}
        a_map = {c.id: c for c in after.children or []}
        for cid in b_ids & a_ids:
            diffs.extend(SemanticUIBridge._diff(b_map[cid], a_map[cid]))
        return diffs

    @staticmethod
    def _annotate_platform_ids(
        el: UIElement, raw: Dict[str, Any]
    ) -> None:
        """把原始 AXNode 的 nodeId 写回 platform_data。"""
        if not raw:
            return
        el.platform_data = {
            "nodeId": raw.get("nodeId", raw.get("id")),
            "role": raw.get("role"),
        }
        children_raw = raw.get("children", [])
        child_map: Dict[str, Dict[str, Any]] = {}
        for c in children_raw:
            if isinstance(c, dict):
                key = str(
                    c.get("nodeId", c.get("id", ""))
                )
                if key:
                    child_map[key] = c
        for child in (el.children or []):
            child_raw = child_map.get(child.id)
            if child_raw:
                SemanticUIBridge._annotate_platform_ids(
                    child, child_raw
                )

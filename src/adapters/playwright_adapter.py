"""Semantic UI Bridge —— Playwright/CDP 浏览器适配器"""
from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from playwright.async_api import (
    Browser,
    BrowserContext,
    CDPSession,
    Page,
    Playwright,
    async_playwright,
)

from src.adapters.base import BaseAdapter
from src.core.errors import AdapterError, ElementNotFoundError

logger = logging.getLogger(__name__)


class PlaywrightAdapter(BaseAdapter):
    """基于 Playwright CDP 的浏览器适配器。"""

    def __init__(
        self,
        headless: bool = True,
        cdp_url: Optional[str] = None,
        chromium_executable_path: Optional[str] = None,
    ) -> None:
        self._headless = headless
        self._cdp_url = cdp_url
        self._chromium_executable_path = chromium_executable_path

        self._pw: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        self._cdp: Optional[CDPSession] = None

        # 缓存 nodeId ↔ CSS selector 映射，减少 CDP 重复调用
        self._node_to_selector: Dict[int, str] = {}

    # ------------------------------------------------------------------ #
    # 生命周期
    # ------------------------------------------------------------------ #

    async def connect(self, url: str, **kwargs: Any) -> None:
        await self.disconnect()

        self._pw = await async_playwright().start()

        if self._cdp_url:
            self._browser = await self._pw.chromium.connect(self._cdp_url)
            # 优先复用现有 cdp 连接（如远程 Chrome）
            cdp_sessions = await self._browser.contexts()[0].new_page().context.new_cdp_session(self._browser) if False else []
        else:
            launch_kwargs: Dict[str, Any] = {"headless": self._headless}
            if self._chromium_executable_path:
                launch_kwargs["executable_path"] = self._chromium_executable_path
            self._browser = await self._pw.chromium.launch(**launch_kwargs)

        self._context = await self._browser.new_context()
        self._page = await self._context.new_page()
        await self._page.goto(url, wait_until="domcontentloaded")

        # 建立 CDP 会话
        self._cdp = await self._page.context.new_cdp_session(self._page)
        await self._cdp.send("Accessibility.enable")

    async def disconnect(self) -> None:
        try:
            if self._cdp:
                await self._cdp.detach()
                self._cdp = None
        except Exception:
            pass
        try:
            if self._context:
                await self._context.close()
                self._context = None
        except Exception:
            pass
        try:
            if self._browser:
                await self._browser.close()
                self._browser = None
        except Exception:
            pass
        finally:
            if self._pw:
                await self._pw.stop()
                self._pw = None
            self._page = None
            self._node_to_selector.clear()

    # ------------------------------------------------------------------ #
    # 原始树
    # ------------------------------------------------------------------ #

    async def get_raw_tree(self) -> Dict[str, Any]:
        if not self._cdp or not self._page:
            raise AdapterError("Adapter not connected")

        # 确保有 document nodeId
        root_response = await self._cdp.send("DOM.getDocument", {"depth": 1})
        root_node_id: int = root_response["root"]["nodeId"]

        ax_tree = await self._cdp.send(
            "Accessibility.getFullAXTree",
            {"backendNodeId": root_node_id, "fetchRelatives": True},
        )

        # 兼容不同返回版本：新版为 {"nodes": [...]}；某些版本直接返回 list
        if isinstance(ax_tree, dict):
            return ax_tree
        return {"nodes": ax_tree}

    # ------------------------------------------------------------------ #
    # 动作执行
    # ------------------------------------------------------------------ #

    async def execute_action(
        self,
        element_id: str,
        action: str,
        params: Dict[str, Any],
    ) -> Dict[str, Any]:
        if not self._page:
            raise AdapterError("Adapter not connected")

        locator = await self._build_locator(element_id)
        logger.debug("execute_action id=%s action=%s", element_id, action)

        try:
            if action == "click":
                await locator.click()
            elif action == "type":
                text: str = params.get("text", "")
                await locator.fill(text)
            elif action == "select":
                value: str = params.get("value", "")
                await locator.select_option(value)
            elif action == "focus":
                await locator.focus()
            elif action == "scroll":
                x = params.get("x", 0)
                y = params.get("y", 0)
                await locator.evaluate(f"el => el.scrollTo({x}, {y})")
            else:
                raise AdapterError(f"Unsupported action: {action}")
        except Exception as exc:
            raise AdapterError(str(exc)) from exc

        return {"element_id": element_id, "action": action, "status": "ok"}

    # ------------------------------------------------------------------ #
    # 内部：ElementId → locator
    # ------------------------------------------------------------------ #

    async def _build_locator(self, element_id: str):
            if not self._cdp or not self._page:
                raise AdapterError("Adapter not connected")

            raw = await self.get_raw_tree()
            nodes = raw.get("nodes", [raw] if isinstance(raw, dict) else [raw])
            ax_node = self._find_node_by_id(nodes, element_id)
            if ax_node is None:
                raise ElementNotFoundError(
                    f"AXNode for element_id={element_id} not found"
                )

            backend_node_id: Optional[int] = (
                ax_node.get("backendDOMNodeId") or ax_node.get("backendNodeId")
            )
            if backend_node_id is not None and backend_node_id in self._node_to_selector:
                cached = self._node_to_selector[backend_node_id]
                if isinstance(cached, str):
                    return self._page.locator(cached)

            # 优先策略：通过 JS 获取 DOM 元素引用 → Playwright locator
            if backend_node_id is not None:
                try:
                    resolved = await self._cdp.send(
                        "DOM.resolveNode", {"backendNodeId": backend_node_id}
                    )
                    object_id = resolved.get("object", {}).get("objectId")
                    if object_id:
                        # 用 Runtime.callFunctionOn 在页面上执行，返回元素的 CSS selector
                        # eval('('+objId+')') 不可行 — 改用存储引用方式
                        result = await self._cdp.send(
                            "Runtime.callFunctionOn",
                            {
                                "objectId": object_id,
                                "functionDeclaration": """
                                    function() {
                                        // this 就是 DOM 元素
                                        const el = this;
                                        if (!el || el.nodeType !== 1) return '';
                                        // 优先 id
                                        if (el.id) return '#' + CSS.escape(el.id);
                                        // 其次：用唯一属性组合
                                        const tag = el.tagName.toLowerCase();
                                        const attrs = [];
                                        if (el.getAttribute('aria-label'))
                                            attrs.push('[aria-label="' + el.getAttribute('aria-label').replace(/"/g, '\\\\"') + '"]');
                                        if (el.getAttribute('placeholder'))
                                            attrs.push('[placeholder="' + el.getAttribute('placeholder').replace(/"/g, '\\\\"') + '"]');
                                        if (el.getAttribute('type'))
                                            attrs.push('[type="' + el.getAttribute('type') + '"]');
                                        if (el.name)
                                            attrs.push('[name="' + el.name + '"]');
                                        if (el.className && typeof el.className === 'string') {
                                            const cls = el.className.trim().split(/\\s+/).filter(c => c).map(c => '.' + CSS.escape(c)).join('');
                                            if (cls) attrs.push(cls);
                                        }
                                        if (attrs.length > 0)
                                            return tag + attrs.join('');
                                        // 最后：文本精确匹配
                                        const text = el.textContent?.trim();
                                        if (text && text.length < 50)
                                            return tag + ':has-text("' + text.replace(/"/g, '\\\\"') + '")';
                                        return '';
                                    }
                                """,
                                "returnByValue": True,
                            },
                        )
                        css = result.get("result", {}).get("value", "")
                        if css:
                            selector = css
                            self._node_to_selector[backend_node_id] = selector
                            return self._page.locator(selector)
                except Exception:
                    pass

            # 兜底策略：通过 role + name 文本匹配
            # 提取 role 值（兼容 dict 和 string）
            role_raw = ax_node.get("role", "")
            if isinstance(role_raw, dict):
                role = role_raw.get("value", "")
            else:
                role = str(role_raw) if role_raw else ""

            # 提取 name 值
            name_val = ax_node.get("name") or ax_node.get("value") or ax_node.get("description")
            if isinstance(name_val, dict):
                name = name_val.get("value", "")
            elif isinstance(name_val, str):
                name = name_val
            else:
                name = ""

            # Playwright 选择器：ARIA 角色 + 可访问名称
            if role and name:
                # 用 Playwright 内置的 getByRole 更可靠
                # 但无法通过 raw selector 表达，所以用多层 fallback
                escaped_name = name.replace('"', '\\"')
                selector_parts = []
                selector_parts.append(f'[aria-label="{escaped_name}"]')
                # 也尝试 role 属性
                if role in ("button", "link", "checkbox", "radio", "textbox", "searchbox",
                           "combobox", "listbox", "slider", "menuitem", "tab", "switch",
                           "option", "gridcell", "row", "columnheader", "rowheader"):
                    selector_parts.append(f'[role="{role}"]')
                # text 匹配
                if len(name) < 50:
                    selector_parts.append(f':has-text("{escaped_name}")')
                selector = ", ".join(selector_parts)
            elif role:
                selector = f'[role="{role}"]'
            elif name:
                selector = f':has-text("{name.replace(chr(34), chr(92)+chr(34))}")'
            else:
                raise ElementNotFoundError(
                    f"Cannot build locator for AXNode: {ax_node.get('nodeId')}"
                )

            if backend_node_id is not None:
                self._node_to_selector[backend_node_id] = selector

            return self._page.locator(selector)

    @staticmethod
    def _find_node_by_id(
        nodes: list[Dict[str, Any]], target_id: str
    ) -> Optional[Dict[str, Any]]:
        stack = list(nodes)
        while stack:
            node = stack.pop()
            node_id = str(node.get("nodeId", node.get("id", "")))
            if node_id == target_id or node_id == f"node-{target_id}":
                return node
            for child in node.get("childIds", []) or node.get("children", []) or []:
                if isinstance(child, dict):
                    stack.append(child)
        return None

    # ------------------------------------------------------------------ #
    # 树工具
    # ------------------------------------------------------------------ #

    async def get_focused_node(self) -> Optional[Dict[str, Any]]:
        if not self._cdp:
            return None
        try:
            result = await self._cdp.send("DOM.getFocusedNode")
            return result.get("node")
        except Exception:
            return None

    async def get_partial_tree(self, focused: bool = True) -> Dict[str, Any]:
        if not self._cdp:
            return {}
        focused_node = await self.get_focused_node()
        if not focused_node:
            return {}
        backend_node_id = focused_node.get("backendNodeId")
        if backend_node_id is None:
            return {}
        ax_tree = await self._cdp.send(
            "Accessibility.getPartialAXTree",
            {"nodeId": backend_node_id, "fetchRelatives": True},
        )
        if isinstance(ax_tree, dict):
            return ax_tree
        return {"nodes": ax_tree}

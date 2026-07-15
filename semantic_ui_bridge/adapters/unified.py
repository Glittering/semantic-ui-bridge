"""Semantic UI Bridge — 统一控制层
一个入口，自动选择AX（桌面原生app）或Playwright（网页）路径。

用法：
    from semantic_ui_bridge.adapters.unified import SUB
    tree = SUB.get_tree("Safari")          # 桌面app
    tree = SUB.get_tree("http://news.cn")  # 网页URL
    SUB.click("Safari", label="重新载入")
    SUB.type("Safari", label="http", value="http://news.cn/")
"""

from __future__ import annotations
from typing import Any
import asyncio


class UnifiedSUB:
    """Agent唯一入口。看target是URL还是app name，自动走AX或Playwright。"""

    def __init__(self):
        self._ax = None  # lazy init
        self._pw_adapter = None
        self._pw_bridge = None

    def _is_url(self, target: str) -> bool:
        return target.startswith("http://") or target.startswith("https://") or target.startswith("file://")

    # ── AX 路径（macOS桌面app）──

    def _get_ax(self):
        if self._ax is None:
            from semantic_ui_bridge.adapters.macos_ax_adapter import get_app_tree, act_on_label, _list_apps
            self._ax = (get_app_tree, act_on_label, _list_apps)
        return self._ax

    def list_apps(self) -> list[dict]:
        """列出所有可操作的GUI应用"""
        *_, list_apps = self._get_ax()
        return list_apps()

    # ── Playwright 路径（网页）──

    async def _get_pw(self):
        if self._pw_bridge is None:
            from semantic_ui_bridge.core.protocol import SemanticUIBridge
            from semantic_ui_bridge.adapters.playwright_adapter import PlaywrightAdapter
            adapter = PlaywrightAdapter()
            self._pw_bridge = SemanticUIBridge(adapter)
        return self._pw_bridge

    async def _ensure_pw_connected(self, url: str):
        bridge = await self._get_pw()
        adapter = bridge._adapter
        if adapter._page is None or url not in (getattr(adapter._page, 'url', '') or ''):
            if adapter._page:
                await adapter.disconnect()
            await adapter.connect(url)
        return bridge

    # ── 统一API ──

    async def get_tree(self, target: str, max_depth: int = 6) -> dict:
        """target="Safari" → AX树；target="http://..." → Playwright语义树"""
        if self._is_url(target):
            bridge = await self._ensure_pw_connected(target)
            tree = await bridge.get_tree()
            return {
                "source": "playwright",
                "app": target,
                "window": target,
                "root": tree.model_dump(),
                "count": _count_elements(tree.root),
            }
        else:
            get_app_tree, *_ = self._get_ax()
            tree = get_app_tree(target, max_depth=max_depth)
            tree["source"] = "ax"
            return tree

    async def click(self, target: str, label: str) -> dict:
        """target="Safari" → AX click; target="http://..." → Playwright→AX fallback"""
        if self._is_url(target):
            bridge = await self._ensure_pw_connected(target)
            from semantic_ui_bridge.core.models import UIRole, Action
            results = await bridge.find(label_contains=label)
            if not results:
                return {"success": False, "error": f"No element matching '{label}' in {target}"}
            result = await bridge.act(Action(action="click", target=results[0].id))
            return {"success": result.success, "source": "playwright", "error": result.error}
        else:
            *_, act, _ = self._get_ax()
            return act(target, label, action="click")

    async def type_text(self, target: str, label: str, value: str) -> dict:
        """target="Safari" → AX setValue; target="http://..." → Playwright fill"""
        if self._is_url(target):
            bridge = await self._ensure_pw_connected(target)
            from semantic_ui_bridge.core.models import UIRole, Action
            results = await bridge.find(role=UIRole.TEXTBOX, label_contains=label)
            if not results:
                results = await bridge.find(label_contains=label)
            if not results:
                return {"success": False, "error": f"No textbox matching '{label}'"}
            result = await bridge.act(Action(action="type", target=results[0].id, params={"text": value}))
            return {"success": result.success, "source": "playwright", "error": result.error}
        else:
            *_, act, _ = self._get_ax()
            return act(target, label, action="type", value=value)

    async def get_web_content(self, url: str, selector: str = "a", wait_ms: int = 4000) -> list[dict]:
        """直接拉网页内容（绕过AX树深度限制）——从DOM提取"""
        if not self._is_url(url):
            url = "http://" + url
        bridge = await self._ensure_pw_connected(url)
        adapter = bridge._adapter
        page = adapter._page
        await page.wait_for_timeout(wait_ms)
        items = await page.evaluate(f'''() => {{
            const out = [];
            document.querySelectorAll({selector!r}).forEach(el => {{
                const t = (el.textContent || '').trim();
                const h = el.href || '';
                if (t.length > 4 && t.length < 120) {{
                    out.push({{text: t, href: h, tag: el.tagName.toLowerCase()}});
                }}
            }});
            const seen = new Set();
            return out.filter(x => {{
                if (seen.has(x.text)) return false;
                seen.add(x.text); return true;
            }});
        }}''')
        return items

    def ls(self, path: str, pattern: str = None, limit: int = 30) -> dict:
        """列出目录内容——文件和文件夹名、大小、修改时间。
        ls("~/Documents/trae_projects/novel_system/") → JSON
        """
        import os, pathlib, time as _time, json as _json
        from collections import OrderedDict

        p = pathlib.Path(path).expanduser().resolve()
        if not p.exists():
            return {"error": f"路径不存在: {p}"}

        if p.is_file():
            st = p.stat()
            return {"files": [{
                "name": p.name, "path": str(p),
                "size": st.st_size,
                "mtime": _time.strftime("%Y-%m-%d %H:%M", _time.localtime(st.st_mtime)),
                "type": "file", "ext": p.suffix,
            }], "count": 1}

        items = []
        for entry in sorted(p.iterdir(),
                            key=lambda e: e.stat().st_mtime, reverse=True):
            name = entry.name
            if pattern and pattern not in name:
                continue
            st = entry.stat()
            items.append({
                "name": name, "path": str(entry),
                "size": st.st_size,
                "mtime": _time.strftime("%Y-%m-%d %H:%M", _time.localtime(st.st_mtime)),
                "type": "dir" if entry.is_dir() else "file",
                "ext": entry.suffix if entry.is_file() else None,
            })
            if len(items) >= limit:
                break

        dirs = sum(1 for x in items if x["type"] == "dir")
        files = sum(1 for x in items if x["type"] == "file")
        return {"path": str(p), "dirs": dirs, "files": files,
                "items": items, "count": len(items)}

    def safari_go(self, url: str) -> dict:
        """一步Safari导航——自动开窗口+输入URL+回车"""
        from semantic_ui_bridge.adapters.macos_ax_adapter import safari_navigate
        return safari_navigate(url)

    async def menu_action(self, app_name: str, menu_path: list[str]) -> dict:
        """操作macOS app菜单：menu_action("Safari", ["文件", "新建窗口"])"""
        get_app_tree, act_on_label, _ = self._get_ax()
        if not menu_path:
            return {"error": "menu_path is empty"}
        # AX菜单操作：点击MenuBarItem → 弹开子菜单 → 点击MenuItem
        _, act, _ = self._get_ax()
        # 简化：按label逐步click
        results = []
        for item_label in menu_path:
            r = act(app_name, item_label, action="click")
            results.append(r)
            if not r.get("success"):
                return {"success": False, "step": item_label, "results": results}
        return {"success": True, "steps": menu_path, "results": results}


def _count_elements(el) -> int:
    n = 1
    for c in getattr(el, 'children', []) or []:
        n += _count_elements(c)
    return n


# 全局单例
SUB = UnifiedSUB()

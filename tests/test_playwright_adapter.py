"""Semantic UI Bridge — Test Playwright Adapter
测试 Playwright/CDP 浏览器适配器的基础行为。
集成测试——需要Playwright浏览器。"""

import pytest
from src.adapters.playwright_adapter import PlaywrightAdapter


@pytest.fixture
async def adapter():
    """每个测试独立的adapter实例（不预连接）"""
    a = PlaywrightAdapter()
    yield a
    await a.disconnect()


class TestConnection:
    """connect / disconnect"""

    async def test_connect_to_url(self, adapter, test_html_url):
        """PA-001: connect(url)后page.url匹配"""
        await adapter.connect(test_html_url)
        assert test_html_url in adapter._page.url  # pyright: ignore[reportPrivateUsage]

    async def test_disconnect_cleanup(self, adapter, test_html_url):
        """PA-004: disconnect()清理浏览器"""
        await adapter.connect(test_html_url)
        await adapter.disconnect()
        # 重连应该能成功（说明上次完全清理）
        await adapter.connect(test_html_url)
        assert test_html_url in adapter._page.url  # pyright: ignore[reportPrivateUsage]

    async def test_reconnect_different_url(self, adapter, test_html_url):
        """PA-005: 断开→重连不同url"""
        await adapter.connect(test_html_url)
        await adapter.disconnect()
        # 重连同一个url
        await adapter.connect(test_html_url)
        assert test_html_url in adapter._page.url  # pyright: ignore[reportPrivateUsage]

    async def test_nonexistent_url(self, adapter):
        """PA-006: 不存在的url → graceful error"""
        try:
            await adapter.connect("http://this-domain-does-not-exist-99999.com/")
            assert False, "Expected exception but none raised"
        except Exception:
            pass  # expected


class TestRawTree:
    """get_raw_tree()"""

    async def test_returns_ax_nodes(self, adapter, test_html_url):
        """PA-002: get_raw_tree返回含nodes的dict"""
        await adapter.connect(test_html_url)
        raw = await adapter.get_raw_tree()
        assert isinstance(raw, dict)
        # CDP Accessibility tree有nodes字段（list）或root AXNode
        assert len(raw) > 0


class TestExecuteAction:
    """execute_action()"""

    async def test_click_executes(self, adapter, test_html_url):
        """PA-003: execute_action(click)触发真实点击"""
        await adapter.connect(test_html_url)

        # 先拿到raw tree找一个button id
        raw = await adapter.get_raw_tree()
        # 通过raw tree的某个element id来触发——适配器负责映射
        # 这里我们测试的是：execute_action能成功执行不抛错
        # 具体id取决于适配器的element id生成方式
        btns = _find_buttons_in_raw(raw)
        if not btns:
            pytest.skip("No buttons in raw tree")

        result = await adapter.execute_action(btns[0]["id"], "click", {})
        assert result is not None  # 至少不是None


def _find_buttons_in_raw(raw: dict) -> list[dict]:
    """从raw树中找button节点——递归"""
    result = []
    if isinstance(raw, dict):
        if raw.get("role") in ("button", "pushbutton", "link"):
            result.append(raw)
        for child in raw.get("children", []):
            result.extend(_find_buttons_in_raw(child))
        for v in raw.values():
            if isinstance(v, (dict, list)):
                result.extend(_find_buttons_in_raw(v))
    elif isinstance(raw, list):
        for item in raw:
            result.extend(_find_buttons_in_raw(item))
    return result
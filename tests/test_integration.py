"""Semantic UI Bridge — Test Integration (E2E)
端到端测试：真实公共网页，全链路 SUB.ui.* → 真实浏览器。
这些测试在CI无浏览器环境时可以skip。"""

import pytest
from src.core.protocol import SemanticUIBridge
from src.adapters.playwright_adapter import PlaywrightAdapter


@pytest.fixture
async def bridge_github():
    """连接到GitHub issue页面"""
    adapter = PlaywrightAdapter()
    await adapter.connect("https://github.com/numpy/numpy/issues/1")
    bridge = SemanticUIBridge(adapter)
    yield bridge
    await adapter.disconnect()


@pytest.fixture
async def bridge_hn():
    """连接到Hacker News"""
    adapter = PlaywrightAdapter()
    await adapter.connect("https://news.ycombinator.com/")
    bridge = SemanticUIBridge(adapter)
    yield bridge
    await adapter.disconnect()


class TestGitHub:
    """GitHub真实页面"""

    @pytest.mark.slow
    async def test_get_tree(self, bridge_github):
        """I-001: GitHub issue页 get_tree()正常"""
        tree = await bridge_github.get_tree()
        assert tree.root is not None
        # GitHub页面角色丰富
        roles = _collect_roles(tree.root)
        assert "button" in roles, f"Roles found: {roles}"
        assert "text" in roles
        assert "textbox" in roles  # 搜索框/评论框

    @pytest.mark.slow
    async def test_find_searchbox(self, bridge_github):
        """I-002: 搜索GitHub上的textbox"""
        from src.core.models import UIRole
        textboxes = await bridge_github.find(role=UIRole.TEXTBOX)
        assert len(textboxes) >= 1

    @pytest.mark.slow
    async def test_type_in_search(self, bridge_github):
        """I-003: act(type)填textbox"""
        from src.core.models import UIRole, Action
        textboxes = await bridge_github.find(role=UIRole.TEXTBOX)
        if not textboxes:
            pytest.skip("No found textbox")
        tb = textboxes[0]
        result = await bridge_github.act(
            Action(action="type", target=tb.id, params={"text": "numpy"})
        )
        assert result.success


class TestHackerNews:
    """Hacker News极简页面"""

    @pytest.mark.slow
    async def test_hn_semantic(self, bridge_hn):
        """I-005: HN链接角色正确"""
        from src.core.models import UIRole
        tree = await bridge_hn.get_tree()
        links = _find_by_role(tree.root, UIRole.BUTTON)  # links映射成button
        # HN有30条新闻链接
        assert len(links) >= 10

    @pytest.mark.slow
    async def test_hn_has_text(self, bridge_hn):
        """I-EXTRA: HN含文本元素"""
        from src.core.models import UIRole
        tree = await bridge_hn.get_tree()
        texts = _find_by_role(tree.root, UIRole.TEXT)
        assert len(texts) >= 5


class TestAnyPage:
    """通用页面鲁棒性"""

    @pytest.mark.slow
    async def test_no_crash(self, bridge_hn):
        """I-004: 任意页面get_tree()不崩溃"""
        tree = await bridge_hn.get_tree()
        assert tree.timestamp > 0
        assert tree.app_name  # 应该有app信息


# ── helpers ──

def _collect_roles(el) -> set:
    roles = {el.role.value if hasattr(el.role, 'value') else str(el.role)}
    for child in el.children:
        roles |= _collect_roles(child)
    return roles


def _find_by_role(el, role):
    result = []
    if el.role == role:
        result.append(el)
    for child in el.children:
        result.extend(_find_by_role(child, role))
    return result
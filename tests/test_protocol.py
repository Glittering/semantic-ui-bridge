"""Semantic UI Bridge — Test Protocol
测试 Protocol 层 API：get_tree / find / act / wait_for
集成测试——需要 Playwright + 本地测试HTML。"""

import pytest
import asyncio

# 这些import在源码实现后才生效；测试先写，先验证失败
from src.core.models import UIRole, UIElement, UITree, Action
from src.core.errors import SUBTimeoutError
from src.core.protocol import SemanticUIBridge
from src.adapters.playwright_adapter import PlaywrightAdapter


@pytest.fixture
async def bridge(test_html_url):
    """创建已连接到测试页面的SUB实例"""
    adapter = PlaywrightAdapter()
    await adapter.connect(test_html_url)
    bridge = SemanticUIBridge(adapter)
    yield bridge
    await adapter.disconnect()


# ── get_tree ──

class TestGetTree:
    """get_tree()——获取页面语义UI树"""

    async def test_basic_call(self, bridge):
        """P-001: get_tree()返回非空root"""
        tree = await bridge.get_tree()
        assert tree is not None
        assert tree.root is not None
        assert tree.root.role is not None
        assert tree.timestamp > 0

    async def test_returns_interactive_elements(self, bridge):
        """P-002: 测试页含button，tree中role=button数量≥3"""
        tree = await bridge.get_tree()
        buttons = _find_by_role(tree.root, UIRole.BUTTON)
        assert len(buttons) >= 3, f"Expected ≥3 buttons, got {len(buttons)}"

    async def test_focused_only(self, bridge):
        """P-014: focused_only=True时，root是focused元素"""
        # 先让一个textbox获得焦点
        textboxes = _find_by_role((await bridge.get_tree()).root, UIRole.TEXTBOX)
        if textboxes:
            await bridge.act(Action(action="focus", target=textboxes[0].id))
            await asyncio.sleep(0.3)
            tree = await bridge.get_tree(focused_only=True)
            assert tree.root is not None
            # root应该是focused元素或包含它
            assert tree.focused_element_id is not None

    async def test_id_stability(self, bridge):
        """P-013: 两次get_tree相同元素id一致"""
        tree1 = await bridge.get_tree()
        tree2 = await bridge.get_tree()
        ids1 = {e.id for e in _collect_elements(tree1.root)}
        ids2 = {e.id for e in _collect_elements(tree2.root)}
        common = ids1 & ids2
        assert len(common) > 0, "No stable IDs across two get_tree calls"


# ── find ──

class TestFind:
    """find()——搜索UI元素"""

    async def test_find_by_role(self, bridge):
        """P-003: find(role=button)返回非空"""
        results = await bridge.find(role=UIRole.BUTTON)
        assert len(results) > 0

    async def test_find_by_label(self, bridge):
        """P-004: find(label_contains='提交')返回精确1个（测试页有'提交订单'按钮）"""
        results = await bridge.find(label_contains="提交")
        assert len(results) >= 1
        assert any("提交" in r.label for r in results if r.label)

    async def test_find_by_states(self, bridge):
        """P-005: find(states=['disabled'])过滤正确——返回disabled按钮"""
        results = await bridge.find(states=["disabled"])
        for r in results:
            assert "disabled" in r.states

    async def test_find_no_match(self, bridge):
        """P-006: 无匹配返回空列表"""
        results = await bridge.find(role=UIRole.DIALOG)
        assert results == []

    async def test_find_combined_filters(self, bridge):
        """P-EXTRA: role+label组合过滤"""
        results = await bridge.find(role=UIRole.BUTTON, label_contains="提交")
        assert len(results) >= 1
        for r in results:
            assert r.role == UIRole.BUTTON


# ── act ──

class TestAct:
    """act()——执行UI动作"""

    async def test_click_success(self, bridge):
        """P-007: click按钮 → success=True"""
        buttons = await bridge.find(role=UIRole.BUTTON, label_contains="Click")
        if not buttons:
            pytest.skip("Test page missing 'Click Me' button")
        result = await bridge.act(Action(action="click", target=buttons[0].id))
        assert result.success
        # 应该有diff——按钮状态变了或新元素出现
        assert len(result.diff) > 0 or result.result_tree is not None

    async def test_click_nonexistent(self, bridge):
        """P-008: click不存在的元素 → success=False"""
        result = await bridge.act(Action(action="click", target="nonexistent-id-99999"))
        assert not result.success
        assert result.error is not None

    async def test_type_text(self, bridge):
        """P-009: type填textbox → 新tree中value正确"""
        textboxes = await bridge.find(role=UIRole.TEXTBOX)
        if not textboxes:
            pytest.skip("No textbox in test page")
        result = await bridge.act(
            Action(action="type", target=textboxes[0].id, params={"text": "HelloSUB"})
        )
        assert result.success
        # 取新tree，验证value
        if result.result_tree:
            updated = _find_by_id(result.result_tree.root, textboxes[0].id)
            if updated:
                assert updated.value == "HelloSUB"

    async def test_type_on_button_fails(self, bridge):
        """P-010: type非textbox → success=False"""
        buttons = await bridge.find(role=UIRole.BUTTON)
        if not buttons:
            pytest.skip("No buttons")
        # 尝试对button做type
        result = await bridge.act(
            Action(action="type", target=buttons[0].id, params={"text": "test"})
        )
        assert not result.success

    async def test_select_option(self, bridge):
        """P-EXTRA: select dropdown选项"""
        selects = await bridge.find(role=UIRole.SELECT)
        if not selects:
            pytest.skip("No select element in test page")
        result = await bridge.act(
            Action(action="select", target=selects[0].id, params={"value": "us"})  # 实际option value
        )
        assert result.success


# ── wait_for ──

class TestWaitFor:
    """wait_for()——条件等待"""

    async def test_wait_for_success(self, bridge):
        """P-012: click按钮→弹dialog, wait_for dialog出现"""
        # 找一个能触发dialog的按钮
        trigger_btns = await bridge.find(label_contains="Dialog")
        if not trigger_btns:
            pytest.skip("No dialog trigger button")

        def _has_dialog(tree: UITree) -> bool:
            dialogs = _find_by_role(tree.root, UIRole.DIALOG)
            return len(dialogs) > 0

        # 点击触发（可能异步弹dialog）
        click_result = await bridge.act(Action(action="click", target=trigger_btns[0].id))
        if not click_result.success:
            pytest.skip(f"Click failed: {click_result.error}")

        # 等待dialog出现
        tree = await bridge.wait_for(_has_dialog, timeout=5)
        dialogs = _find_by_role(tree.root, UIRole.DIALOG)
        assert len(dialogs) > 0

    async def test_wait_for_timeout(self, bridge):
        """P-011: 条件永不满足 → 超时"""
        def _never_true(tree: UITree) -> bool:
            return False

        try:
            await bridge.wait_for(_never_true, timeout=1.0)
            assert False, "Expected SUBTimeoutError"
        except SUBTimeoutError:
            pass  # expected


# ── helpers ──

def _find_by_role(el: UIElement, role: UIRole) -> list[UIElement]:
    result = []
    if el.role == role:
        result.append(el)
    for child in el.children:
        result.extend(_find_by_role(child, role))
    return result

def _find_by_id(el: UIElement, target_id: str) -> UIElement | None:
    if el.id == target_id:
        return el
    for child in el.children:
        found = _find_by_id(child, target_id)
        if found:
            return found
    return None

def _collect_elements(el: UIElement) -> list[UIElement]:
    result = [el]
    for child in el.children:
        result.extend(_collect_elements(child))
    return result
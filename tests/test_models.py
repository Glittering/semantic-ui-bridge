"""Semantic UI Bridge — Test Models
测试 Pydantic 数据模型的正确性。
纯单元测试，无外部依赖。"""

import json
import pytest
from pydantic import ValidationError

from src.core.models import UIRole, UIElement, UITree, Action, ActionResult


class TestUIRole:
    """UIRole枚举——10种统一控件角色"""

    def test_all_roles_exist(self):
        """M-EXTRA: 确认10种核心角色都在枚举中"""
        expected = {"button", "textbox", "text", "checkbox",
                     "select", "slider", "image", "table", "dialog", "group"}
        actual = set(r.value for r in UIRole)
        assert actual == expected

    def test_from_string(self):
        assert UIRole("button") == UIRole.BUTTON
        assert UIRole("textbox") == UIRole.TEXTBOX

    def test_invalid_role_raises(self):
        with pytest.raises(ValueError):
            UIRole("invalid_role")


class TestUIElementBasic:
    """UIElement 基本创建"""

    def test_minimal_valid(self):
        """M-001: 最小有效值"""
        el = UIElement(id="btn-1", role=UIRole.BUTTON)
        assert el.id == "btn-1"
        assert el.role == UIRole.BUTTON
        assert el.label is None
        assert el.states == []
        assert el.value is None
        assert el.actions == []
        assert el.children == []
        assert el.bounds is None

    def test_all_optional_fields(self):
        """M-002: 所有可选字段"""
        child = UIElement(id="child-1", role=UIRole.TEXT, label="hello")
        el = UIElement(
            id="btn-1",
            role=UIRole.BUTTON,
            label="提交订单",
            states=["enabled", "focusable", "visible"],
            value="submit",
            actions=["click", "focus"],
            children=[child],
            bounds={"x": 100, "y": 200, "w": 80, "h": 40},
        )
        assert el.label == "提交订单"
        assert "enabled" in el.states
        assert el.value == "submit"
        assert "click" in el.actions
        assert len(el.children) == 1
        assert el.children[0].label == "hello"
        assert el.bounds["x"] == 100

    def test_role_validation(self):
        """M-003: UIRole枚举限制——错误的role应被拒绝"""
        with pytest.raises(ValidationError):
            UIElement(id="x", role="invalid_role")


class TestUIElementChildren:
    """递归children"""

    def test_nested_3_levels(self):
        """M-004: 3层嵌套正确"""
        l3 = UIElement(id="l3", role=UIRole.TEXT, label="leaf")
        l2 = UIElement(id="l2", role=UIRole.GROUP, children=[l3])
        l1 = UIElement(id="l1", role=UIRole.GROUP, children=[l2])
        root = UIElement(id="root", role=UIRole.GROUP, children=[l1])

        assert root.children[0].children[0].children[0].label == "leaf"

    def test_no_children_by_default(self):
        el = UIElement(id="x", role=UIRole.TEXT)
        assert el.children == []


class TestUITree:
    """UITree——完整界面树"""

    def test_complete_tree(self):
        """M-005: 所有必填字段"""
        root = UIElement(id="root", role=UIRole.GROUP,
                          children=[UIElement(id="btn", role=UIRole.BUTTON, label="OK")])
        tree = UITree(
            app_name="chrome",
            app_title="Test Page",
            root=root,
            timestamp=1752569600.123,
            focused_element_id="btn",
        )
        assert tree.app_name == "chrome"
        assert tree.app_title == "Test Page"
        assert tree.root.children[0].label == "OK"
        assert tree.focused_element_id == "btn"

    def test_no_focused_element(self):
        root = UIElement(id="r", role=UIRole.GROUP)
        tree = UITree(app_name="safari", app_title="Blank", root=root, timestamp=0.0)
        assert tree.focused_element_id is None


class TestAction:
    """Action模型"""

    def test_valid_click(self):
        """M-006: click动作"""
        a = Action(action="click", target="btn-1")
        assert a.action == "click"
        assert a.target == "btn-1"
        assert a.params == {}

    def test_type_with_text(self):
        a = Action(action="type", target="tb-1", params={"text": "hello"})
        assert a.params["text"] == "hello"


class TestActionResult:
    """ActionResult模型"""

    def test_success_result(self):
        """M-007: success=True → result_tree非None"""
        root = UIElement(id="r", role=UIRole.GROUP)
        tree = UITree(app_name="c", app_title="p", root=root, timestamp=0.0)
        action = Action(action="click", target="btn-1")
        result = ActionResult(success=True, action=action, result_tree=tree, diff=["btn-1: clicked"])
        assert result.success
        assert result.result_tree is not None
        assert result.error is None
        assert len(result.diff) == 1

    def test_failure_result(self):
        """M-008: success=False → error非None"""
        action = Action(action="click", target="nonexistent")
        result = ActionResult(
            success=False, action=action,
            error="Element nonexistent not found"
        )
        assert not result.success
        assert result.error is not None
        assert result.result_tree is None


class TestSerialization:
    """JSON序列化往返"""

    def test_element_to_json(self):
        """M-009: model_dump_json → 合法JSON"""
        el = UIElement(id="btn-1", role=UIRole.BUTTON, label="提交",
                        states=["enabled"], actions=["click"])
        json_str = el.model_dump_json()
        data = json.loads(json_str)
        assert data["id"] == "btn-1"
        assert data["role"] == "button"
        assert data["label"] == "提交"

    def test_element_from_json(self):
        """M-010: 合法JSON → model_validate"""
        data = {"id": "btn-1", "role": "button", "label": "提交",
                "states": ["enabled"], "actions": ["click"]}
        el = UIElement.model_validate(data)
        assert el.id == "btn-1"
        assert el.role == UIRole.BUTTON

    def test_tree_roundtrip(self):
        root = UIElement(id="r", role=UIRole.GROUP,
                          children=[UIElement(id="b", role=UIRole.BUTTON, label="OK")])
        tree = UITree(app_name="chrome", app_title="Test", root=root, timestamp=1.0)
        json_str = tree.model_dump_json()
        restored = UITree.model_validate_json(json_str)
        assert restored.app_name == "chrome"
        assert restored.root.children[0].label == "OK"

    def test_action_roundtrip(self):
        a = Action(action="type", target="tb", params={"text": "hello"})
        json_str = a.model_dump_json()
        restored = Action.model_validate_json(json_str)
        assert restored.params["text"] == "hello"
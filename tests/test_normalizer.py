"""Semantic UI Bridge — Test Normalizer
测试语义标准化逻辑：角色映射、去噪、分组。
纯单元测试——mock原始控件树，不依赖真实浏览器。"""

import pytest
from src.core.models import UIRole, UIElement
from src.core.normalizer import Normalizer


# ── helper to make raw platform-like element dicts ──

def raw_el(id_: str, role: str | None = None, label: str | None = None,
           states: list[str] | None = None, children: list | None = None,
           **extra) -> dict:
    d = {"id": id_, "role": role, "label": label,
         "states": states or [], "children": children or [], "actions": []}
    d.update(extra)
    return d


@pytest.fixture
def norm():
    return Normalizer()


# ── Role Mapping ──

class TestRoleMapping:
    """角色映射：平台角色→UIRole"""

    @pytest.mark.parametrize("raw,expected", [
        ("pushbutton", UIRole.BUTTON),
        ("button", UIRole.BUTTON),
        ("link", UIRole.BUTTON),
        ("edit", UIRole.TEXTBOX),
        ("textbox", UIRole.TEXTBOX),
        ("searchbox", UIRole.TEXTBOX),
        ("statictext", UIRole.TEXT),
        ("label", UIRole.TEXT),
        ("heading", UIRole.TEXT),
        ("paragraph", UIRole.TEXT),
        ("checkbox", UIRole.CHECKBOX),
        ("radio", UIRole.CHECKBOX),
        ("toggle", UIRole.CHECKBOX),
        ("list", UIRole.SELECT),
        ("listbox", UIRole.SELECT),
        ("menu", UIRole.SELECT),
        ("combobox", UIRole.SELECT),
        ("slider", UIRole.SLIDER),
        ("scrollbar", UIRole.SLIDER),
        ("progressbar", UIRole.SLIDER),
        ("image", UIRole.IMAGE),
        ("table", UIRole.TABLE),
        ("grid", UIRole.TABLE),
        ("dialog", UIRole.DIALOG),
        ("alert", UIRole.DIALOG),
        ("group", UIRole.GROUP),
        ("pane", UIRole.GROUP),
        ("toolbar", UIRole.GROUP),
        ("menubar", UIRole.GROUP),
    ])
    def test_known_role(self, norm, raw, expected):
        """N-001..N-004(N部分): 已知角色正确映射"""
        el = norm.normalize_element(raw_el("x", role=raw))
        assert el.role == expected

    def test_unknown_role_fallback(self, norm):
        """N-004: 未知角色→GROUP fallback"""
        el = norm.normalize_element(raw_el("x", role="made_up_role_xyz"))
        assert el.role == UIRole.GROUP


# ── Denoising ──

class TestDenoiseVisibility:
    """去噪：不可见元素"""

    def test_cut_invisible_node(self, norm):
        """N-005: states含invisible→砍"""
        root = raw_el("r", role="group", children=[
            raw_el("hidden", role="button", label="Ghost", states=["invisible"]),
            raw_el("visible", role="button", label="Real", states=["enabled", "visible"]),
        ])
        tree = norm.normalize_tree(root)
        labels = _collect_labels(tree.root)
        assert "Ghost" not in labels
        assert "Real" in labels

    def test_keep_visible_node(self, norm):
        """N-006: 可见+enabled→保留"""
        root = raw_el("r", role="group", children=[
            raw_el("btn", role="button", label="OK", states=["visible", "enabled"]),
        ])
        tree = norm.normalize_tree(root)
        labels = _collect_labels(tree.root)
        assert "OK" in labels

    def test_cut_hidden_by_attr(self, norm):
        """N-EXTRA: aria-hidden=true→砍"""
        root = raw_el("r", role="group", children=[
            raw_el("btn", role="button", label="Secret", states=["visible"],
                   extra_attrs={"aria-hidden": "true"}),
        ])
        tree = norm.normalize_tree(root)
        assert len(tree.root.children) == 0

    def test_cut_display_none(self, norm):
        """N-009: display:none等价→砍"""
        root = raw_el("r", role="group", children=[
            raw_el("btn", role="button", label="Gone", states=["visible"],
                   computed_style={"display": "none"}),
        ])
        tree = norm.normalize_tree(root)
        assert len(tree.root.children) == 0


class TestDenoiseLayoutContainers:
    """去噪：纯布局容器"""

    def test_cut_empty_layout_group(self, norm):
        """N-007: 无语义role group且无交互子→砍，子提升"""
        root = raw_el("r", role="group", children=[
            raw_el("wrapper", role="group", children=[
                raw_el("btn", role="button", label="OK"),
            ]),
        ])
        tree = norm.normalize_tree(root)
        # wrapper应该被砍，btn提升到root下
        assert len(tree.root.children) == 1
        assert tree.root.children[0].label == "OK"

    def test_keep_group_with_interactive_child(self, norm):
        """N-008: group含button→保留"""
        root = raw_el("r", role="group", children=[
            raw_el("toolbar", role="toolbar", label="Tools", children=[
                raw_el("btn1", role="button", label="Cut"),
                raw_el("btn2", role="button", label="Copy"),
            ]),
        ])
        tree = norm.normalize_tree(root)
        # toolbar保留（有语义role）
        assert len(tree.root.children) == 1
        assert tree.root.children[0].role == UIRole.GROUP
        assert tree.root.children[0].label == "Tools"


class TestDenoiseDuplicates:
    """去噪：重复标签"""

    def test_dedup_sibling_with_same_label(self, norm):
        """N-010: 相邻兄弟标签相同且无语义差异→只保留第一个"""
        root = raw_el("r", role="group", children=[
            raw_el("l1", role="text", label="Price: $10"),
            raw_el("l2", role="text", label="Price: $10"),
            raw_el("l3", role="text", label="Price: $10"),
        ])
        tree = norm.normalize_tree(root)
        assert len(tree.root.children) == 1  # 只保留一个


class TestNormalizeFullTree:
    """完整normalize流程"""

    def test_full_normalize_pipeline(self, norm):
        """N-011: 模拟DOM+AX混合树 → UITree正确"""
        raw_tree = raw_el("root", role="root", label="Test App", children=[
            raw_el("hidden_div", role="group", states=["invisible"], children=[
                raw_el("ghost_btn", role="button", label="Don't show"),
            ]),
            raw_el("main", role="group", children=[
                raw_el("search", role="searchbox", label="Search"),
                raw_el("submit", role="pushbutton", label="提交"),
                raw_el("desc", role="statictext", label="Description text"),
                raw_el("empty_wrapper", role="generic", children=[
                    raw_el("inner_btn", role="button", label="Inside"),
                ]),
            ]),
        ])
        tree = norm.normalize_tree(raw_tree)

        labels = _collect_labels(tree.root)
        assert "Search" in labels
        assert "提交" in labels
        assert "Description text" in labels
        assert "Inside" in labels
        assert "Don't show" not in labels  # invisible父→全子树被砍

        roles = {c.role for c in tree.root.children}
        assert UIRole.TEXTBOX in roles
        assert UIRole.BUTTON in roles
        assert UIRole.TEXT in roles

    def test_normalize_idempotent(self, norm):
        """N-012: 两次normalize结果相同"""
        raw = raw_el("root", role="group", children=[
            raw_el("b", role="button", label="OK"),
        ])
        t1 = norm.normalize_tree(raw)
        t2 = norm.normalize_tree(raw)
        # 比较JSON输出
        assert t1.root.model_dump_json() == t2.root.model_dump_json()

    def test_empty_tree(self, norm):
        """N-EXTRA: 空raw树不崩溃"""
        raw = raw_el("root", role="group")
        tree = norm.normalize_tree(raw)
        assert tree.root.role == UIRole.GROUP

    def test_preserves_states(self, norm):
        """N-EXTRA: states正确传递"""
        raw = raw_el("root", role="group", children=[
            raw_el("btn", role="button", label="Disabled", states=["disabled"]),
        ])
        tree = norm.normalize_tree(raw)
        assert "disabled" in tree.root.children[0].states


# ── helpers ──

def _collect_labels(el: UIElement) -> list[str]:
    """递归收集所有label"""
    result = []
    if el.label:
        result.append(el.label)
    for child in el.children:
        result.extend(_collect_labels(child))
    return result
"""Semantic UI Bridge — Normalizer
把平台原始控件树映射到统一的 UIElement 树。支持 CDP AX 和简化 dict 两种格式。"""

from __future__ import annotations
from typing import Any

from src.core.models import UIElement, UITree, UIRole


class Normalizer:
    """语义标准化器"""

    # 角色映射表
    ROLE_MAP: dict[str, UIRole] = {
        "pushbutton": UIRole.BUTTON, "button": UIRole.BUTTON, "link": UIRole.BUTTON,
        "edit": UIRole.TEXTBOX, "textbox": UIRole.TEXTBOX, "searchbox": UIRole.TEXTBOX,
        "statictext": UIRole.TEXT, "StaticText": UIRole.TEXT,
        "label": UIRole.TEXT, "heading": UIRole.TEXT, "paragraph": UIRole.TEXT,
        "checkbox": UIRole.CHECKBOX, "radio": UIRole.CHECKBOX, "toggle": UIRole.CHECKBOX,
        "list": UIRole.SELECT, "listbox": UIRole.SELECT, "menu": UIRole.SELECT, "combobox": UIRole.SELECT,
        "slider": UIRole.SLIDER, "scrollbar": UIRole.SLIDER, "progressbar": UIRole.SLIDER,
        "image": UIRole.IMAGE,
        "table": UIRole.TABLE, "grid": UIRole.TABLE,
        "dialog": UIRole.DIALOG, "alert": UIRole.DIALOG,
        "group": UIRole.GROUP, "pane": UIRole.GROUP, "toolbar": UIRole.GROUP, "menubar": UIRole.GROUP,
        "generic": UIRole.GROUP,
        "LabelText": UIRole.TEXT, "InlineTextBox": UIRole.GROUP, "none": UIRole.GROUP,
        "RootWebArea": UIRole.GROUP, "MenuListPopup": UIRole.GROUP,
        "row": UIRole.GROUP, "rowgroup": UIRole.GROUP,
        "columnheader": UIRole.TEXT, "cell": UIRole.TEXT,
        "option": UIRole.GROUP,
    }

    # CDP chromeRole 数字 → UIRole 映射（常见值）
    CHROME_ROLE_MAP: dict[int, UIRole] = {
        1: UIRole.GROUP,       # kAlertDialog
        2: UIRole.GROUP,       # kAlert
        18: UIRole.CHECKBOX,   # kCheckBox
        19: UIRole.TABLE,      # kColumnHeader
        20: UIRole.BUTTON,     # kComboBoxMenuButton - ignore
        21: UIRole.SELECT,     # kComboBoxSelect
        22: UIRole.BUTTON,     # kDisclosureTriangle
        23: UIRole.GROUP,      # kDisclosureTriangleGrouped
        24: UIRole.DIALOG,     # kDialog
        25: UIRole.BUTTON,     # kButtonDropDown
        26: UIRole.GROUP,      # kDocAbstract
        27: UIRole.GROUP,      # kDocAcknowledgments
        28: UIRole.BUTTON,     # kDocAppendix
        29: UIRole.GROUP,      # kBackLink
        30: UIRole.GROUP,      # kDocBiblioEntry
        31: UIRole.GROUP,      # kDocBibliography
        32: UIRole.GROUP,      # kDocBiblioRef
        33: UIRole.GROUP,      # kDocChapter
        34: UIRole.GROUP,      # kDocColophon
        35: UIRole.GROUP,      # kDocConclusion
        36: UIRole.GROUP,      # kDocCover
        37: UIRole.GROUP,      # kDocCredit
        38: UIRole.GROUP,      # kDocCredits
        39: UIRole.GROUP,      # kDocDedication
        40: UIRole.GROUP,      # kDocEndnotes
        41: UIRole.GROUP,      # kDocEpigraph
        42: UIRole.GROUP,      # kDocEpilogue
        43: UIRole.GROUP,      # kDocErrata
        44: UIRole.GROUP,      # kDocExample
        45: UIRole.GROUP,      # kDocFootnote
        46: UIRole.GROUP,      # kDocForeword
        47: UIRole.GROUP,      # kDocGlossary
        48: UIRole.GROUP,      # kDocGlossRef
        49: UIRole.GROUP,      # kDocIndex
        50: UIRole.GROUP,      # kDocIntroduction
        51: UIRole.GROUP,      # kDocNoteRef
        52: UIRole.GROUP,      # kDocNotice
        53: UIRole.GROUP,      # kDocPageFooter
        54: UIRole.GROUP,      # kDocPageHeader
        55: UIRole.GROUP,      # kDocPageList
        56: UIRole.GROUP,      # kDocPart
        57: UIRole.GROUP,      # kDocPreface
        58: UIRole.GROUP,      # kDocPrologue
        59: UIRole.GROUP,      # kDocPullquote
        60: UIRole.GROUP,      # kDocQna
        61: UIRole.GROUP,      # kDocSubtitle
        62: UIRole.GROUP,      # kDocTip
        63: UIRole.GROUP,      # kDocToc
        72: UIRole.GROUP,      # kFooter
        73: UIRole.GROUP,      # kFooterAsNonNative
        74: UIRole.GROUP,      # kForm
        76: UIRole.GROUP,      # kGenericContainer
        78: UIRole.TEXT,       # kHeading
        79: UIRole.IMAGE,      # kIframe
        80: UIRole.IMAGE,      # kIframePresentational
        81: UIRole.IMAGE,      # kImage
        82: UIRole.GROUP,      # kInputTime
        83: UIRole.GROUP,      # kLabelText
        84: UIRole.TEXT,       # kLegend
        85: UIRole.GROUP,      # kLineBreak
        86: UIRole.BUTTON,     # kLink
        87: UIRole.GROUP,      # kList
        88: UIRole.GROUP,      # kListBox
        89: UIRole.GROUP,      # kListBoxPopup
        90: UIRole.GROUP,      # kListItem
        91: UIRole.GROUP,      # kListMarker
        93: UIRole.GROUP,      # kMathMLFraction
        94: UIRole.GROUP,      # kMathMLIdentifier
        95: UIRole.GROUP,      # kMathMLMath
        96: UIRole.GROUP,      # kMathMLMultiscripts
        97: UIRole.GROUP,      # kMathMLNoneScript
        98: UIRole.GROUP,      # kMathMLNumber
        99: UIRole.GROUP,      # kMathMLOperator
        100: UIRole.GROUP,     # kMathMLOver
        101: UIRole.GROUP,     # kMathMLPrescriptDelimiter
        102: UIRole.GROUP,     # kMathMLRoot
        103: UIRole.GROUP,     # kMathMLRow
        104: UIRole.GROUP,     # kMathMLSquareRoot
        105: UIRole.GROUP,     # kMathMLStringLiteral
        106: UIRole.GROUP,     # kMathMLSub
        107: UIRole.GROUP,     # kMathMLSubSup
        108: UIRole.GROUP,     # kMathMLSup
        109: UIRole.GROUP,     # kMathMLTable
        110: UIRole.GROUP,     # kMathMLTableCell
        111: UIRole.GROUP,     # kMathMLTableRow
        112: UIRole.GROUP,     # kMathMLText
        113: UIRole.GROUP,     # kMathMLUnder
        114: UIRole.GROUP,     # kMathMLUnderOver
        115: UIRole.TABLE,     # kMenuListPopup
        116: UIRole.GROUP,     # kMenuListOption
        117: UIRole.GROUP,     # kMenuBar
        118: UIRole.BUTTON,    # kMenuItem
        119: UIRole.GROUP,     # kMenuPopup
        122: UIRole.TABLE,     # kGrid
        123: UIRole.TABLE,     # kCell
        124: UIRole.TABLE,     # kRowHeader
        125: UIRole.TABLE,     # kRow
        127: UIRole.BUTTON,    # kPopUpButton
        128: UIRole.BUTTON,    # kPortal
        130: UIRole.GROUP,     # kProgressIndicator
        131: UIRole.BUTTON,    # kRadioButton
        132: UIRole.GROUP,     # kRadioGroup
        133: UIRole.BUTTON,    # kToggleButton
        134: UIRole.GROUP,     # kRootWebArea
        135: UIRole.GROUP,     # kRowGroup
        136: UIRole.BUTTON,    # kRubyAnnotation
        137: UIRole.BUTTON,    # kRubyPronunciation
        138: UIRole.TEXTBOX,   # kSearchBox
        140: UIRole.SLIDER,    # kSlider
        141: UIRole.GROUP,     # kSpinButton
        142: UIRole.GROUP,     # kSplitter
        143: UIRole.SELECT,    # kDisclosureTriangle
        145: UIRole.TEXT,      # kStaticText
        146: UIRole.GROUP,     # kSuggestion
        147: UIRole.BUTTON,    # kTab
        148: UIRole.GROUP,     # kTabList
        149: UIRole.GROUP,     # kTabPanel
        150: UIRole.TEXTBOX,   # kTextField
        151: UIRole.GROUP,     # kTextFieldWithComboBox
        152: UIRole.GROUP,     # kTime
        155: UIRole.BUTTON,    # kToggleButton
        156: UIRole.GROUP,     # kToolbar
        157: UIRole.GROUP,     # kTree
        158: UIRole.TEXT,      # kTreeItem
        159: UIRole.GROUP,     # kUnknown
        160: UIRole.GROUP,     # kWebView
        161: UIRole.GROUP,     # kWindow
        255: UIRole.GROUP,     # kPdfRoot
    }

    @staticmethod
    def _get_string_value(val: Any) -> str | None:
        """CDP值可能是dict {\"type\":..., \"value\":...}"""
        if isinstance(val, dict):
            return val.get("value") or val.get("type")
        if isinstance(val, str):
            return val
        return None

    @staticmethod
    def _extract_role_from_cdp(node: dict) -> str:
        """从CDP AX node或简化dict提取角色字符串"""
        role_val = node.get("role")
        # 简化格式：直接是字符串
        if isinstance(role_val, str):
            return role_val
        # CDP AX 格式：dict {\"type\": \"role\"|\"internalRole\", \"value\": \"...\"}
        if isinstance(role_val, dict):
            rval = role_val.get("value")
            if isinstance(rval, str):
                return rval
            if isinstance(rval, int):
                return str(rval)
        # chromeRole 作为fallback
        chrome = node.get("chromeRole")
        if isinstance(chrome, dict):
            val = chrome.get("value")
            if isinstance(val, (int, str)):
                return str(val)
        return "group"

    def _map_cdp_role(self, raw_role_str: str) -> UIRole:
        """CDP角色→UIRole，支持数字chromeRole"""
        # 尝试数字 chromeRole
        try:
            num = int(raw_role_str)
            return self.CHROME_ROLE_MAP.get(num, UIRole.GROUP)
        except (ValueError, TypeError):
            pass
        return self.ROLE_MAP.get(raw_role_str, UIRole.GROUP)

    def _extract_label_cdp(self, raw: dict) -> str | None:
        """获取label：CDP name对象 或 简化dict的label字段"""
        name = raw.get("name") or raw.get("label")
        return self._get_string_value(name)

    def _extract_states_cdp(self, raw: dict) -> list[str]:
        """从CDP AX properties数组提取states"""
        states: list[str] = []
        props = raw.get("properties") or []
        if isinstance(props, list):
            for p in props:
                if isinstance(p, dict):
                    pname = p.get("name", "")
                    pval = p.get("value", {})
                    if isinstance(pval, dict):
                        v = pval.get("value")
                        if v is True:
                            states.append(pname)
                        elif v is not None and v is not False:
                            states.append(f"{pname}={v}")
        return states

    def _is_visible(self, raw: dict) -> bool:
        """可见性判断：兼容CDP AX和简化dict"""
        # 简化格式：states列表含invisible——这是用户级隐藏（display:none等），子树全砍
        states = raw.get("states") or []
        if isinstance(states, list) and "invisible" in states:
            return False
        # 简化格式：extra_attrs/attributes 的 aria-hidden → 全砍
        extra = raw.get("extra_attrs", {}) or {}
        if extra.get("aria-hidden") == "true":
            return False
        attrs = raw.get("attributes", {}) or {}
        if attrs.get("aria-hidden") == "true":
            return False
        # 简化格式：computed_style display:none/visibility:hidden → 全砍
        style = raw.get("computed_style", {}) or {}
        if style.get("display") == "none" or style.get("visibility") == "hidden":
            return False
        # CDP AX properties 中的 invisible
        props = raw.get("properties") or []
        if isinstance(props, list):
            for p in props:
                if isinstance(p, dict):
                    if p.get("name") == "invisible" and p.get("value", {}).get("value") is True:
                        return False
        return True

    def _is_subtree_hidden(self, raw: dict) -> bool:
        """是否因为用户级隐藏（display:none等）而应全子树砍掉"""
        # 简化格式的states中的invisible
        states = raw.get("states") or []
        if isinstance(states, list) and "invisible" in states:
            return True
        extra = raw.get("extra_attrs", {}) or {}
        if extra.get("aria-hidden") == "true":
            return True
        attrs = raw.get("attributes", {}) or {}
        if attrs.get("aria-hidden") == "true":
            return True
        style = raw.get("computed_style", {}) or {}
        if style.get("display") == "none" or style.get("visibility") == "hidden":
            return True
        return False

    def normalize_element(self, raw: dict[str, Any]) -> UIElement:
        """CDP AX node 或 简化dict → UIElement"""
        role_str = self._extract_role_from_cdp(raw)
        role = self._map_cdp_role(role_str)
        # states: CDP properties 数组 或 简化格式的 states 列表
        states_raw = raw.get("states") or []
        if isinstance(states_raw, list) and states_raw and isinstance(states_raw[0], str):
            states = list(states_raw)
        else:
            states = self._extract_states_cdp(raw)
        # value
        val_raw = raw.get("value")
        if isinstance(val_raw, dict):
            val_str = val_raw.get("value", "")
        elif isinstance(val_raw, str):
            val_str = val_raw
        else:
            val_str = None
        return UIElement(
            id=str(raw.get("nodeId", raw.get("id", ""))),
            role=role,
            label=self._extract_label_cdp(raw),
            states=states,
            value=val_str if isinstance(val_str, str) else None,
            actions=list(raw.get("actions", []) or []),
            bounds=raw.get("bounds"),
            platform_data=raw,
            children=[],
        )

    def _is_cuttable_layout(self, node: dict, is_root: bool = False) -> bool:
        """砍掉纯布局/无意义容器 —— 兼容CDP和简化格式"""
        if is_root:
            return False
        role_str = self._extract_role_from_cdp(node)
        # CDP StaticText / InlineTextBox 永远不砍
        if role_str in ("145", "158", "101"):
            return False
        role = self._map_cdp_role(role_str)
        # 只有 UIRole.GROUP 可能被砍
        if role != UIRole.GROUP:
            return False
        # 有label → 保留
        if self._extract_label_cdp(node):
            return False
        return True

    def _raw_children(self, node: dict) -> list[dict]:
        children = node.get("children", [])
        if isinstance(children, dict):
            return [children]
        if isinstance(children, list):
            return list(children)
        return []

    def _prune(self, node: dict) -> list[UIElement]:
        # 用户级隐藏（display:none）→ 子树全砍
        if self._is_subtree_hidden(node):
            return []
        # CDP ignored/内部invisible → 节点跳过但递归处理children
        if not self._is_visible(node):
            result: list[UIElement] = []
            for c in self._raw_children(node):
                result.extend(self._prune(c))
            return result
        if self._is_cuttable_layout(node):
            result: list[UIElement] = []
            for c in self._raw_children(node):
                result.extend(self._prune(c))
            return result
        el = self.normalize_element(node)
        kids: list[UIElement] = []
        for c in self._raw_children(node):
            kids.extend(self._prune(c))
        el.children = self._dedup_children(kids)
        return [el]

    def _dedup_children(self, children: list[UIElement]) -> list[UIElement]:
        """去重相邻的同角色+同label节点，但保留结构不同的（children不同）"""
        result: list[UIElement] = []
        for child in children:
            if result:
                prev = result[-1]
                # 只去重完全相同的叶子节点：角色+label+states 相同，且都没有 children
                if (child.role == prev.role and child.label == prev.label
                        and set(child.states) == set(prev.states)
                        and len(child.children) == 0 and len(prev.children) == 0):
                    continue
            result.append(child)
        return result

    def normalize_tree(self, raw: dict) -> UITree:
        """入口：处理CDP AX nodes数组或简化dict格式"""
        nodes = raw.get("nodes")

        if nodes is not None and isinstance(nodes, list) and len(nodes) > 0:
            # CDP AX 格式 —— 第一个节点是 rootWebArea
            root_dict = nodes[0]
            # 构建 nodeId → node 索引
            id_map = {str(n.get("nodeId", "")): n for n in nodes if n.get("nodeId") is not None}

            def _build_children(node):
                """递归用 childIds 填充 children"""
                kids = []
                for cid in node.get("childIds", []) or []:
                    child = id_map.get(str(cid))
                    if child:
                        kids.append(_build_children(child))
                node_copy = dict(node)
                node_copy["children"] = kids
                return node_copy

            root_dict = _build_children(root_dict)
            app_title = self._extract_label_cdp(root_dict) or ""
            app_name = "browser"
        else:
            root_dict = raw
            app_title = str(root_dict.get("label") or root_dict.get("name") or "")
            app_name = str(root_dict.get("app_name", "unknown"))

        root_el = self.normalize_element(root_dict)
        children: list[UIElement] = []
        for c in self._raw_children(root_dict):
            children.extend(self._prune(c))
        root_el.children = self._dedup_children(children)

        # 时间戳优先取raw的，否则取root_dict的，否则0
        ts = raw.get("timestamp") or root_dict.get("timestamp") or 0.0
        # focused_element_id: 从 raw 获取 或 从 root_dict 第一个 nodeId 推断
        focused = (
            str(raw.get("focused_node_id", "") or root_dict.get("focused_node_id", ""))
            or None
        )
        # 如果是 CDP AX 格式且没有显式 focused_node_id，用 root 的 nodeId
        if not focused and nodes is not None:
            focused = str(root_dict.get("nodeId", "")) or None
        return UITree(
            app_name=app_name,
            app_title=app_title,
            root=root_el,
            timestamp=float(ts),
            focused_element_id=focused,
        )
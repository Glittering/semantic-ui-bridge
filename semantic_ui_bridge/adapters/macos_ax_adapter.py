"""Semantic UI Bridge — macOS Accessibility API Adapter
让AI通过AX API直接理解和操作macOS桌面任意应用。
不截图、不OCR、不模拟坐标——原生API调用。"""

from __future__ import annotations
import asyncio
from typing import Any

from AppKit import NSWorkspace
from ApplicationServices import (
    AXUIElementCopyAttributeValue,
    AXUIElementSetAttributeValue,
    AXUIElementCopyAttributeNames,
    AXUIElementCopyActionNames,
    AXUIElementPerformAction,
    AXUIElementCreateApplication,
    kAXChildrenAttribute,
    kAXTitleAttribute,
    kAXRoleAttribute,
    kAXValueAttribute,
    kAXFocusedWindowAttribute,
    kAXSubroleAttribute,
    kAXFocusedAttribute,
)


# ── AX Role → 我们的UIRole映射 ──
ROLE_MAP = {
    "AXButton": "button",
    "AXMenuButton": "button",
    "AXPopUpButton": "button",
    "AXCheckBox": "checkbox",
    "AXRadioGroup": "checkbox",
    "AXRadioButton": "checkbox",
    "AXTextField": "textbox",
    "AXTextArea": "textbox",
    "AXComboBox": "select",
    "AXPopUpButton": "select",
    "AXStaticText": "text",
    "AXLink": "button",
    "AXImage": "image",
    "AXTable": "table",
    "AXOutline": "table",
    "AXSlider": "slider",
    "AXScrollBar": "slider",
    "AXScrollArea": "group",
    "AXGroup": "group",
    "AXSplitGroup": "group",
    "AXWindow": "dialog",
    "AXSheet": "dialog",
    "AXToolbar": "group",
    "AXMenuBar": "group",
    "AXMenuBarItem": "button",
    "AXMenuItem": "button",
    "AXMenu": "group",
    "AXApplication": "group",
    "AXTabGroup": "group",
    "AXOutline": "table",
}


def _g(el, attr):
    """getattr 包装，吞掉err"""
    err, val = AXUIElementCopyAttributeValue(el, attr, None)
    return val


def _list_apps() -> list[dict]:
    """列出所有运行的GUI应用"""
    ws = NSWorkspace.sharedWorkspace()
    out = []
    for app in ws.runningApplications():
        if app.activationPolicy() == 0:  # NSApplicationActivationPolicyRegular
            out.append({
                "name": str(app.localizedName()),
                "bundle_id": str(app.bundleIdentifier() or ""),
                "pid": app.processIdentifier(),
            })
    return out


def _ax_app(pid: int):
    return AXUIElementCreateApplication(pid)


def _count_children(el) -> int:
    ch = _g(el, kAXChildrenAttribute) or []
    return len(ch)


def _walk(el, depth=0, max_depth=6, out=None):
    """递归遍历AX树，产出UIElement结构"""
    if out is None: out = []
    if depth > max_depth:
        return out

    role = _g(el, kAXRoleAttribute) or ""
    title = _g(el, kAXTitleAttribute) or ""
    value = _g(el, kAXValueAttribute) or ""
    sub = _g(el, kAXSubroleAttribute) or ""

    # 去噪：跳过无内容的AXGroup
    if role == "AXGroup" and not title and not sub and depth > 1 and _count_children(el) <= 1:
        children = _g(el, kAXChildrenAttribute) or []
        for c in children:
            _walk(c, depth, max_depth, out)
        return out

    # 转role
    ui_role = ROLE_MAP.get(role, "group")
    label = title or (str(value)[:40] if value and ui_role == "text" else "")

    item = {
        "id": f"ax:{depth}-{len(out)}",
        "role": ui_role,
        "label": label,
        "value": str(value) if value and len(str(value)) < 200 else None,
        "subrole": str(sub) if sub else None,
        "_ax_element": el,  # 保留原AX元素引用，用于act
    }
    out.append(item)

    children = _g(el, kAXChildrenAttribute) or []
    for c in children[:30]:  # 限制每层最多30个子节点防爆炸
        _walk(c, depth + 1, max_depth, out)
    return out


def get_app_tree(app_name: str, max_depth: int = 6) -> dict:
    """获取某个应用的完整UI树"""
    apps = _list_apps()
    target = None
    for a in apps:
        if app_name in a["name"]:
            target = a
            break
    if not target:
        return {"error": f"App not found: {app_name}", "apps": [a["name"] for a in apps]}

    ax = _ax_app(target["pid"])
    win = _g(ax, kAXFocusedWindowAttribute)
    win_title = _g(win, kAXTitleAttribute) if win else None

    elements = _walk(ax, max_depth=max_depth)
    return {
        "app": target["name"],
        "pid": target["pid"],
        "window": str(win_title or ""),
        "elements": [
            {k: v for k, v in e.items() if k != "_ax_element"}
            for e in elements
        ],
        "count": len(elements),
    }


def act_on_label(app_name: str, label_contains: str, action: str = "click", value: str = "") -> dict:
    """找到含指定label的元素并执行动作"""
    apps = _list_apps()
    target = None
    for a in apps:
        if app_name in a["name"]:
            target = a
            break
    if not target:
        return {"error": "App not found"}

    ax = _ax_app(target["pid"])
    elements = _walk(ax, max_depth=7)

    # 找匹配label的元素
    matched = None
    for e in elements:
        if e["label"] and label_contains in e["label"]:
            matched = e
            break

    if not matched:
        return {"error": f"No element matching '{label_contains}'", "elements_count": len(elements)}

    el = matched["_ax_element"]

    if action == "click":
        # 拿supported actions
        err, actions = AXUIElementCopyActionNames(el, None)
        action_str = "AXPress"
        if actions and "AXPress" in actions:
            action_str = "AXPress"
        elif actions and "AXConfirm" in actions:
            action_str = "AXConfirm"
        err = AXUIElementPerformAction(el, action_str)
        return {"success": err == 0, "action": action_str, "label": matched["label"]}

    elif action == "type":
        # 先聚焦
        AXUIElementSetAttributeValue(el, kAXFocusedAttribute, True)
        # 设value
        err = AXUIElementSetAttributeValue(el, kAXValueAttribute, value)
        # 尝试AXConfirm，失败则用CGEvent发回车
        err2 = AXUIElementPerformAction(el, "AXConfirm")
        if err2 != 0:
            # Safari等app的AXConfirm返回-25200，用CGEvent模拟回车
            _send_return_key()
            err2 = 0
        return {"success": err == 0, "value": value, "set_err": err, "confirm_err": err2}

    elif action == "press_key":
        AXUIElementSetAttributeValue(el, kAXFocusedAttribute, True)
        _send_key(value or '\n')
        return {"success": True, "key": value}

    elif action == "focus":
        AXUIElementSetAttributeValue(el, kAXFocusedAttribute, True)
        return {"success": True}

    return {"error": f"Unknown action: {action}"}


# ── CGEvent 键盘模拟 ──

def _send_return_key():
    """用CGEvent发回车键——Safari等app的AXConfirm不work时的fallback"""
    _send_key('\n')


def _send_key(key: str):
    """用CGEvent发送单个按键。只支持回车/空格/ESC/Tab等常见键。"""
    from Quartz import (
        CGEventCreateKeyboardEvent, CGEventPost, kCGHIDEventTap,
        kCGEventKeyDown, kCGEventKeyUp,
    )

    key_map = {
        '\n': 36,   # Return
        '\r': 36,   # Return
        '\t': 48,   # Tab
        ' ': 49,    # Space
        '\x1b': 53, # ESC
        '\x08': 51, # Delete
        'a': 0, 'b': 11, 'c': 8, 'd': 2, 'e': 14, 'f': 3, 'g': 5,
        'h': 4, 'i': 34, 'j': 38, 'k': 40, 'l': 37, 'm': 46, 'n': 45,
        'o': 31, 'p': 35, 'q': 12, 'r': 15, 's': 1, 't': 17, 'u': 32,
        'v': 9, 'w': 13, 'x': 7, 'y': 16, 'z': 6,
        '0': 29, '1': 18, '2': 19, '3': 20, '4': 21,
        '5': 23, '6': 22, '7': 26, '8': 28, '9': 25,
    }

    keycode = key_map.get(key, 36)  # 默认回车

    # 模拟 key down + key up
    down = CGEventCreateKeyboardEvent(None, keycode, True)
    up = CGEventCreateKeyboardEvent(None, keycode, False)
    CGEventPost(kCGHIDEventTap, down)
    CGEventPost(kCGHIDEventTap, up)


def menu_click(app_name: str, menu_path: list[str]) -> dict:
    """操作macOS app菜单。
    menu_click("Safari", ["文件", "新建窗口"])
    每步：找到MenuBarItem → AXPress展开 → 子菜单里找MenuItem → AXPress
    """
    apps = _list_apps()
    target = None
    for a in apps:
        if app_name in a["name"]:
            target = a
            break
    if not target:
        return {"error": f"App not found: {app_name}"}

    ax = _ax_app(target["pid"])

    # 第一步：找到菜单栏
    menubar = None
    children = _g(ax, kAXChildrenAttribute) or []
    for c in children:
        role = _g(c, kAXRoleAttribute) or ""
        if "MenuBar" in role:
            menubar = c
            break

    if not menubar:
        return {"error": "No menu bar found"}

    current = menubar
    results = []

    for i, item_label in enumerate(menu_path):
        items = _g(current, kAXChildrenAttribute) or []
        found = None
        for item in items:
            t = _g(item, kAXTitleAttribute) or ""
            if item_label in t:
                found = item
                break

        if not found:
            # 可能菜单还没展开，先press父项
            if i > 0 and results:
                AXUIElementPerformAction(current, "AXPress")
                import time; time.sleep(0.3)
                items = _g(current, kAXChildrenAttribute) or []
                for item in items:
                    t = _g(item, kAXTitleAttribute) or ""
                    if item_label in t:
                        found = item
                        break

        if not found:
            labels = [_g(it, kAXTitleAttribute) or "" for it in items[:10]]
            return {"error": f"Menu item '{item_label}' not found",
                    "available": labels}

        # 展开这个菜单项
        AXUIElementPerformAction(found, "AXPress")
        import time; time.sleep(0.2)
        results.append({"label": item_label, "pressed": True})

        # 下一层：子菜单
        sub = _g(found, kAXChildrenAttribute) or []
        if sub:
            current = sub[0]  # AXMenu是唯一的子元素

    return {"success": True, "path": menu_path, "results": results}


def safari_navigate(url: str) -> dict:
    """Safari专用导航——在起始页搜索栏输入URL并跳转。
    击败了-25200/找不到地址栏等问题。
    """
    apps = _list_apps()
    target = None
    for a in apps:
        if "Safari" in a["name"]:
            target = a
            break
    if not target:
        return {"error": "Safari not running"}

    ax = _ax_app(target["pid"])
    err, windows = AXUIElementCopyAttributeValue(ax, "AXWindows", None)
    if not windows:
        # 打开新窗口
        menu_click("Safari", ["文件", "新建窗口"])
        import time; time.sleep(2)
        err, windows = AXUIElementCopyAttributeValue(ax, "AXWindows", None)
    if not windows:
        return {"error": "No Safari windows"}

    win = windows[0]
    elements = _walk(win, max_depth=7)
    tf = None
    for e in elements:
        el = e["_ax_element"]
        role = _g(el, kAXRoleAttribute) or ""
        if "TextField" in role or "SearchField" in role:
            tf = el
            break

    if not tf:
        return {"error": "No textfield in Safari window (not on start page?)"}

    AXUIElementSetAttributeValue(tf, kAXFocusedAttribute, True)
    AXUIElementSetAttributeValue(tf, kAXValueAttribute, url)
    AXUIElementPerformAction(tf, "AXConfirm")

    import time; time.sleep(3)
    new_title = _g(win, kAXTitleAttribute) or ""
    return {"success": True, "url": url, "window_title": new_title}


if __name__ == "__main__":
    import json

    print("=== 当前所有GUI应用 ===")
    apps = _list_apps()
    for a in apps:
        print(f"  {a['name']} (PID={a['pid']})")
    print()

    print("=== 备忘录UI树（前20个元素） ===")
    tree = get_app_tree("备忘录", max_depth=5)
    for e in tree["elements"][:20]:
        print(f"  [{e['role']}] {e['label']!r:.40} value={e.get('value', '')!r:.20}")

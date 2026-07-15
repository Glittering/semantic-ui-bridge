"""
真实端到端测试：用 SUB 打开本地 HTML，抓树 → 查找 → 点击 → 输入 → 看diff变化
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from semantic_ui_bridge.core.models import Action, UIRole
from semantic_ui_bridge.adapters.playwright_adapter import PlaywrightAdapter
from semantic_ui_bridge.core.protocol import SemanticUIBridge


def print_tree(tree, max_depth=3):
    """简洁打印树"""
    def _print(el, d=0):
        if d > max_depth:
            return
        prefix = "  " * d
        label = el.label or "(none)"
        val = f" val='{el.value}'" if el.value else ""
        print(f"{prefix}[{el.role.value}] id={el.id}: {label}{val}")
        for ch in el.children:
            _print(ch, d + 1)

    print(f"App: {tree.app_title}")
    _print(tree.root, 0)


async def main():
    adapter = PlaywrightAdapter(headless=True)
    bridge = SemanticUIBridge(adapter)

    page_url = "file://" + str(Path(__file__).resolve().parent / "demo_page.html")
    await adapter.connect(page_url)
    await asyncio.sleep(1)

    # 1. 初始树
    print("\n========== 初始语义树 ==========")
    tree = await bridge.get_tree()
    print_tree(tree)

    # 2. 查找按钮
    print("\n========== 查找所有按钮 ==========")
    buttons = await bridge.find(role=UIRole.BUTTON)
    print(f"找到 {len(buttons)} 个按钮:")
    for b in buttons:
        print(f"  id={b.id} label='{b.label}'")

    # 3. 查找文本框
    print("\n========== 查找所有文本框 ==========")
    textboxes = await bridge.find(role=UIRole.TEXTBOX)
    print(f"找到 {len(textboxes)} 个文本框:")
    for tb in textboxes:
        print(f"  id={tb.id} label='{tb.label}' value='{tb.value}'")

    # 4. 在文本框输入
    if textboxes:
        tb = textboxes[0]
        print(f"\n========== 在 '{tb.label}' (id={tb.id}) 输入 '无障碍测试' ==========")
        action = Action(action="type", target=tb.id, params={"text": "无障碍测试"})
        result = await bridge.act(action)
        print(f"success={result.success}")
        if result.diff:
            print(f"Diff: {result.diff}")
        if result.error:
            print(f"Error: {result.error}")

        await asyncio.sleep(0.5)

        # 验证输入后的树
        print("\n--- 输入后的树（变化部分）---")
        tree2 = await bridge.get_tree()
        # 只打印有 value 变化的节点
        tbs2 = await bridge.find(role=UIRole.TEXTBOX)
        for tb2 in tbs2:
            print(f"  id={tb2.id} value='{tb2.value}'")

    # 5. 点击按钮 "点击我"
    if buttons:
        btn = next((b for b in buttons if b.label and "点击我" in b.label), buttons[0])
        print(f"\n========== 点击 '{btn.label}' (id={btn.id}) ==========")
        action = Action(action="click", target=btn.id)
        result = await bridge.act(action)
        print(f"success={result.success}")
        if result.diff:
            print(f"Diff: {result.diff}")
        if result.error:
            print(f"Error: {result.error}")

        await asyncio.sleep(0.5)

        # 确认 result div 内容变化
        print("\n--- 点击后的树（找 result div）---")
        tree3 = await bridge.get_tree()
        # 查找 id 或 label 匹配 'result' 的
        results = await bridge.find(label_contains="按钮1")
        for r in results:
            print(f"  [{r.role.value}] id={r.id} label='{r.label}'")

    print("\n========== 全程完成 ==========")
    await adapter.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
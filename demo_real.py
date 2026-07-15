"""
用修复后的 SUB bridge 操作真实网页
"""
import asyncio
import sys
from pathlib import Path
sys.path.insert(0, '.')

from semantic_ui_bridge.core.models import Action, UIRole
from semantic_ui_bridge.adapters.playwright_adapter import PlaywrightAdapter
from semantic_ui_bridge.core.protocol import SemanticUIBridge


def print_summary(tree):
    """打印关键可交互元素"""
    print(f"App: {tree.app_title}")
    print(f"Focus: {tree.focused_element_id}")
    interactives = []
    def collect(el):
        if el.role.value in ("button", "textbox", "checkbox", "select", "slider"):
            interactives.append(el)
        for ch in el.children:
            collect(ch)
    collect(tree.root)
    print(f"可交互元素: {len(interactives)} 个")
    for el in interactives[:15]:
        states = ",".join(el.states[:3]) if el.states else ""
        val = f" val='{el.value}'" if el.value else ""
        print(f"  [{el.role.value}] id={el.id} label='{el.label}'{val} states={states}")


async def main():
    adapter = PlaywrightAdapter(headless=True)
    bridge = SemanticUIBridge(adapter)

    # 打开 example.com（能访问的简单站点）
    print("=== 连接 http://example.com ===")
    await adapter.connect("http://example.com")
    await asyncio.sleep(1)

    tree = await bridge.get_tree()
    print_summary(tree)

    # 找链接
    links = await bridge.find(role=UIRole.BUTTON)
    print(f"\n找到 {len(links)} 个按钮/链接:")
    for l in links:
        print(f"  id={l.id} label='{l.label}'")

    # 尝试点击第一个链接
    if links:
        link = links[0]
        print(f"\n=== 点击 '{link.label}' (id={link.id}) ===")
        action = Action(action="click", target=link.id)
        result = await bridge.act(action)
        print(f"success={result.success}")
        if result.diff:
            print(f"Diff ({len(result.diff)} changes):")
            for d in result.diff[:8]:
                print(f"  {d}")
        if result.error:
            print(f"Error: {result.error}")

        await asyncio.sleep(1)
        tree2 = await bridge.get_tree()
        print(f"\n点击后页面: {tree2.app_title}")
        print(f"顶层元素: {len(tree2.root.children)}")

    print("\n========== 完成 ==========")
    await adapter.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
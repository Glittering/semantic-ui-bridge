"""Semantic UI Bridge — Quick Verification Script
验证 import 链 + 一个最基本的 round-trip。
不替代正式测试，只是快速烟雾测试。"""

import asyncio
import sys
from pathlib import Path

# 确保 src/ 在 sys.path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.models import UIRole, UIElement, UITree, Action, ActionResult
from src.core.normalizer import Normalizer
from src.core.errors import SUBTimeoutError
from src.adapters.playwright_adapter import PlaywrightAdapter
from src.core.protocol import SemanticUIBridge


async def smoke_test():
    print("✓ 所有模块 import 成功")

    # 基本模型创建
    el = UIElement(id="btn-1", role=UIRole.BUTTON, label="Test")
    print(f"✓ UIElement 创建: {el.label}")

    # Normalizer
    norm = Normalizer()
    raw = {"id": "root", "role": "group", "label": "", "states": [], "children": [
        {"id": "btn", "role": "button", "label": "OK", "states": ["visible"], "children": [], "actions": []}
    ], "actions": []}
    tree = norm.normalize_tree(raw)
    print(f"✓ Normalizer: {len(tree.root.children)} children, role={tree.root.children[0].role.value}")

    # Protocol + Adapter quick live test
    adapter = PlaywrightAdapter()
    await adapter.connect("https://example.com")
    bridge = SemanticUIBridge(adapter)
    tree = await bridge.get_tree()
    print(f"✓ get_tree() 成功: root role={tree.root.role.value}, timestamp={tree.timestamp}")
    text_elements = await bridge.find(label_contains="Example")
    print(f"✓ find() 找到 {len(text_elements)} 个匹配 'Example' 的元素")
    await adapter.disconnect()

    print("\n─── Smoke test PASSED ───")


if __name__ == "__main__":
    asyncio.run(smoke_test())
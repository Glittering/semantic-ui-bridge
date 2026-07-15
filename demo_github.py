"""生成 GitHub README demo GIF 的脚本
用 asciinema 或直接 print 效果
"""

import asyncio
import sys
sys.path.insert(0, '.')

from semantic_ui_bridge.adapters.unified import SUB

async def demo():
    print("╔══════════════════════════════════════════╗")
    print("║   Semantic UI Bridge — Live Demo        ║")
    print("║   AI controls desktop without pixels    ║")
    print("╚══════════════════════════════════════════╝")
    print()

    # 1. 列出所有GUI应用
    print(">>> SUB.list_apps()")
    apps = SUB.list_apps()
    names = [a['name'] for a in apps[:10]]
    print(f"    {len(apps)} GUI apps running: {', '.join(names[:8])}...")
    print()

    # 2. 读备忘录
    print(">>> SUB.get_tree('备忘录')")
    tree = await SUB.get_tree('备忘录', max_depth=3)
    print(f"    Window: {tree['window']}")
    print(f"    Elements: {tree['count']}")
    labeled = [e for e in tree['elements'] if e.get('label')][:6]
    for e in labeled:
        print(f"      [{e['role']}] {e['label'][:40]}")
    print()

    # 3. 浏览文件
    print(">>> SUB.ls('~/Documents/trae_projects/semantic-ui-bridge/', pattern='.py')")
    files = SUB.ls('/Users/Zhuanz/Documents/trae_projects/semantic-ui-bridge/', pattern='.py', limit=5)
    for f in files['items']:
        print(f"    {f['mtime']}  {f['size']:>6}B  {f['name']}")
    print()

    # 4. Safari导航+网页提取
    print(">>> SUB.safari_go('https://www.xinhuanet.com/')")
    r = SUB.safari_go('https://www.xinhuanet.com/')
    print(f"    Navigation: {r.get('window_title', r.get('error'))}")
    print()

    print(">>> SUB.get_web_content('https://www.xinhuanet.com/')")
    news = await SUB.get_web_content('https://www.xinhuanet.com/', wait_ms=4000)
    print(f"    {len(news)} links extracted")
    for n in news[:5]:
        print(f"      • {n['text'][:50]}")
    print()

    # 5. 菜单操作
    print(">>> SUB.menu_action('Safari', ['文件'])")
    r = await SUB.menu_action('Safari', ['文件'])
    print(f"    expanded: {r.get('success')}")
    print()

    print("═══ Demo complete. 0 screenshots, 0 OCR, 0 coordinates. ═══")

if __name__ == '__main__':
    asyncio.run(demo())
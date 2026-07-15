# Semantic UI Bridge（语义 UI 桥）

AI Agent 不需要截图，不需要 OCR，不需要猜坐标。

让 AI 像调 API 一样操控桌面和网页。

## 一句话

把人类视觉世界的像素屏障拆掉——AI 看到的是结构化语义树，操作的是 API 调用，永远不需要知道坐标和像素存在。

## 架构

```
Agent (LLM)
    │
    ▼
  SUB  ── 统一入口
    │
    ├── target="http://..." ──► Playwright Adapter + DOM提取
    │
    └── target="app名" ─────► macOS AX Adapter
```

## 30 秒演示

```
>>> SUB.list_apps()
    13 GUI apps: Safari, 备忘录, 终端, 访达, 活动监视器, TRAE...

>>> SUB.get_tree("备忘录")
    Window: iCloud全部 – 52个备忘录
    Elements: 285
      [group]  备忘录
      [dialog] iCloud全部 – 52个备忘录
      [text]   2026年7月15日 16:08
      [text]   iCloud全部
      [text]   52个备忘录

>>> SUB.safari_go("https://www.xinhuanet.com/")
    Navigation: 新华网_让新闻离你更近          ← 窗口标题确认

>>> SUB.get_web_content("https://www.xinhuanet.com/")
    348 links extracted
      • 哈萨克斯坦总统托卡耶夫抵达上海
      • 美国环孢子虫病例破纪录
      • 港股15日涨1.4% 收报24681.1点

>>> SUB.ls("~/Documents/trae_projects/", pattern=".py")
    2026-07-16  2,374B  demo_github.py
    2026-07-16  3,630B  demo_end_to_end.py

>>> SUB.menu_action("Safari", ["文件", "新建窗口"])
    expanded: True  ← 菜单成功打开

═══ 0 screenshots, 0 OCR, 0 coordinates. ═══
```

## 安装

```bash
pip install semantic-ui-bridge
# 或
uv pip install playwright pyobjc-core pyobjc-framework-ApplicationServices pyobjc-framework-Cocoa pyobjc-framework-Quartz
python -m playwright install chromium
```

**macOS Accessibility 权限**（需要一次手动授权）：
系统设置 → 隐私与安全性 → 辅助功能 → 允许你的 Python 进程。

## 使用

```python
from src.adapters.unified import SUB
import asyncio

# 1. Safari一键导航
SUB.safari_go("https://news.sina.com.cn/")

# 2. 提取网页正文
async def news():
    items = await SUB.get_web_content("https://www.xinhuanet.com/")
    for n in items[:5]:
        print(n["text"])

asyncio.run(news())

# 3. 读桌面app UI树（不截图不OCR）
tree = SUB.get_tree("备忘录")
print(tree["window"])  # → "iCloud全部 – 52个备忘录"

# 4. 操作app菜单
r = SUB.menu_action("Safari", ["文件", "新建窗口"])

# 5. 浏览文件系统
files = SUB.ls("~/Documents/trae_projects/", pattern=".md")
```

## 实测验证（2026-07-15）

| 场景 | 结果 | 数据 |
|------|------|------|
| 备忘录UI树 | ✅ | 285个元素，133个有label |
| 访达UI树 | ✅ | 283个元素，149个有label |
| Safari菜单操作 | ✅ | "文件→新建窗口"成功 |
| Safari导航 | ✅ | 新华网/新浪新闻成功 |
| 网页DOM | ✅ | 新华网338条链接，新浪606条链接 |

**不能做的事**：游戏画面、PS画布、精确拖拽、视频/图片理解。

## 测试

```bash
pytest tests/test_models.py tests/test_normalizer.py tests/test_protocol.py tests/test_playwright_adapter.py -v
# 79 passed, 2 skipped, 0 failed
```

## 为什么要做这个？

现有方案让 AI 操作界面是在"逆向工程人类浏览器"——截图→OCR→猜坐标→模拟点击。这条路的每一步都有可能出错。无障碍 API（AX/UIA/AT-SPI）早已内建在操作系统中，只是从未被整理成 AI 能直接调用的接口。Semantic UI Bridge 就是把这块已有的富矿挖出来，做成 Agent 的 API。

## 白皮书

`docs/WHITEPAPER.md` — 完整问题分析、三层架构、AI Native Render 理念。

## License

MIT
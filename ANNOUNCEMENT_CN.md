## 让 AI 操控电脑，不需要截图、不需要 OCR、不需要点坐标

我做了一个 Python 库，叫 **Semantic UI Bridge**。

一句话：AI Agent 不需要"看屏幕"。它直接读操作系统内建的 UI 结构树。

---

### 问题

现在的 AI agent 操控电脑的方案都是：

1. 截图桌面/网页
2. 送进视觉模型 OCR 识别按钮位置
3. 模拟鼠标移动到坐标 (x=320, y=194)
4. 点击

这条路每一步都可能出错——字体变了坐标偏移、弹窗遮住按钮、DOM JS动态渲染延迟。

### 发现

macOS 操作系统里，**每一帧 UI 已经在渲染时同步产出了完整的结构化树**——AXApplication → AXWindow → AXButton → AXStaticText → ... 每个元素的 label、value、坐标、role、父子关系，全有。

不是"新造"的东西——**这是 2012 年就内建在 macOS 里的 Accessibility API**。Windows 有 UI Automation，Linux 有 AT-SPI。它们一直就在那儿，只是从来没人把它们整理成 AI 可以直接调用的 SDK。

### Semantic UI Bridge 做了什么

把这块"已有的富矿"挖出来，做成一个 Python 库：

```python
from semantic_ui_bridge import SUB

# 1. 读桌面app UI树——不截图、不OCR
tree = SUB.get_tree("备忘录")
# → window="iCloud全部 – 52个备忘录"，285个元素，133个有label

# 2. 一键 Safari 导航
SUB.safari_go("https://news.sina.com.cn/")

# 3. 提取网页正文
news = SUB.get_web_content("https://news.sina.com.cn/")
# → 606 条链接全提纯

# 4. 浏览文件系统
SUB.ls("~/Documents/trae_projects/", pattern=".py")

# 5. 操作菜单
SUB.menu_action("Safari", ["文件", "新建窗口"])
```

内置双适配器：macOS Accessibility API（操作原生桌面app）+ Playwright/Chromium（载入网页DOM提取文本）。

### 实测数据

| 场景 | 结果 | 数据 |
|------|------|------|
| 备忘录 UI树 | ✅ | 285元素，133个有label |
| 访达 UI树 | ✅ | 283元素，149个有label |
| Safari一键导航 | ✅ | 新华网/新浪新闻确认 |
| 网页正文提取 | ✅ | 新浪606条链接 |
| 菜单操作 | ✅ | "文件→新建窗口"成功 |

79 个测试，全绿。0 screenshot，0 OCR，0 坐标。

### 局限（诚实）

- **游戏**不行：梦幻西游等自绘 Metal/OpenGL 不走 AppKit，AX 拿不到。
- **PS / Figma 画布**不行：专业工具画布内容不走 AX。
- **Windows/Linux** 还没适配：macOS 先行。Windows UIA 和 Linux AT-SPI 架构上兼容，需要 Adapter。

### 为什么不做 AI 专用浏览器？

项目中讨论了另两个更激进的方向（Chromium 内核做 AI native 渲染 + 系统级渲染管线插件），最终选择了"统一语义接口层"——不造新浏览器，不给内核打补丁，把现有的 Accessibility API 封装成 Agent SDK。成本最低、稳定性最高、兼容性最高。

项目里有完整白皮书：`docs/WHITEPAPER.md`。

### 安装

```bash
pip install semantic-ui-bridge[macos]
playwright install chromium
```

macOS 需要一次手动授权：系统设置 → 隐私与安全性 → 辅助功能 → 允许。

### 地址

https://github.com/Glittering/semantic-ui-bridge

MIT License。欢迎 issue、PR、试用。
# Semantic UI Bridge — 白皮书 v1.0

> "不要重新发明像素。重新发明AI和UI之间的语言。"
> — Steve Jobs 模式架构评审，2026.07.15

---

## 1. 问题：AI为什么还在"看"屏幕？

当前AI Agent操控图形界面的主流方法是：**截图 → OCR/视觉模型识图 → 推算坐标 → 模拟点击**。这是狗屎设计。

### 为什么狗屎？

| 维度 | 截图/识图 | 结构化接口 |
|------|----------|-----------|
| 准确率 | 85-95%（OCR出错、遮挡、相似元素） | 100%（直接拿到语义） |
| 延迟 | 截图1s + 模型推理2-5s = 3-6s | API调用 <100ms |
| Token消耗 | 一张图=数千token | 结构化JSON=几十token |
| 动态UI | 每帧都要截图 | 事件推送，0截图 |
| 暗黑模式/缩放 | 模型容易混淆 | 不依赖视觉渲染 |

根本原因不是技术不存在——Accessibility API（Windows UIA、macOS AX、Linux AT-SPI）、Chromium DevTools Protocol（CDP）、ARIA语义标注——这些结构化接口已经存在了10-25年。但从来没有人把它们整理成Agent可以直接调用的格式。

---

## 2. 洞察：富矿已在脚下

### 已有结构化数据源

| 层 | 接口 | 能力 | 存在时间 |
|----|------|------|---------|
| 浏览器 DOM | CDP / DOM.getDocument | 完整DOM树+computed style+事件 | 2015+ |
| 浏览器可访问性 | CDP / Accessibility.getFullAXTree | 语义角色树+属性+状态 | 2019+ |
| Windows 桌面 | UI Automation (UIA) | 所有原生控件树+属性+动作 | 2005+ |
| macOS 桌面 | Accessibility API (AX) | 所有原生+Web控件树 | 2003+ |
| Linux 桌面 | AT-SPI2 | 跨应用控件树 | 2002+ |
| Android | UIAutomator / AccessibilityService | 完整View树 | 2013+ |
| iOS | XCUITest / Accessibility | UIKit控件树 | 2015+ |

这些API为盲人辅助技术设计。讽刺的是：它们恰好是AI的完美接口——结构化、语义化、可操作。只是从来没人给它们包一层AI SDK。

---

## 3. Semantic UI Bridge：三层架构

```
┌─────────────────────────────────────────────────┐
│                  Agent (LLM)                    │
│         调用统一的 UI Protocol API              │
└──────────────────┬──────────────────────────────┘
                   │ 统一 JSON-RPC / REST
┌──────────────────▼──────────────────────────────┐
│         Semantic UI Bridge Core                 │
│                                                 │
│  ┌───────────────────────────────────────────┐ │
│  │  Protocol Layer                           │ │
│  │  - UI Tree Schema (统一数据模型)          │ │
│  │  - Action Bus (统一操作模型)              │ │
│  │  - Event Stream (状态变更推送)            │ │
│  └───────────────────────────────────────────┘ │
│                      │                          │
│  ┌───────────────────────────────────────────┐ │
│  │  Normalizer Layer                         │ │
│  │  - 跨平台控件角色映射                     │ │
│  │  - 语义去噪（砍掉布局噪音）               │ │
│  │  - 智能分组（语义聚类）                   │ │
│  └───────────────────────────────────────────┘ │
└──────────────────┬──────────────────────────────┘
                   │ 多适配器
     ┌─────────────┼─────────────┬──────────────┐
     ▼             ▼             ▼              ▼
┌─────────┐ ┌──────────┐ ┌──────────┐  ┌──────────┐
│ Browser │ │ Windows  │ │  macOS   │  │  Linux   │
│ Adapter │ │   UIA    │ │    AX    │  │ AT-SPI2  │
│ (CDP)   │ │ Adapter  │ │ Adapter  │  │ Adapter  │
└─────────┘ └──────────┘ └──────────┘  └──────────┘
```

### Layer 1: Adapters（适配器层）
- 每个平台一个适配器
- 负责调用底层API，产出原始控件树
- 处理平台特有的噩魔细节（UIA线程模型、AX异步回调等）

### Layer 2: Normalizer（标准化层）
- 把不同平台的控件角色映射到统一Schema
- 语义去噪：砍掉纯布局节点（div/container/group-without-semantics）
- 智能分组：把相邻相关元素聚合成逻辑块

### Layer 3: Protocol（协议层）
- 暴露统一的JSON API给Agent
- 三个核心能力：`get_tree` / `act` / `subscribe`
- 每个元素包含：语义角色、标签、状态、可用动作、位置（可选，仅用于需要空间的场景）

---

## 4. 核心数据模型

### UIElement（单个元素）

```json
{
  "id": "e:compose-127",
  "role": "button",
  "label": "提交订单",
  "states": ["enabled", "focusable", "visible"],
  "value": null,
  "actions": ["click", "focus"],
  "bounds": { "x": 320, "y": 480, "w": 120, "h": 40 },
  "children_count": 0,
  "semantic_weight": 0.9
}
```

### UITree（完整界面树）

```json
{
  "app": {
    "name": "chrome",
    "title": "GitHub - Issues",
    "pid": 28471
  },
  "root": { /* UIElement树 */ },
  "timestamp": 1752569600.123,
  "tree_size": 47,
  "interactive_elements": 12,
  "focused_element": "e:textbox-15"
}
```

### Action（Agent调用动作）

```json
{
  "action": "click",
  "target": "e:button-42",
  "params": {}
}
```

```json
{
  "action": "type",
  "target": "e:textbox-15",
  "params": { "text": "Hello World" }
}
```

### ActionResult

```json
{
  "success": true,
  "action": "click",
  "target": "e:button-42",
  "result_tree": { /* 点击后的新UITree */ },
  "diff": ["e:dialog-99: new", "e:button-42: state changed"]
}
```

---

## 5. 统一控件角色映射（42种→10种核心角色）

砍掉Accessibility API的42+种角色。对Agent来说，只需要10种：

| 统一角色 | 涵盖的原始角色 | Agent理解 |
|---------|--------------|----------|
| `button` | button, link, menuitem, tab | "可点击触发动作" |
| `textbox` | textbox, searchbox, combobox | "可输入文本" |
| `text` | statictext, label, heading, paragraph | "只读文本内容" |
| `checkbox` | checkbox, radio, toggle | "二态切换" |
| `select` | list, listbox, menu, dropdown | "从列表中选择" |
| `slider` | slider, scrollbar, progressbar | "连续值调节" |
| `image` | image, diagram, chart | "非交互视觉元素" |
| `table` | table, grid, datagrid | "表格数据" |
| `dialog` | dialog, alert, window | "弹出层" |
| `group` | group, pane, toolbar, region | "容器/分组" |

---

## 6. 核心API

```
SUB.ui.get_tree(app_name=None, focused_only=False)
  → UITree

SUB.ui.find(role=None, label_contains=None, states=None)
  → [UIElement]

SUB.ui.act(action, target, params={})
  → ActionResult

SUB.ui.subscribe(app_name, events=["focus", "open", "close", "text_change"])
  → EventStream

SUB.ui.wait_for(condition, timeout=30)
  → UITree  # 阻塞直到条件满足（如：某按钮出现）

SUB.ui.screenshot(region=None)  # 降级：只在必要时提供视觉
  → base64 PNG
```

Agent的典型工作流：
```
tree = SUB.ui.get_tree()
button = SUB.ui.find(role="button", label_contains="提交")[0]
result = SUB.ui.act("click", button.id)
```

---

## 7. MVP范围

### 砍掉（不是因为不重要，而是因为不是灵魂）

- ❌ 跨平台桌面适配器（Windows UIA / Mac AX / Linux AT-SPI）
- ❌ 移动端适配器（Android / iOS）
- ❌ 视觉截图降级模式
- ❌ Web Dashboard / 管理界面

### 留下（灵魂功能）

- ✅ **Browser Adapter**：基于Playwright CDP，完整DOM语义树输出
- ✅ **Protocol Layer**：统一UIElement/UITree/Action/ActionResult数据模型
- ✅ **Core API**：get_tree / act / find / wait_for
- ✅ **Python SDK**：`from semantic_ui_bridge import SUB`
- ✅ **测试全覆盖**：单元测试 + 真实页面集成测试

### MVP一句话定义
> 一个Python库。Agent调用 `SUB.ui.get_tree()` 就能拿到任何网页的结构化UI树，调用 `SUB.ui.act("click", id)` 就能操作——不截图、不OCR、不猜测坐标。稳定、快速、100%准确。

---

## 8. 开发原则：测试先行

1. 先写测试用例（定义期望行为）
2. 测试红（失败）——证明测试有效
3. 写最小实现让测试绿（通过）
4. 重构——测试保护
5. 每个模块：`tests/test_<module>.py` 在 `<module>.py` 之前创建

---

## 9. 非目标（明确不做什么）

- 不做新浏览器（Chromium够好了）
- 不碰渲染管线/内核（政治自杀）
- 不做GUI配置界面（这是给AI用的，不是给人看的）
- 不训练新模型（1.0是协议+SDK，2.0才是模型）
- 不做自然语言→动作的翻译层（那是Agent的事，我们只提供接口）

---

## 10. 成功标准

| 指标 | 目标 |
|------|------|
| get_tree() 延迟 | <100ms |
| act() 延迟 | <50ms + 页面响应时间 |
| 语义准确率 | 100%（与人工标注对比） |
| 跨页面通用性 | 任意网页，0配置 |
| 测试覆盖率 | >90% |
| Agent集成体验 | 3行代码拿到完整UI树 |

---

*这份白皮书代表一个产品，不是一个研究项目。它要么Insanely Great，要么不值得做。我们选择了前者。*
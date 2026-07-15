# Semantic UI Bridge — 技术规格 v1.0

## 技术栈

| 组件 | 选择 | 理由 |
|------|------|------|
| 浏览器自动化引擎 | Playwright (Python) | CDP全能力 + 跨浏览器 + 生产级 |
| 核心语言 | Python 3.12+ | Agent生态首选 + asyncio优秀 |
| 数据模型 | Pydantic v2 | 验证+序列化+JSON Schema自动生成 |
| 测试框架 | pytest + pytest-asyncio | 异步测试支持 |
| 类型检查 | mypy strict | 必须 |
| 包管理 | uv (pip兼容) | 快 |
| 异步运行时 | asyncio | Playwright原生异步 |

## 依赖

```toml
[project]
name = "semantic-ui-bridge"
version = "0.1.0"
description = "AI Agent's universal interface to graphical UIs — no screenshots, no OCR."
requires-python = ">=3.12"
dependencies = [
    "playwright>=1.45",
    "pydantic>=2.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "mypy>=1.0",
    "ruff>=0.5",
]
```

## 模块结构

```
src/
├── core/
│   ├── __init__.py
│   ├── models.py        # UIElement, UITree, Action, ActionResult (Pydantic)
│   ├── protocol.py      # SUB.ui.* API (get_tree, act, find, wait_for)
│   ├── normalizer.py    # 语义去噪 + 角色映射 + 智能分组
│   └── errors.py        # 自定义异常类
├── adapters/
│   ├── __init__.py
│   ├── base.py          # BaseAdapter 抽象类
│   └── playwright_adapter.py  # Playwright/CDP 浏览器适配器
└── __init__.py           # 顶层 import: from semantic_ui_bridge import SUB
```

## 测试结构

```
tests/
├── conftest.py           # fixtures: 浏览器实例 + 测试页面
├── test_models.py        # Pydantic模型验证
├── test_normalizer.py    # 标准化逻辑
├── test_protocol.py      # Protocol层API
├── test_playwright_adapter.py  # 适配器集成测试
└── test_integration.py   # 端到端：真实网页
```

## 核心类签名

### models.py

```python
from enum import StrEnum
from pydantic import BaseModel, Field

class UIRole(StrEnum):
    BUTTON = "button"
    TEXTBOX = "textbox"
    TEXT = "text"
    CHECKBOX = "checkbox"
    SELECT = "select"
    SLIDER = "slider"
    IMAGE = "image"
    TABLE = "table"
    DIALOG = "dialog"
    GROUP = "group"

class UIElement(BaseModel):
    id: str
    role: UIRole
    label: str | None = None
    states: list[str] = Field(default_factory=list)
    value: str | None = None
    actions: list[str] = Field(default_factory=list)
    children: list["UIElement"] = Field(default_factory=list)
    bounds: dict | None = None  # {x,y,w,h} optional

class UITree(BaseModel):
    app_name: str
    app_title: str
    root: UIElement
    timestamp: float
    focused_element_id: str | None = None

class Action(BaseModel):
    action: str  # click, type, select, focus, scroll
    target: str  # element id
    params: dict = Field(default_factory=dict)

class ActionResult(BaseModel):
    success: bool
    action: Action
    result_tree: UITree | None = None
    diff: list[str] = Field(default_factory=list)
    error: str | None = None
```

### protocol.py

```python
class SemanticUIBridge:
    """SUB.ui — Agent的单一入口"""
    
    def __init__(self, adapter: BaseAdapter):
        ...
    
    async def get_tree(self, focused_only: bool = False) -> UITree:
        """返回当前页面的完整语义UI树"""
        ...
    
    async def find(self, role: UIRole | None = None,
                   label_contains: str | None = None,
                   states: list[str] | None = None) -> list[UIElement]:
        """按条件搜索UI元素"""
        ...
    
    async def act(self, action: Action) -> ActionResult:
        """执行动作并返回结果树+diffs"""
        ...
    
    async def wait_for(self, condition: Callable[[UITree], bool],
                       timeout: float = 30) -> UITree:
        """轮询等待某条件满足"""
        ...
```

### base.py (Adapter抽象)

```python
class BaseAdapter(ABC):
    """平台适配器抽象"""
    
    @abstractmethod
    async def connect(self, target: str) -> None:
        """连接目标（URL / PID / window title）"""
        ...
    
    @abstractmethod
    async def get_raw_tree(self) -> dict:
        """获取原始控件树（平台特定格式）"""
        ...
    
    @abstractmethod
    async def execute_action(self, element_id: str, action: str, params: dict) -> dict:
        """执行底层操作"""
        ...
    
    @abstractmethod
    async def disconnect(self) -> None:
        ...
```

### normalizer.py

```python
class Normalizer:
    """把原始平台树 → 统一UIElement树"""
    
    ROLE_MAP: dict[str, UIRole]  # 平台角色→统一角色
    
    def normalize_element(self, raw: dict) -> UIElement:
        ...
    
    def denoise_tree(self, root: UIElement) -> UIElement:
        """砍掉纯布局节点，只留语义节点"""
        ...
```

### playwright_adapter.py

```python
class PlaywrightAdapter(BaseAdapter):
    """基于Playwright CDP的浏览器适配器"""
    
    def __init__(self):
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None
        self._page: Page | None = None
    
    async def connect(self, url: str) -> None:
        ...
    
    async def get_raw_tree(self) -> dict:
        """用CDP Accessibility.getFullAXTree + DOM.getDocument"""
        ...
    
    async def execute_action(self, element_id: str, action: str, params: dict) -> dict:
        """映射到Playwright locator操作"""
        ...
```

## 语义去噪规则

从原始DOM/AX树中砍掉的节点：
1. role=None 或 role=generic 且无交互元素子孙的纯容器
2. 不可见节点（display:none, visibility:hidden, aria-hidden, opacity:0）
3. 纯布局节点（role=group 但只有1个子节点且无语义属性）
4. 重复标签（相邻兄弟标签相同且无交互性差异）

## 执行映射

| Agent Action | Playwright映射 |
|-------------|---------------|
| click | `page.locator(css_or_id).click()` |
| type {text} | `page.locator(css_or_id).fill(text)` |
| select {value} | `page.locator(css_or_id).select_option(value)` |
| focus | `page.locator(css_or_id).focus()` |
| scroll {x,y} | `page.locator(css_or_id).scroll(x,y)` |

---

*此规格是活的——测试驱动开发过程中根据实际发现调整。*
# Semantic UI Bridge — 测试规范 v1.0

## 测试哲学

> 先写测试。测试即需求文档。红线不可破。

### 测试金字塔

```
        ┌──────┐
        │ E2E  │  5%  — test_integration.py（真实网页全链路）
        ├──────┤
        │ 集成  │  25% — test_protocol.py, test_playwright_adapter.py
        ├──────┤
        │ 单元  │  70% — test_models.py, test_normalizer.py, test_errors.py
        └──────┘
```

## 测试按模块分解

### test_models.py — Pydantic模型验证（纯单元，无外部依赖）

| 用例ID | 描述 | 断言 |
|--------|------|------|
| M-001 | UIElement最小有效值 | role=button, id=str → 创建成功 |
| M-002 | UIElement所有可选字段 | 含label/states/value/actions/children → 全保留 |
| M-003 | UIRole枚举限制 | role="invalid" → ValidationError |
| M-004 | UIElement递归children | 嵌套3层 → children正确嵌套 |
| M-005 | UITree完整校验 | 所有必填字段 → 成功 |
| M-006 | Action参数校验 | action="click", target=str → 成功 |
| M-007 | ActionResult.success=True | result_tree非None |
| M-008 | ActionResult.success=False | error非None, result_tree可以为None |
| M-009 | UIElement JSON序列化 | model_dump_json() → 合法JSON |
| M-010 | UIElement从JSON反序列化 | 合法JSON → model_validate正确 |

### test_normalizer.py — 标准化逻辑（纯单元，mock数据）

| 用例ID | 描述 | 输入 | 预期输出 |
|--------|------|------|---------|
| N-001 | 角色映射 | raw_role="pushbutton" | UIRole.BUTTON |
| N-002 | 角色映射 | raw_role="edit" | UIRole.TEXTBOX |
| N-003 | 角色映射 | raw_role="statictext" | UIRole.TEXT |
| N-004 | 角色映射 | raw_role="unknown_xxx" | UIRole.GROUP (fallback) |
| N-005 | 去噪: 砍不可见节点 | states含"invisible" | 节点被砍 |
| N-006 | 去噪: 保留可见节点 | states=["visible","enabled"] | 节点保留 |
| N-007 | 去噪: 砍纯布局容器 | role=group, 无交互子节点 | 节点被砍，子节点提升 |
| N-008 | 去噪: 保留有交互子的group | role=group, 子含button | 节点保留 |
| N-009 | 去噪: 砍全透明节点 | opacity:0 | 节点被砍 |
| N-010 | label去重 | 兄弟节点label相同无语义差异 | 保留第一个 |
| N-011 | 完整normalize流程 | raw_tree(模拟DOM+AX混合) | → UITree正确 |
| N-012 | normalize幂等 | 两次normalize → 结果相同 |

### test_protocol.py — Protocol层（集成：需Playwright+测试用本地HTML）

| 用例ID | 描述 | 前置条件 | 断言 |
|--------|------|---------|------|
| P-001 | get_tree()基本调用 | browser打开test_page | UITree.root非None |
| P-002 | get_tree()返回交互元素 | test_page含3个button | tree含3个role=button |
| P-003 | find(role=button) | test_page含button | 返回列表非空 |
| P-004 | find(label_contains="提交") | test_page有"提交订单"按钮 | 精确返回1个 |
| P-005 | find(states=["disabled"]) | test_page有disabled按钮 | 过滤正确 |
| P-006 | find无匹配返回空列表 | role=dialog, 页面无dialog | [] |
| P-007 | act(click)成功 | click一个button | success=True, diff含变化 |
| P-008 | act(click)失败 | target不存在 | success=False, error非空 |
| P-009 | act(type)输入文本 | textbox填"hello" | 新tree的textbox value="hello" |
| P-010 | act(type)非textbox元素 | target=button | success=False |
| P-011 | wait_for()超时 | 条件永不满足, timeout=1s | raise TimeoutError |
| P-012 | wait_for()成功 | click按钮→弹dialog, wait dialog出现 | 返回含dialog的UITree |
| P-013 | id稳定性 | 两次get_tree()相同元素 | 相同id |
| P-014 | get_tree(focused_only=True) | 某textbox有焦点 | root是focused元素 |

### test_playwright_adapter.py — 适配器集成

| 用例ID | 描述 | 断言 |
|--------|------|------|
| PA-001 | connect(url)启动浏览器 | page.url == url |
| PA-002 | get_raw_tree()返回AX树 | 含nodes列表 |
| PA-003 | execute_action(click)实际点击 | 元素click事件触发 |
| PA-004 | disconnect()清理 | browser已关闭 |
| PA-005 | 重连到不同url | 正常工作 |
| PA-006 | 不存在的url | graceful error |
| PA-007 | 动态加载页面(SPA) | get_raw_tree含动态渲染内容 |

### test_integration.py — 端到端：真实公共网页

| 用例ID | 描述 | 目标页面 | 断言 |
|--------|------|---------|------|
| I-001 | 真实GitHub issue页 get_tree() | github.com某issue | root非None, 含button+textbox+text |
| I-002 | 真实页面 find搜索框 | github.com | 找到textbox含label |
| I-003 | 真实页面 act(type)填搜索 | github.com搜索框 | value正确填入 |
| I-004 | 任意复杂SaaS页无崩溃 | (至少1个现代SPA) | 无exception, tree_size>10 |
| I-005 | Hacker News极简页 | news.ycombinator.com | 语义准确（链接角色正确） |

## 测试基础设施

### conftest.py 提供的 fixtures

```python
@pytest.fixture(scope="session")
async def browser():  # 整个测试session共享一个浏览器实例
    ...

@pytest.fixture
async def fresh_page(browser):  # 每个测试独立新页面
    ...

@pytest.fixture(scope="session")
async def test_html_file(tmp_path_factory):
    """生成一个包含所有控件类型的测试HTML，返回file://路径"""
    ...
```

### 测试HTML内容覆盖

- buttons (enabled + disabled)
- textbox (普通 + password + search)
- checkboxes + radios
- select/dropdown
- links (a标签)
- 嵌套group/container
- 不可见元素 (hidden attribute, display:none, aria-hidden)
- 动态元素 (JS插入的dialog)
- 表格 (简单data table)

## 运行命令

```bash
# 所有单元测试（无浏览器，秒级）
uv run pytest tests/test_models.py tests/test_normalizer.py -v

# 核心集成（需浏览器）
uv run pytest tests/test_protocol.py tests/test_playwright_adapter.py -v

# 全量
uv run pytest -v --cov=src --cov-report=term-missing

# 单文件
uv run pytest tests/test_protocol.py::test_get_tree_basic -v
```

## 测试先行硬规则

1. **测试文件在源码文件之前创建**
2. **第一版测试必须100% FAIL**——验证测试有效性
3. **一次只让一个测试从红变绿**
4. **测试即文档**——测试用例名描述行为，不读源码也能理解API
5. **不测试已有库的行为**——不测Pydantic的ValidationError本身，只测我们的schema
6. **集成测试可跳过**——CI环境无浏览器时 `@pytest.mark.skipif(no_browser)`

---

*测试不是附加品。测试就是产品定义。*
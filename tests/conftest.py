"""Semantic UI Bridge — Test Fixtures

提供的fixtures:
- browser: session级共享浏览器实例
- fresh_page: 每个测试独立新页面
- test_html_file: 包含所有控件类型的测试HTML文件路径
- test_html_url: test_html_file的file:// URL
"""

import pytest
import asyncio
from pathlib import Path
from playwright.async_api import async_playwright, Browser, Page


TEST_HTML_CONTENT = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="UTF-8"><title>SUB Test Page</title>
<style>
  body { font-family: system-ui; max-width: 600px; margin: 40px auto; padding: 20px; }
  .hidden { display: none; }
  .invisible { visibility: hidden; }
  [aria-hidden="true"] { opacity: 0; pointer-events: none; }
  section { margin-bottom: 24px; padding: 16px; border: 1px solid #eee; border-radius: 8px; }
  h2 { font-size: 18px; margin-top: 0; }
  button, input, select { margin: 4px 8px 4px 0; }
  label { display: block; margin: 4px 0; }
  #dynamic-area { min-height: 40px; }
  dialog { border: 2px solid #333; border-radius: 12px; padding: 24px; }
  dialog::backdrop { background: rgba(0,0,0,0.3); }
</style></head>
<body>

<h1>SUB Semantic UI Bridge — Test Page</h1>

<!-- Buttons -->
<section>
  <h2>Buttons</h2>
  <button id="btn-submit" onclick="this.textContent='Clicked!'">提交订单</button>
  <button id="btn-cancel" disabled>取消 (disabled)</button>
  <button id="btn-dialog" onclick="document.getElementById('my-dialog').showModal()">打开 Dialog</button>
  <a href="#top" id="link-home" role="button">返回首页 (link)</a>
</section>

<!-- Textboxes -->
<section>
  <h2>Inputs</h2>
  <label for="tb-search">搜索框:</label>
  <input type="search" id="tb-search" placeholder="输入关键词...">

  <label for="tb-name">姓名:</label>
  <input type="text" id="tb-name" placeholder="请输入姓名">

  <label for="tb-pass">密码:</label>
  <input type="password" id="tb-pass">
</section>

<!-- Checkboxes & Radios -->
<section>
  <h2>Toggles</h2>
  <label><input type="checkbox" id="cb-agree" checked> 同意协议</label>
  <label><input type="checkbox" id="cb-news" disabled> 订阅消息 (disabled)</label>
  <label><input type="radio" name="size" id="rb-s" value="s" checked> 小</label>
  <label><input type="radio" name="size" id="rb-m" value="m"> 中</label>
</section>

<!-- Select -->
<section>
  <h2>Dropdown</h2>
  <label for="sel-country">国家:</label>
  <select id="sel-country">
    <option value="">请选择...</option>
    <option value="cn">中国</option>
    <option value="us">美国</option>
    <option value="jp">日本</option>
  </select>
</section>

<!-- Slider -->
<section>
  <h2>Range</h2>
  <label for="sl-vol">音量:</label>
  <input type="range" id="sl-vol" min="0" max="100" value="50">
</section>

<!-- Table -->
<section>
  <h2>Table</h2>
  <table id="tb-data" border="1">
    <thead><tr><th>Name</th><th>Role</th></tr></thead>
    <tbody>
      <tr><td>Alice</td><td>Engineer</td></tr>
      <tr><td>Bob</td><td>Designer</td></tr>
    </tbody>
  </table>
</section>

<!-- Text content -->
<section>
  <h2>Text Content</h2>
  <p id="p-desc">这是一段描述文字</p>
  <span id="sp-label">Status: <strong>Active</strong></span>
  <div id="div-price">价格: ¥99.00</div>
</section>

<!-- Hidden / invisible elements -->
<section>
  <h2>Invisible Elements (should NOT appear in tree)</h2>
  <button class="hidden" id="btn-hidden">Hidden Button</button>
  <button style="display:none" id="btn-display-none">Display None Button</button>
  <button aria-hidden="true" id="btn-aria-hidden">Aria Hidden Button</button>
  <div class="invisible" id="div-invisible">Invisible text</div>
</section>

<!-- Pure layout wrappers -->
<section>
  <h2>Layout Wrappers (should be denoised)</h2>
  <div id="wrapper-empty"><button id="btn-inside-wrapper">Inside Wrapper</button></div>
  <div id="wrapper-multi">
    <span>Price: ¥10</span>
    <span>Price: ¥10</span>
    <span>Price: ¥10</span>
  </div>
</section>

<!-- Dynamic area -->
<section>
  <h2>Dynamic Elements</h2>
  <div id="dynamic-area"></div>
  <button id="btn-create" onclick="createDynamic()">Create Dynamic Element</button>
  <script>
    function createDynamic() {
      var div = document.getElementById('dynamic-area');
      div.innerHTML = '<button id="btn-dynamic">I am new!</button><input id="tb-dynamic" placeholder="dynamic input">';
    }
  </script>
</section>

<!-- Dialog (hidden initially) -->
<dialog id="my-dialog">
  <h2>Dialog Title</h2>
  <p>这是一个弹窗内容</p>
  <button id="btn-dialog-close" onclick="this.closest('dialog').close()">关闭</button>
</dialog>

<script>
  // 自动focus搜索框
  document.getElementById('tb-search').focus();
</script>
</body>
</html>"""


@pytest.fixture(scope="session")
def event_loop():
    """session级别event loop——pytest-asyncio要求"""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def browser():
    """session级别——所有测试共享一个浏览器进程"""
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)
    yield browser
    await browser.close()
    await pw.stop()


@pytest.fixture
async def fresh_page(browser: Browser):
    """每个测试——独立页面"""
    page = await browser.new_page()
    yield page
    await page.close()


@pytest.fixture(scope="session")
def test_html_file(tmp_path_factory) -> Path:
    """session级别——生成测试HTML并写入临时目录"""
    tmp_dir = tmp_path_factory.mktemp("sub_test_html")
    filepath = tmp_dir / "test_page.html"
    filepath.write_text(TEST_HTML_CONTENT, encoding="utf-8")
    return filepath


@pytest.fixture(scope="session")
def test_html_url(test_html_file: Path) -> str:
    """返回 file:// URL"""
    return f"file://{test_html_file.absolute()}"


# ── pytest markers ──

def pytest_configure(config):
    config.addinivalue_line("markers", "slow: marks tests as slow (E2E with real URLs)")


def pytest_collection_modifyitems(config, items):
    """自动给test_integration.py的测试加slow mark"""
    for item in items:
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.slow)
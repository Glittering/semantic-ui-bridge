# 发布平台 + 标题/内容

## Hacker News (Show HN)

**Title**: Show HN: semantic-ui-bridge — AI agents control your desktop without screenshots or OCR

**Body** (first comment):
Python library that gives LLM agents structured access to macOS apps and web pages through the Accessibility API that's been built into the OS since 2012.

```python
from semantic_ui_bridge import SUB
SUB.get_tree("Notes")  # → 285 UI elements, 133 labeled
SUB.safari_go("https://news.sina.com.cn/")  # one-shot navigate
SUB.get_web_content("https://news.sina.com.cn/")  # → 606 links extracted
```

79 tests pass. Zero screenshots, zero OCR, zero coordinate guessing.
Windows/Linux adapters not yet built (UIA/AT-SPI are compatible).
https://github.com/Glittering/semantic-ui-bridge

---

## Twitter / Bluesky
**Tweet**: semantic-ui-bridge v0.1.0 — AI agents read your desktop UI tree through macOS Accessibility API. No screenshots. No OCR. No pixel coordinates. 79 tests pass. github.com/Glittering/semantic-ui-bridge

**Hashtags**: #AI #agent #OpenSource #macOS #python #accessibility

---

## V2EX (中文创造节点)
**标题**: 我做了一个 Python 库——AI agent 不需要截图和 OCR 就能看懂你的电脑界面

**内容**: 用 ANNOUNCEMENT_CN.md 全文

---

## Reddit (r/programming + r/artificial + r/Python)
**Title**: I built a Python library that lets AI agents read your desktop UI tree — 0 screenshots, 0 OCR, 0 coordinate guessing

**Body**: use ANNOUNCEMENT_EN.md
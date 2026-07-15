## AI agents shouldn't need screenshots.

They shouldn't need OCR.
They shouldn't need to guess pixel coordinates.

They should read the operating system's built-in UI tree — which has been there since 2012, waiting for someone to wrap it for LLMs.

---

### semantic-ui-bridge

A Python library that gives AI agents structured access to desktop apps and web pages. Zero screenshots. Zero OCR. Zero coordinate simulation.

```python
from semantic_ui_bridge import SUB

# Read desktop app UI tree — no screenshot
tree = SUB.get_tree("Notes")
# → window="iCloud – 52 notes", 285 elements, 133 labeled

# Safari one-shot navigation
SUB.safari_go("https://news.sina.com.cn/")

# Web content extraction — 606 links in one call
news = SUB.get_web_content("https://news.sina.com.cn/")

# Filesystem browsing
SUB.ls("~/Documents/projects/", pattern=".py")

# Menu operations
SUB.menu_action("Safari", ["File", "New Window"])
```

### How it works

macOS, Windows, and Linux all ship with Accessibility APIs (AX, UI Automation, AT-SPI) that expose every UI element as a structured tree — role, label, value, children, position. These APIs have existed for over a decade. They power screen readers for blind users.

semantic-ui-bridge wraps them for AI agents:

- **macOS AX Adapter** → `pyobjc` → `AXUIElementCreateApplication` → recursive tree traversal → normalized UIRole mapping
- **Playwright Adapter** → Chromium headless → DOM evaluation → text extraction

One unified entry point: `SUB` — pass "Safari" and it uses AX. Pass "http://..." and it uses Playwright.

### Verified (2026-07-15)

| Scenario | Status | Data |
|----------|--------|------|
| macOS Notes UI tree | ✅ | 285 elements, 133 labeled |
| Finder UI tree | ✅ | 283 elements, 149 labeled |
| Safari navigate | ✅ | Xinhuanet/Sina confirmed |
| Web content extraction | ✅ | 606 Sina links, 348 Xinhuanet links |
| Menu operations | ✅ | "File → New Window" works |
| Test suite | ✅ | 79 passed, 0 failed |

### What it can't do (honest)

- **Games** — Metal/OpenGL custom rendering doesn't expose AX
- **Photoshop/Figma canvases** — custom paint surfaces aren't in the AX tree
- **Windows/Linux** — not yet adapted (UIA and AT-SPI are architecturally compatible, needs adapters)
- **Precise drag-and-drop** — not implemented yet

### Why not an "AI browser"?

The repo also explores two more radical ideas (Chromium-based dual-output renderer + system-level render pipeline plugin) in `docs/WHITEPAPER.md`. The chosen path is simpler: wrap existing OS accessibility infrastructure. Lowest cost, highest stability, widest compatibility.

### Install

```bash
pip install semantic-ui-bridge[macos]
playwright install chromium
```

macOS requires one-time permission: System Settings → Privacy & Security → Accessibility.

### Repo

https://github.com/Glittering/semantic-ui-bridge

MIT License. Issues, PRs, experiments welcome.
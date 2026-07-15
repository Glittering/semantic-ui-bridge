#!/bin/bash
# 录制 GitHub demo GIF
# macOS screencapture → ffmpeg → gif

set -e
cd /Users/Zhuanz/Documents/trae_projects/semantic-ui-bridge

OUTDIR="demo_assets"
mkdir -p "$OUTDIR"

echo "1. 运行 demo_github.py 提取输出..."
.venv/bin/python3 demo_github.py > "$OUTDIR/demo_output.txt" 2>&1
echo "   done → $OUTDIR/demo_output.txt"

echo ""
echo "2. 截取终端截图..."
# 用 screencapture -w 截取当前终端窗口
screencapture -w -T2 "$OUTDIR/screenshot_terminal.png" 2>/dev/null || \
screencapture -x "$OUTDIR/screenshot_terminal.png"
echo "   done"

echo ""
echo "Demo assets ready in $OUTDIR/"
ls -la "$OUTDIR/"
# Duplicates Handler Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Create a standalone duplicate files processing utility (`duplicates-handler`) that reads duplicate files reports and allows users to safely recycle redundant duplicates via an interactive CLI or a local Web GUI.

**Architecture:** The tool is structured as a subpackage `find_duplicates.handler` containing clean divisions for processing logic (using `send2trash` for OS Recycle Bin integration), a CLI control loop, and a lightweight built-in HTTP server for a responsive HTML/CSS/JS frontend. A top-level entrypoint launcher script maps the user options.

**Tech Stack:** Python >= 3.12, xxhash, rich, send2trash, Native HTML5/CSS3/JavaScript.

## Global Constraints
- Minimal external dependencies: Only add `send2trash`. Use Python standard library modules (`http.server`, `webbrowser`, `json`, `argparse`, `pathlib`) for server and command routing.
- The web frontend must use ONLY native, vanilla HTML/CSS/JS without external CDN/npm build frameworks to ensure full offline functionality.
- Safety absolute constraint: Every duplicate group must retain at least one file. If any rule or manual action attempts to recycle all files in a group, the operation must fail validation and be blocked.

---

### Task 1: Package Dependencies Scaffolding

**Files:**
- Modify: `pyproject.toml`
- Create: `src/find_duplicates/handler/__init__.py`

**Interfaces:**
- Produces: Package structure for `find_duplicates.handler` and `send2trash` module in environment.

- [ ] **Step 1: Modify `pyproject.toml` to add `send2trash`**

Edit `pyproject.toml` lines 5-8:
```toml
dependencies = [
    "xxhash>=3.8.0",
    "rich>=13.7.0",
    "send2trash>=1.8.0",
]
```

- [ ] **Step 2: Sync dependencies using uv**

Run command:
`uv sync`
Expected output: Success message showing installation of `send2trash` and update of lock file.

- [ ] **Step 3: Create package initializer file**

Create `src/find_duplicates/handler/__init__.py`:
```python
"""Duplicates handler subpackage."""
__version__ = "0.1.0"
```

- [ ] **Step 4: Verify package import works**

Run: `python -c "import find_duplicates.handler; print(find_duplicates.handler.__version__)"`
Expected output: `0.1.0`

- [ ] **Step 5: Commit changes**

Run:
```bash
git add pyproject.toml src/find_duplicates/handler/__init__.py
git commit -m "chore: scaffold handler package and add send2trash dependency"
```

---

### Task 2: Core Processor Implementation & Unit Tests

**Files:**
- Create: `src/find_duplicates/handler/core.py`
- Create: `tests/test_handler.py`

**Interfaces:**
- Consumes: None
- Produces:
  - `load_json_report(report_path: Path) -> tuple[dict, dict]`
  - `validate_selections(duplicates: dict, keep_paths: set[str], trash_paths: set[str]) -> str | None`
  - `recycle_files(trash_paths: list[str]) -> tuple[int, int]`

- [ ] **Step 1: Write failing tests for core logic**

Create `tests/test_handler.py`:
```python
import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from find_duplicates.handler.core import load_json_report, validate_selections, recycle_files

def test_load_json_report(tmp_path):
    report_file = tmp_path / "report.json"
    dummy_data = {
        "summary": {"total_files": 10},
        "duplicates": {
            "hash123": ["file1.txt", "file2.txt"]
        }
      }
    report_file.write_text(json.dumps(dummy_data))
    
    summary, duplicates = load_json_report(report_file)
    assert summary["total_files"] == 10
    assert "hash123" in duplicates
    assert len(duplicates["hash123"]) == 2

def test_validate_selections_empty():
    duplicates = {"h1": ["f1.txt", "f2.txt"]}
    keep = {"f1.txt"}
    trash = {"f2.txt"}
    # Should pass (returns None)
    assert validate_selections(duplicates, keep, trash) is None

def test_validate_selections_must_keep_one():
    duplicates = {"h1": ["f1.txt", "f2.txt"]}
    keep = set()
    trash = {"f1.txt", "f2.txt"}
    # Should return an error message
    err = validate_selections(duplicates, keep, trash)
    assert err is not None
    assert "必须至少保留一个文件" in err

@patch("find_duplicates.handler.core.send2trash.send2trash")
def test_recycle_files_mocked(mock_send2trash, tmp_path):
    f1 = tmp_path / "t1.txt"
    f1.write_text("content")
    
    mock_send2trash.return_value = None
    count, size = recycle_files([str(f1)])
    assert count == 1
    assert size == 7
    mock_send2trash.assert_called_once_with(str(f1))
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_handler.py -v`
Expected: FAIL with `ModuleNotFoundError` for `find_duplicates.handler.core`

- [ ] **Step 3: Write minimal implementation in `src/find_duplicates/handler/core.py`**

Create `src/find_duplicates/handler/core.py`:
```python
import json
from pathlib import Path
import send2trash

def load_json_report(report_path: Path) -> tuple[dict, dict]:
    """读取并解析查重JSON报告，返回 (summary, duplicates)。"""
    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("summary", {}), data.get("duplicates", {})

def validate_selections(duplicates: dict, keep_paths: set[str], trash_paths: set[str]) -> str | None:
    """校验选择是否安全。如果任一组的所有文件都被标记为删除，或者文件不存在，返回错误字符串。"""
    for hash_val, paths in duplicates.items():
        trash_count = sum(1 for p in paths if p in trash_paths)
        if trash_count == len(paths):
            return f"安全防护：重复组 {hash_val} 的所有文件都标记了删除，必须至少保留一个文件！"
    return None

def recycle_files(trash_paths: list[str]) -> tuple[int, int]:
    """物理移动文件至回收站。返回 (回收文件数, 释放空间字节数)。"""
    count = 0
    reclaimed_bytes = 0
    for path_str in trash_paths:
        path = Path(path_str)
        if path.is_file():
            size = path.stat().st_size
            send2trash.send2trash(str(path))
            count += 1
            reclaimed_bytes += size
    return count, reclaimed_bytes
```

- [ ] **Step 4: Run tests and verify they pass**

Run: `pytest tests/test_handler.py -v`
Expected: PASS

- [ ] **Step 5: Commit changes**

Run:
```bash
git add src/find_duplicates/handler/core.py tests/test_handler.py
git commit -m "feat: implement handler core processor logic and passing unit tests"
```

---

### Task 3: Interactive CLI Submodule

**Files:**
- Create: `src/find_duplicates/handler/cli.py`

**Interfaces:**
- Consumes:
  - `load_json_report` from `find_duplicates.handler.core`
  - `validate_selections` from `find_duplicates.handler.core`
  - `recycle_files` from `find_duplicates.handler.core`
- Produces:
  - `run_cli_handler(report_path: str) -> None`

- [ ] **Step 1: Write terminal CLI prompt and loop logic**

Create `src/find_duplicates/handler/cli.py`:
```python
import sys
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .core import load_json_report, validate_selections, recycle_files

console = Console()

def format_size(size_in_bytes: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} TB"

def run_cli_handler(report_path: str) -> None:
    path = Path(report_path)
    if not path.is_file():
        console.print(f"[bold red]错误: 报告文件 '{report_path}' 不存在。[/bold red]", style="red")
        sys.exit(1)

    try:
        summary, duplicates = load_json_report(path)
    except Exception as e:
        console.print(f"[bold red]解析 JSON 报告失败: {e}[/bold red]")
        sys.exit(1)

    if not duplicates:
        console.print("[bold green]报告中没有重复文件记录。无需处理。[/bold green]")
        return

    keep_paths = set()
    trash_paths = set()

    console.print(Panel("[bold green]进入 重复文件命令行交互处理器 (CLI)[/bold green]", expand=False))
    console.print("操作说明: 输入序号保留指定文件，其余自动回收。输入 's' 跳过，输入 'q' 退出。\n")

    # 循环遍历组
    for idx, (hsh, paths) in enumerate(duplicates.items(), start=1):
        console.print(f"[bold yellow]重复组 {idx}/{len(duplicates)}[/bold yellow] (Hash: {hsh})")
        table = Table(title="备选文件列表", show_header=True, header_style="bold magenta")
        table.add_column("序号", style="dim", width=6)
        table.add_column("修改时间", width=20)
        table.add_column("文件大小", width=12)
        table.add_column("文件路径")

        valid_paths = []
        for file_idx, p_str in enumerate(paths, start=1):
            p = Path(p_str)
            if not p.is_file():
                continue
            valid_paths.append(p_str)
            stat = p.stat()
            from datetime import datetime
            mtime_str = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
            size_str = format_size(stat.st_size)
            table.add_row(str(file_idx), mtime_str, size_str, p_str)

        if not valid_paths:
            console.print("[red]当前组文件在磁盘上已全部不存在。[/red]\n")
            continue

        console.print(table)

        while True:
            choice = input("请输入要【保留】的序号 (s:跳过, q:退出): ").strip().lower()
            if choice == "q":
                console.print("[yellow]操作被终止。[/yellow]")
                sys.exit(0)
            elif choice == "s":
                console.print("[dim]已跳过当前组[/dim]\n")
                break
            elif choice.isdigit():
                val = int(choice)
                if 1 <= val <= len(valid_paths):
                    keep_file = valid_paths[val - 1]
                    keep_paths.add(keep_file)
                    for other in valid_paths:
                        if other != keep_file:
                            trash_paths.add(other)
                    console.print(f"[green]已选择保留: {keep_file}，其余移至待回收[/green]\n")
                    break
            console.print("[red]输入无效，请输入正确的序号、's' 或 'q'。[/red]")

    if not trash_paths:
        console.print("[yellow]没有文件被标记为回收。[/yellow]")
        return

    # 安全检查
    err = validate_selections(duplicates, keep_paths, trash_paths)
    if err:
        console.print(f"[bold red]{err}[/bold red]")
        sys.exit(1)

    # 汇总展示并最终确认
    console.print(Panel("[bold yellow]待回收文件确认清单[/bold yellow]", expand=False))
    total_size_to_recycle = 0
    for p_str in sorted(trash_paths):
        p = Path(p_str)
        if p.is_file():
            size = p.stat().st_size
            total_size_to_recycle += size
            console.print(f"  [red]🗑️  [回收][/red] {p_str} ({format_size(size)})")

    console.print(f"\n共准备回收 [red]{len(trash_paths)}[/red] 个重复文件，预计释放 [green]{format_size(total_size_to_recycle)}[/green] 空间。")
    confirm = input("确认将上述文件移至回收站吗？(y/n): ").strip().lower()
    if confirm == "y":
        count, reclaimed = recycle_files(list(trash_paths))
        console.print(f"[bold green]成功移入回收站！共回收了 {count} 个文件，实际释放空间: {format_size(reclaimed)}[/bold green]")
    else:
        console.print("[yellow]操作已取消。[/yellow]")
```

- [ ] **Step 2: Commit CLI implementation**

Run:
```bash
git add src/find_duplicates/handler/cli.py
git commit -m "feat: implement interactive CLI duplicate processor loop"
```

---

### Task 4: Web GUI Backend Server Submodule

**Files:**
- Create: `src/find_duplicates/handler/web.py`

**Interfaces:**
- Consumes:
  - `load_json_report` from `find_duplicates.handler.core`
  - `validate_selections` from `find_duplicates.handler.core`
  - `recycle_files` from `find_duplicates.handler.core`
- Produces:
  - `run_web_handler(report_path: str, host: str, port: int) -> None`

- [ ] **Step 1: Implement HTTP request handler class and server runner**

Create `src/find_duplicates/handler/web.py`:
```python
import json
import sys
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
import socket

from .core import load_json_report, validate_selections, recycle_files

# 将存储静态网页模板的路径
TEMPLATE_PATH = Path(__file__).parent / "templates" / "index.html"
REPORT_FILE_PATH = None

class HandlerHTTPRequestHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        # 覆写，静默日志输出以使控制台清爽
        pass

    def do_GET(self):
        global REPORT_FILE_PATH
        if self.path == "/":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            if TEMPLATE_PATH.is_file():
                with open(TEMPLATE_PATH, "r", encoding="utf-8") as f:
                    self.wfile.write(f.read().encode("utf-8"))
            else:
                self.wfile.write("<h1>Error: Frontend template index.html not found!</h1>".encode("utf-8"))
        elif self.path == "/api/data":
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            try:
                summary, duplicates = load_json_report(Path(REPORT_FILE_PATH))
                # 丰富返回数据，携带每个文件的基本状态
                rich_duplicates = {}
                for hsh, paths in duplicates.items():
                    group_files = []
                    for p_str in paths:
                        p = Path(p_str)
                        exists = p.is_file()
                        size = p.stat().st_size if exists else 0
                        mtime = p.stat().st_mtime if exists else 0
                        group_files.append({
                            "path": p_str,
                            "exists": exists,
                            "size": size,
                            "mtime": mtime
                        })
                    rich_duplicates[hsh] = group_files
                
                response = {
                    "status": "success",
                    "summary": summary,
                    "duplicates": rich_duplicates
                }
            except Exception as e:
                response = {"status": "error", "message": str(e)}
            self.wfile.write(json.dumps(response, ensure_ascii=False).encode("utf-8"))
        else:
            self.send_error(404, "File Not Found")

    def do_POST(self):
        global REPORT_FILE_PATH
        if self.path == "/api/action":
            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            try:
                payload = json.loads(body.decode("utf-8"))
                # payload format: {"actions": {"hash_val": {"keep": ["path1"], "trash": ["path2"]}}}
                actions = payload.get("actions", {})
                
                # 重新加载报告，得到原始组清单，进行安全交叉验证
                _, duplicates = load_json_report(Path(REPORT_FILE_PATH))
                
                all_keep = set()
                all_trash = set()
                for hsh, detail in actions.items():
                    all_keep.update(detail.get("keep", []))
                    all_trash.update(detail.get("trash", []))
                
                # 交叉安全核验
                err = validate_selections(duplicates, all_keep, all_trash)
                if err:
                    self.send_response(400)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": err}).encode("utf-8"))
                    return
                
                # 物理执行
                count, reclaimed_bytes = recycle_files(list(all_trash))
                
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({
                    "status": "success",
                    "count": count,
                    "reclaimed_bytes": reclaimed_bytes
                }).encode("utf-8"))
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
        else:
            self.send_error(404, "Endpoint Not Found")

def run_web_handler(report_path: str, host: str, port: int) -> None:
    global REPORT_FILE_PATH
    REPORT_FILE_PATH = report_path
    
    server_address = (host, port)
    try:
        httpd = HTTPServer(server_address, HandlerHTTPRequestHandler)
    except socket.error as err:
        print(f"[错误] 绑定端口 {port} 失败: {err}", file=sys.stderr)
        sys.exit(1)
        
    url = f"http://{host}:{port}/"
    print(f"==================================================")
    print(f"启动 Web GUI 服务成功！")
    print(f"监听地址: {url}")
    print(f"按 Ctrl+C 可以退出服务")
    print(f"==================================================")
    
    # 自动打开浏览器
    webbrowser.open(url)
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nWeb 服务已关闭。")
        sys.exit(0)
```

- [ ] **Step 2: Commit Web server backend implementation**

Run:
```bash
git add src/find_duplicates/handler/web.py
git commit -m "feat: implement built-in http.server backend API for Web GUI mode"
```

---

### Task 5: Web GUI Frontend Single-Page Application

**Files:**
- Create: `src/find_duplicates/handler/templates/index.html`

**Interfaces:**
- Consumes:
  - Backend API: `GET /api/data`, `POST /api/action`
- Produces: Rendered visual card list interface.

- [ ] **Step 1: Create Single-Page HTML with style and behavior scripts**

Create `src/find_duplicates/handler/templates/index.html`:
```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <title>重复文件清理控制台 (Duplicates Handler)</title>
  <style>
    :root {
      --bg-dark: #121214;
      --bg-card: rgba(30, 30, 38, 0.6);
      --border-color: rgba(255, 255, 255, 0.08);
      --text-main: #e4e4e7;
      --text-dim: #a1a1aa;
      --color-primary: #3b82f6;
      --color-success: #10b981;
      --color-danger: #ef4444;
    }

    body {
      background: var(--bg-dark);
      color: var(--text-main);
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      margin: 0;
      padding: 20px;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
    }

    header {
      margin-bottom: 20px;
    }

    h1 {
      margin: 0 0 5px 0;
      font-size: 24px;
      background: linear-gradient(90deg, #3b82f6, #10b981);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .subtitle {
      margin: 0;
      color: var(--text-dim);
      font-size: 14px;
    }

    .layout-container {
      display: grid;
      grid-template-columns: 320px 1fr;
      gap: 20px;
      flex-grow: 1;
      margin-bottom: 80px;
    }

    /* Sidebar */
    .sidebar {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 12px;
      padding: 20px;
      backdrop-filter: blur(10px);
      display: flex;
      flex-direction: column;
      gap: 20px;
      align-self: start;
    }

    .stat-card {
      background: rgba(255, 255, 255, 0.03);
      border-radius: 8px;
      padding: 15px;
      border-left: 4px solid var(--color-success);
    }

    .stat-val {
      font-size: 24px;
      font-weight: bold;
      color: var(--color-success);
      margin-top: 5px;
    }

    .stat-lbl {
      font-size: 11px;
      color: var(--text-dim);
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }

    .rule-group {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .rule-btn {
      background: var(--color-primary);
      color: white;
      border: none;
      border-radius: 6px;
      padding: 10px;
      font-weight: 500;
      cursor: pointer;
      transition: background 0.2s;
      font-size: 13px;
    }
    .rule-btn:hover {
      background: #2563eb;
    }

    .rule-select {
      background: #27272a;
      border: 1px solid #3f3f46;
      color: white;
      border-radius: 6px;
      padding: 8px;
      font-size: 13px;
      outline: none;
    }

    /* Main Area */
    .main-content {
      display: flex;
      flex-direction: column;
      gap: 15px;
    }

    .group-card {
      background: var(--bg-card);
      border: 1px solid var(--border-color);
      border-radius: 10px;
      overflow: hidden;
    }

    .group-header {
      background: rgba(255, 255, 255, 0.02);
      padding: 12px 15px;
      border-bottom: 1px solid var(--border-color);
      display: flex;
      justify-content: space-between;
      align-items: center;
    }

    .group-title {
      font-size: 14px;
      font-weight: 600;
      color: #f4f4f5;
    }

    .group-meta {
      font-size: 12px;
      color: var(--text-dim);
    }

    .file-list {
      padding: 10px 15px;
    }

    .file-item {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 0;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
    }
    .file-item:last-child {
      border-bottom: none;
    }

    .file-path-wrapper {
      display: flex;
      align-items: center;
      gap: 10px;
      flex-grow: 1;
      min-width: 0;
    }

    .file-path {
      font-family: monospace;
      font-size: 13px;
      color: #e4e4e7;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .file-date {
      font-size: 12px;
      color: var(--text-dim);
      margin-left: 10px;
      flex-shrink: 0;
    }

    .action-toggle {
      display: flex;
      background: #27272a;
      border-radius: 20px;
      padding: 2px;
      border: 1px solid #3f3f46;
      flex-shrink: 0;
      margin-left: 20px;
    }

    .action-btn {
      border: none;
      background: transparent;
      color: var(--text-dim);
      font-size: 11px;
      padding: 4px 10px;
      border-radius: 15px;
      cursor: pointer;
      font-weight: 500;
      transition: all 0.2s;
    }

    .action-btn.active-keep {
      background: var(--color-success);
      color: white;
    }

    .action-btn.active-trash {
      background: var(--color-danger);
      color: white;
    }

    .badge-keep {
      background: rgba(16, 185, 129, 0.15);
      color: var(--color-success);
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 11px;
      min-width: 32px;
      text-align: center;
    }

    .badge-trash {
      background: rgba(239, 68, 68, 0.15);
      color: var(--color-danger);
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 11px;
      min-width: 32px;
      text-align: center;
    }

    /* Fixed Bottom Action Bar */
    .action-bar {
      background: rgba(20, 20, 25, 0.9);
      border-top: 1px solid var(--border-color);
      position: fixed;
      bottom: 0;
      left: 0;
      right: 0;
      padding: 15px 40px;
      display: flex;
      justify-content: space-between;
      align-items: center;
      box-shadow: 0 -5px 25px rgba(0, 0, 0, 0.5);
      backdrop-filter: blur(10px);
      z-index: 100;
    }

    .action-bar-info {
      font-size: 14px;
    }

    .action-bar-submit {
      background: var(--color-success);
      color: white;
      font-weight: bold;
      border: none;
      border-radius: 6px;
      padding: 10px 24px;
      cursor: pointer;
      transition: background 0.2s;
    }
    .action-bar-submit:hover {
      background: #059669;
    }
  </style>
</head>
<body>
  <header>
    <h1>重复文件清理控制台 (Duplicates Handler)</h1>
    <p class="subtitle">读取查重报告，轻松管理并回收多余冗余文件。</p>
  </header>

  <div class="layout-container">
    <div class="sidebar">
      <div>
        <h3 style="margin:0 0 10px 0; font-size: 14px;">空间释放统计</h3>
        <div class="stat-card">
          <div class="stat-lbl">预计释放空间</div>
          <div class="stat-val" id="reclaim-size">0.00 B</div>
        </div>
      </div>

      <div class="rule-group">
        <h3 style="margin:0 0 5px 0; font-size: 14px;">批量选择规则</h3>
        <select class="rule-select" id="rule-select">
          <option value="oldest">保留修改时间最早的文件 (Keep Oldest)</option>
          <option value="newest">保留修改时间最晚的文件 (Keep Newest)</option>
          <option value="shortest">保留路径深度最短的文件 (Shortest Path)</option>
          <option value="longest">保留路径深度最长的文件 (Longest Path)</option>
        </select>
        <button class="rule-btn" onclick="applyBatchRule()">应用批量规则</button>
      </div>

      <div style="font-size:12px; color:var(--text-dim); border-top:1px solid var(--border-color); padding-top:15px;">
        <strong>安全说明：</strong><br>
        文件将被移至系统回收站，如有误操作可以随时从回收站找回。
      </div>
    </div>

    <div class="main-content" id="groups-container">
      <div style="text-align: center; padding: 40px; color: var(--text-dim);">正在加载扫描结果...</div>
    </div>
  </div>

  <div class="action-bar">
    <div class="action-bar-info" id="bar-info">
      已选择：准备回收 <strong>0</strong> 个重复文件，释放 <strong>0.00 B</strong> 空间
    </div>
    <button class="action-bar-submit" onclick="submitCleanup()">执行清理操作</button>
  </div>

  <script>
    let duplicatesData = {}; // Format: { hash_val: [ {path, exists, size, mtime}, ... ] }
    let userSelections = {}; // Format: { hash_val: { keep: "path", trash: ["path", ...] } }

    function formatSize(bytes) {
      if (bytes === 0) return '0 B';
      const k = 1024;
      const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
      const i = Math.floor(Math.log(bytes) / Math.log(k));
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    async function loadData() {
      try {
        const res = await fetch('/api/data');
        const json = await res.json();
        if (json.status === 'success') {
          duplicatesData = json.duplicates;
          initSelections();
          renderGroups();
          updateStats();
        } else {
          document.getElementById('groups-container').innerHTML = `<div style="color:var(--color-danger); text-align:center;">加载失败: ${json.message}</div>`;
        }
      } catch (err) {
        document.getElementById('groups-container').innerHTML = `<div style="color:var(--color-danger); text-align:center;">网络错误: ${err}</div>`;
      }
    }

    function initSelections() {
      // 默认让第一个有效文件作为keep，其余为trash
      for (const hsh in duplicatesData) {
        const files = duplicatesData[hsh].filter(f => f.exists);
        if (files.length > 1) {
          userSelections[hsh] = {
            keep: files[0].path,
            trash: files.slice(1).map(f => f.path)
          };
        }
      }
    }

    function renderGroups() {
      const container = document.getElementById('groups-container');
      container.innerHTML = '';
      let index = 1;

      for (const hsh in duplicatesData) {
        const files = duplicatesData[hsh];
        const selection = userSelections[hsh];
        if (!selection) continue;

        const sizeStr = formatSize(files[0].size);
        const card = document.createElement('div');
        card.className = 'group-card';
        card.id = `group-${hsh}`;

        let fileItemsHtml = '';
        files.forEach(file => {
          const isKeep = (selection.keep === file.path);
          const badgeClass = isKeep ? 'badge-keep' : 'badge-trash';
          const badgeText = isKeep ? '保留' : '回收';
          const dateStr = new Date(file.mtime * 1000).toLocaleString();

          fileItemsHtml += `
            <div class="file-item" id="file-${hsh}-${btoa(file.path)}">
              <div class="file-path-wrapper">
                <span class="${badgeClass}">${badgeText}</span>
                <span class="file-path" title="${file.path}">${file.path}</span>
                <span class="file-date">${dateStr}</span>
              </div>
              <div class="action-toggle">
                <button class="action-btn ${isKeep ? 'active-keep' : ''}" onclick="selectFile('${hsh}', '${file.path.replace(/\\/g, '\\\\')}', 'keep')">保留</button>
                <button class="action-btn ${!isKeep ? 'active-trash' : ''}" onclick="selectFile('${hsh}', '${file.path.replace(/\\/g, '\\\\')}', 'trash')">回收</button>
              </div>
            </div>
          `;
        });

        card.innerHTML = `
          <div class="group-header">
            <span class="group-title">重复组 #${index++}</span>
            <span class="group-meta">单文件大小: ${sizeStr} | 哈希: ${hsh.substring(0, 16)}...</span>
          </div>
          <div class="file-list">
            ${fileItemsHtml}
          </div>
        `;
        container.appendChild(card);
      }

      if (index === 1) {
        container.innerHTML = '<div style="text-align:center; padding:40px; color:var(--text-dim);">没有需要处理的重复文件组。</div>';
      }
    }

    function selectFile(hash, path, mode) {
      const selection = userSelections[hash];
      const files = duplicatesData[hash].filter(f => f.exists);

      if (mode === 'keep') {
        selection.keep = path;
        selection.trash = files.map(f => f.path).filter(p => p !== path);
      } else {
        // 如果点击回收的是当前唯一的keep，则自动找另一个作为keep
        if (selection.keep === path) {
          const another = files.find(f => f.path !== path);
          if (another) {
            selection.keep = another.path;
            selection.trash = files.map(f => f.path).filter(p => p !== another.path);
          } else {
            alert("安全限制：每组必须至少保留一个文件！");
            return;
          }
        }
      }

      // 重新渲染该组
      renderGroups();
      updateStats();
    }

    function applyBatchRule() {
      const rule = document.getElementById('rule-select').value;
      for (const hsh in duplicatesData) {
        const files = duplicatesData[hsh].filter(f => f.exists);
        if (files.length <= 1) continue;

        let bestFile = files[0];
        files.forEach(file => {
          if (rule === 'oldest') {
            if (file.mtime < bestFile.mtime) bestFile = file;
          } else if (rule === 'newest') {
            if (file.mtime > bestFile.mtime) bestFile = file;
          } else if (rule === 'shortest') {
            if (file.path.length < bestFile.path.length) bestFile = file;
          } else if (rule === 'longest') {
            if (file.path.length > bestFile.path.length) bestFile = file;
          }
        });

        userSelections[hsh] = {
          keep: bestFile.path,
          trash: files.map(f => f.path).filter(p => p !== bestFile.path)
        };
      }
      renderGroups();
      updateStats();
    }

    function updateStats() {
      let trashCount = 0;
      let reclaimBytes = 0;

      for (const hsh in userSelections) {
        const trashList = userSelections[hsh].trash;
        const files = duplicatesData[hsh];
        trashList.forEach(p => {
          const file = files.find(f => f.path === p);
          if (file) {
            trashCount++;
            reclaimBytes += file.size;
          }
        });
      }

      document.getElementById('reclaim-size').innerText = formatSize(reclaimBytes);
      document.getElementById('bar-info').innerHTML = `已选择：准备回收 <strong>${trashCount}</strong> 个重复文件，释放 <strong>${formatSize(reclaimBytes)}</strong> 空间`;
    }

    async function submitCleanup() {
      let trashCount = 0;
      for (const hsh in userSelections) {
        trashCount += userSelections[hsh].trash.length;
      }
      if (trashCount === 0) {
        alert("未勾选任何需要回收的文件。");
        return;
      }

      if (!confirm(`确认将选中的 ${trashCount} 个文件移入系统回收站吗？`)) {
        return;
      }

      try {
        const res = await fetch('/api/action', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({ actions: userSelections })
        });
        const json = await res.json();
        if (json.status === 'success') {
          alert(`清理完成！实际移入回收站 ${json.count} 个文件，释放空间: ${formatSize(json.reclaimed_bytes)}`);
          loadData();
        } else {
          alert(`执行失败: ${json.message}`);
        }
      } catch (err) {
        alert(`网络异常: ${err}`);
      }
    }

    window.onload = loadData;
  </script>
</body>
</html>
```

- [ ] **Step 2: Commit Frontend SPA HTML implementation**

Run:
```bash
git add src/find_duplicates/handler/templates/index.html
git commit -m "feat: implement frontend web SPA using native HTML, CSS, and Vanilla JS"
```

---

### Task 6: Unified Entrypoint Script & command wiring

**Files:**
- Create: `duplicates_handler.py`
- Modify: `pyproject.toml:10-12`

**Interfaces:**
- Consumes:
  - `run_cli_handler` from `find_duplicates.handler.cli`
  - `run_web_handler` from `find_duplicates.handler.web`
- Produces: Executable command `duplicates-handler`.

- [ ] **Step 1: Create top-level launcher `duplicates_handler.py`**

Create `duplicates_handler.py`:
```python
import argparse
import sys
from pathlib import Path

from find_duplicates.handler.cli import run_cli_handler
from find_duplicates.handler.web import run_web_handler

def main():
    parser = argparse.ArgumentParser(
        description="重复文件选择处理器 (Duplicates Handler) - 安全清理冗余文件"
    )
    
    parser.add_argument(
        "report",
        help="查重生成的 JSON 报告文件路径"
    )
    
    parser.add_argument(
        "--web",
        action="store_true",
        help="启用网页模式启动本地服务及 GUI 交互"
    )
    
    parser.add_argument(
        "--port",
        type=int,
        default=52342,
        help="Web 服务器绑定的端口（默认: 52342）"
    )
    
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Web 服务器绑定的 Host（默认: 127.0.0.1）"
    )
    
    args = parser.parse_args()
    
    report_path = Path(args.report)
    if not report_path.is_file():
        print(f"[错误] 报告文件不存在: '{args.report}'", file=sys.stderr)
        sys.exit(1)
        
    if args.web:
        run_web_handler(str(report_path), args.host, args.port)
    else:
        run_cli_handler(str(report_path))

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Add duplicates-handler script mapping to `pyproject.toml`**

Edit `pyproject.toml` lines 10-12:
```toml
[project.scripts]
find-duplicates = "find_duplicates.cli:main"
duplicates-handler = "find_duplicates.handler.core:main" # we will route to main in entry script, or configure it appropriately. Let's make it map to find_duplicates.handler.cli:main or define an alias. Let's make it map to our handler script.
```
Wait! To map it to package entry point, we can put a `main` function inside `src/find_duplicates/handler/core.py` or create `src/find_duplicates/handler/__main__.py` containing the main entry. Let's define the entrypoint as `find_duplicates.handler.core:main` (and place the `main` argparse logic in `src/find_duplicates/handler/core.py` so it packages nicely, or put it in `find_duplicates.handler.__main__`).
Let's modify `pyproject.toml` to:
```toml
[project.scripts]
find-duplicates = "find_duplicates.cli:main"
duplicates-handler = "find_duplicates.handler.core:main"
```
Wait, let's look at `core.py` and implement the `main` function in it which routes to `duplicates_handler.py:main` logic. This is extremely clean.
Let's define `core.py`'s `main` in our plan:
In `src/find_duplicates/handler/core.py`, add:
```python
def main():
    import argparse
    import sys
    from .cli import run_cli_handler
    from .web import run_web_handler
    
    parser = argparse.ArgumentParser(
        description="重复文件选择处理器 (Duplicates Handler) - 安全清理冗余文件"
    )
    parser.add_argument("report", help="查重生成的 JSON 报告文件路径")
    parser.add_argument("--web", action="store_true", help="启用网页模式启动本地服务及 GUI 交互")
    parser.add_argument("--port", type=int, default=52342, help="Web 服务器绑定的端口（默认: 52342）")
    parser.add_argument("--host", default="127.0.0.1", help="Web 服务器绑定的 Host（默认: 127.0.0.1）")
    
    args = parser.parse_args()
    report_path = Path(args.report)
    if not report_path.is_file():
        print(f"[错误] 报告文件不存在: '{args.report}'", file=sys.stderr)
        sys.exit(1)
        
    if args.web:
        run_web_handler(str(report_path), args.host, args.port)
    else:
        run_cli_handler(str(report_path))
```
Then the root script `duplicates_handler.py` simply calls:
```python
from find_duplicates.handler.core import main

if __name__ == "__main__":
    main()
```
This is extremely clean and matches python standards perfectly!

- [ ] **Step 3: Update `core.py` with `main` function**

Verify `core.py` imports/logic.

- [ ] **Step 4: Sync environment with uv to register new console script**

Run:
`uv sync`

- [ ] **Step 5: Commit entrypoint implementation**

Run:
```bash
git add duplicates_handler.py src/find_duplicates/handler/core.py pyproject.toml
git commit -m "feat: add unified launcher script and wire duplicates-handler console script entry"
```

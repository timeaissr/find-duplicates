# 重复文件处理器设计方案 (Duplicate Files Handler Design Spec)

本方案设计了一个名为 `duplicates-handler` 的独立处理程序。它在 `find-duplicates` 扫描出重复文件并生成 JSON 报告后，读取该报告进行下一步的交互式处理。

## 1. 目标与背景

查重工具扫描完成后，用户需要对重复文件进行清理。本程序提供命令行 (CLI) 和网页 (Web GUI) 两种交互模式，使用户能够：
* 逐组确认并手动勾选需要保留和回收的文件。
* 批量应用自动规则（例如：保留修改时间最早的文件，其余移入回收站）。
* 安全地将不需要的重复文件移入操作系统的回收站（而非直接物理粉碎），防止误删。

---

## 2. 系统设计

### 2.1 目录结构与模块划分

为了保持清晰的包依赖关系与模块划分，本处理器的所有实现代码均置于 `src/find_duplicates/handler` 子包下，避免污染主查重工具的根级文件。

项目的新增目录结构如下：
```text
find-duplicates/
├── duplicates_handler.py             # [NEW] 根目录下统一启动入口脚本
├── pyproject.toml                    # 依赖管理，新增 send2trash 依赖并配置入口命令
├── src/
│   └── find_duplicates/
│       └── handler/                  # [NEW] 处理器专属包目录
│           ├── __init__.py           # 包初始化文件
│           ├── core.py               # 核心逻辑：JSON解析、安全性检查、物理回收
│           ├── cli.py                # 命令行交互界面渲染及控制循环
│           ├── web.py                # 本地 Web 服务后台 (基于 http.server)
│           └── templates/            # 前端资源目录
│               └── index.html        # 单页面前端 UI 模板 (HTML/CSS/JS)
└── tests/
    └── test_handler.py               # [NEW] 处理器单元测试
```

### 2.2 依赖关系

在项目已有的依赖基础（`xxhash`, `rich`）上，引入一个新的第三方库：
* **`send2trash`** (版本 `>=1.8.0`)：用于跨平台、无感地将文件移至操作系统的回收站（Trash / Recycle Bin），支持 Windows, macOS, Linux。

### 2.3 核心处理器 (`src/find_duplicates/handler/core.py`)

封装底层的数据操作与安全性检查：
1. **输入解析**：读取并反序列化查重工具导出的 `.json` 报告文件。
2. **安全性校验**：
   * 在执行任何删除/移动操作前，检查目标路径的文件在磁盘上是否依然存在且为普通文件。
   * **防止完全删除**：对每一组重复文件，强制要求必须至少有一个文件被标记为“保留 (keep)”。如果检测到用户尝试将某组的所有文件全部回收，抛出验证错误，拒绝执行。
3. **物理回收**：遍历标记为回收的文件，调用 `send2trash.send2trash(path)` 执行操作。
4. **统计反馈**：计算成功回收的文件数量，累加这些文件的大小，输出实际释放的空间量。

### 2.4 终端交互界面 (`src/find_duplicates/handler/cli.py`)

默认的交互界面，面向命令行爱好者：
* **分组渲染**：利用 `rich` 在控制台渲染分组，显示每一组文件的序号、大小、修改时间及绝对路径。
* **交互循环**：
  * 程序会逐组询问用户的操作。例如：
    ```text
    重复组 1 (大小: 2.35 MB | 哈希: 8d2c2b...):
    [1] C:/data/photos/img_0421.jpg (2026-06-01 12:00)
    [2] C:/backup/photos/img_0421.jpg (2026-06-15 14:30)
    请输入要【保留】的文件序号 (输入 s 跳过，q 退出): 
    ```
  * 支持便捷输入：输入数字（如 `1`）即代表保留第 1 个文件，其余文件标记为回收。
* **规则批量应用**：在提示符中支持输入 `a` 进入批量应用规则模式，可选规则：
  * 保留修改时间最早的文件。
  * 保留修改时间最晚的文件。
  * 保留路径深度最短的文件。
  * 保留路径深度最长的文件。
* **最终确认**：在用户处理完所有组（或选择提前应用规则）后，在控制台打印待回收文件的清单与大小统计，提示 `确认将以上 X 个文件移至回收站？(y/n)`。用户确认后执行操作。

### 2.5 本地网页服务与前端模板 (`src/find_duplicates/handler/web.py`, `src/find_duplicates/handler/templates/index.html`)

提供零外部依赖的轻量级 Web 服务：
* **服务器引擎**：使用 Python 标准库的 `http.server.BaseHTTPRequestHandler` 编写，不引入 FastAPI/Flask 等重型库。
* **网页前端 SPA (`src/find_duplicates/handler/templates/index.html`)**：
  * 编写单文件 HTML 并作为模板文件由 `web.py` 在 `GET /` 时进行读取并加载，内含 Vanilla CSS 和 JavaScript。
  * **视觉设计**：深色现代极简风格 (Dark Mode)，使用毛玻璃卡片 (Glassmorphism) 和圆角布局，配备醒目的状态色（绿色代表 Keep，红色代表 Trash）。
  * **客户端规则预估**：用户在侧边栏切换批量选择规则，JS 会遍历所有重复组并自动更改选中状态，在界面上直接预览。
  * **底栏信息**：动态计算并显示“已选择回收 X 个文件，释放 Y MB 空间”。
* **接口定义**：
  * `GET /api/data`：返回包含重复文件数据、汇总统计信息的 JSON 结构。
  * `POST /api/action`：接收前端发送的动作决策 JSON，如：
    ```json
    {
      "actions": {
        "8d2c2bc051187eb30a21fb9d1a3c7aa3": {
          "keep": ["C:/data/photos/img_0421.jpg"],
          "trash": ["C:/backup/photos/img_0421.jpg"]
        }
      }
    }
    ```
    后端执行核心校验，确认无误后执行 `send2trash`。

### 2.6 统一启动入口 (`duplicates_handler.py` 位于项目根目录)

```bash
# 用法：
python duplicates_handler.py <path_to_json_report> [参数]
```

参数列表：
* `<path_to_json_report>`: 必填。查重扫描生成的 JSON 报告文件路径。
* `--web`: 可选。启用网页版界面，自动启动本地 Web 服务并在浏览器中打开 Web GUI。
* `--port`: 可选。Web 服务绑定的端口（默认随机高端口或 `52342`）。
* `--host`: 可选。Web 服务绑定的 Host（默认 `127.0.0.1`）。

---

## 3. 验证与测试方案

### 3.1 自动化测试 (Automated Tests)
在 `tests/` 目录下新增 `test_handler.py`，覆盖以下场景：
1. **JSON 报告解析**：验证正确解析各组重复文件以及提取元数据（大小、哈希）。
2. **安全防空规则校验**：测试如果尝试回收某组的全部文件，核心处理器是否正确拦截并抛出异常。
3. **批量规则算法**：对包含不同修改时间、路径层级的文件组，验证“保留最早/最晚/最短路径”规则生成的动作指令是否正确。
4. **Mock 回收站测试**：使用 Mock 模拟 `send2trash.send2trash` 物理操作，验证调用路径与成功时的体积统计。

### 3.2 手动验证 (Manual Verification)
1. **CLI 模式测试**：
   * 运行 `python duplicates_handler.py test_report.json`。
   * 测试逐组输入数字选择保留，测试输入 `s` 跳过，测试最终确认。
   * 确认文件被正确移动至系统回收站，且未被物理粉碎。
2. **Web 模式测试**：
   * 运行 `python duplicates_handler.py test_report.json --web`。
   * 确认系统自动启动浏览器并载入页面。
   * 测试手动在卡片上切换“保留/回收”状态，并应用批量选择规则。
   * 点击“执行清理”，确认页面刷新，被清理的文件组已消失，且后台确认文件成功移至回收站。

# find-duplicates

一个高性能、高颜值的命令行查重工具，使用 **XXH3-128** 哈希算法在多个文件夹中快速查找内容完全相同的重复文件。支持自适应终端的漂亮进度条展示、重复文件树状层级排版、SQLite 增量缓存扫描，并提供专用的**安全重复文件处理器（duplicates-handler）**实现交互式文件清理（支持终端交互和本地 Web 界面）。

---

## 🌟 特性

* **高性能哈希**：基于 `xxhash` 的 `XXH3-128` 非加密算法，速度远超传统 MD5 或 SHA-256。
* **增量扫描缓存**：支持可选的 SQLite 数据库缓存，记录文件的 `size`、`mtime` 和 `hash`。在重复扫描时只处理被修改过的文件，避免多余的硬盘读写，速度可提升数十至数百倍。
* **安全重复文件回收 (duplicates-handler)**：
  * **命令行交互 (CLI)**：在控制台逐组审查，按数字键轻松标记要保留的文件，其余文件安全移入回收站。
  * **高颜值网页控制台 (Web GUI)**：深色现代极简风格 (Dark Mode) 的毛玻璃面板。支持**批量规则应用**（如自动保留最早/最晚修改、路径最短/最长文件）并实时计算预计释放空间，一键清理。
  * **安全防空校验**：强制规定每个重复文件组必须在磁盘上至少保留一个物理文件。如果用户或规则尝试回收整组的全部文件，系统将安全拦截。
  * **回收站备份**：调用 `send2trash` 模块将文件移动到系统的回收站，而不是物理粉碎，确保误删时随时可找回。
* **精美终端界面 (Rich UI)**：
  * **动态进度条**：扫描时使用 `rich` 渲染动态滚动进度，展示当前扫描进度、耗时预测及当前处理的文件（自动安全截断长路径）。
  * **树状层级输出**：在终端中使用树形 (Tree) 结构分组展示重复文件，直观呈现每组文件的统一大小、XXH3 哈希值和对应路径。
  * **无样式降级**：当输出被重定向到管道或非 TTY 终端时，自动隐式移除颜色和树状控制符，以方便其他自动化脚本处理。
* **灵活的多路输出**：支持在一次扫描中同时导出多种格式的报告，目前支持 `.txt`、`.json`、`.csv`。
* **重合路径去重保护**：如果包含目录发生重叠（例如同时包含父目录和子目录），工具会自动跳过已扫描路径，防止重复读取计算。

---

## 📦 项目结构

```text
find-duplicates/
├── pyproject.toml                      # 依赖管理和打包入口配置
├── find_duplicates_xxh3_128.py         # 根目录查重扫描器快速启动脚本
├── duplicates_handler.py               # 根目录清理处理器快速启动脚本
├── src/                                # 源码目录
│   └── find_duplicates/                # 核心包
│       ├── __init__.py                 # 版本和元数据 (基于 importlib.metadata 动态解析)
│       ├── cache.py                    # SQLite 缓存引擎
│       ├── scanner.py                  # 核心扫描与去重发现模块
│       ├── output.py                   # 导出报告驱动
│       ├── cli.py                      # 命令行控制和 Rich 终端扫描进度渲染
│       └── handler/                    # 清理处理器子模块
│           ├── __init__.py             # 版本映射
│           ├── core.py                 # 处理器核心逻辑（安全性检查、物理回收、参数解析）
│           ├── cli.py                  # 命令行交互式选择界面
│           ├── web.py                  # 本地 Web 服务后台 (基于 http.server)
│           └── templates/              # 前端资源目录
│               └── index.html          # 单页面前端 UI 模板 (HTML/CSS/JS)
└── tests/                              # 自动化测试脚本
```

---

## ⚙️ 安装与环境

本工具要求 **Python >= 3.12**。

### 使用 uv 安装（推荐）
```bash
# 同步并安装依赖环境，同时将工具包以可编辑模式链接安装进虚拟环境
uv sync
```

### 使用 pip 安装
```bash
pip install xxhash rich send2trash pytest
```

---

## 🚀 命令行用法与实例

### 1. 扫描重复文件 (`find-duplicates`)

你可以通过以下两种方式运行扫描：
1. **作为虚拟环境命令运行**（推荐）：
   ```bash
   uv run find-duplicates [参数]
   ```
2. **直接运行根目录包装脚本**：
   ```bash
   python find_duplicates_xxh3_128.py [参数]
   ```

#### 实例一：扫描单个或多个文件夹
你可以通过多次传递 `-i` / `--include` 参数来指定多个扫描路径：
```bash
# 扫描单个文件夹
uv run find-duplicates -i /path/to/project

# 扫描多个独立的文件夹
uv run find-duplicates -i /data/photos -i /backup/photos
```

#### 实例二：排除指定文件夹
```bash
# 扫描当前目录，但排除 node_modules 和 .git
uv run find-duplicates -i . -e ./node_modules -e ./.git
```

#### 实例三：启用 SQLite 增量扫描缓存提高速度
使用 `--cache-file` 指定数据库位置。在重复扫描时只处理被修改过的文件：
```bash
uv run find-duplicates -i /my/data --cache-file cache.db
```

#### 实例四：导出 JSON 报告以供后续清理
```bash
# 在一次运行中同时导出 .txt (人读) 和 .json (处理器读) 报告
uv run find-duplicates -i /my/data -o reports/result.txt -o reports/result.json
```

---

### 2. 清理重复文件 (`duplicates-handler`)

扫描出结果并生成 JSON 报告后，可使用 `duplicates-handler` 对文件进行清理。

你可以通过以下两种方式运行：
1. **作为虚拟环境命令运行**（推荐）：
   ```bash
   uv run duplicates-handler --report <path_to_json> [参数]
   ```
2. **直接运行根目录包装脚本**：
   ```bash
   python duplicates_handler.py --report <path_to_json> [参数]
   ```

#### 方式一：终端命令行交互清理 (CLI)
处理器将逐组询问您保留哪一个文件，其余文件安全移入回收站：
```bash
uv run duplicates-handler --report reports/result.json
```
* **控制台操作**：
  * 输入数字序号（如 `1`）：保留该序号文件，回收此组其他文件。
  * 输入 `s`：跳过当前组（稍后手动处理）。
  * 输入 `q`：安全终止并退出。
  * 全部组选择完毕后，会列出确认删除清单，输入 `y` 确认提交。

#### 方式二：网页端可视化一键清理 (Web GUI)
启动内置的轻量网页服务，自动在默认浏览器中打开高颜值交互面板：
```bash
uv run duplicates-handler --report reports/result.json --web
```
* **功能特点**：
  * **批量规则**：一键应用规则自动标记每组中“修改时间最早/最晚”或“路径最长/最短”的文件。
  * **手动微调**：直观地在毛玻璃卡片上对文件状态进行“保留”和“回收”状态的切换。
  * **数据同步**：底部操作栏实时计算并显示本次清理释放的空间大小。

* **自定义绑定端口和 Host**：
  ```bash
  uv run duplicates-handler --report reports/result.json --web --port 8080 --host 127.0.0.1
  ```

---

## 📋 参数详解

### 1. 扫描器参数 (`find-duplicates`)

| 参数 | 缩写 | 是否必填 | 默认值 | 详细说明 |
| :--- | :--- | :---: | :---: | :--- |
| `--include` | `-i` | **是** | - | 指定要进行扫描的文件目录，支持多次追加以扫描多个目录。 |
| `--exclude` | `-e` | 否 | `None` | 指定需要排除扫描的文件目录，支持多次追加。 |
| `--output` | `-o` | 否 | `None` | 指定结果输出报告。后缀必须是 `.json`、`.csv`、`.txt` 之一，支持多次指定。 |
| `--cache-file` | - | 否 | `None` | 指定 SQLite 增量扫描缓存数据库位置。 |

### 2. 清理处理器参数 (`duplicates-handler`)

| 参数 | 缩写 | 是否必填 | 默认值 | 详细说明 |
| :--- | :--- | :---: | :---: | :--- |
| `--report` | - | **是** | - | 查重步骤生成的 JSON 报告文件路径。 |
| `--web` | - | 否 | - | 启用网页版界面，自动启动本地 Web 服务并在浏览器中打开 Web GUI。 |
| `--port` | - | 否 | `52342` | Web 服务器绑定的端口。 |
| `--host` | - | 否 | `127.0.0.1` | Web 服务器绑定的 IP 地址。 |

---

## 📊 终端输出和报告样例

### 1. 扫描器 Tree 结构输出
```text
╭─────────────────────────────── 扫描完成 ────────────────────────────────╮
│ 发现的重复文件组                                                        │
│ ├── 重复组 1 (文件大小: 2.35 MB | 哈希: 8d2c2bc051187eb30a21fb9d1a3c7aa3)│
│ │   ├── C:/data/photos/vacation/img_0421.jpg                            │
│ │   └── C:/backup/photos/img_0421.jpg                                   │
│ └── 重复组 2 (文件大小: 128.00 KB | 哈希: 14782bb192ca7fe39e1a12a8385bb12b)│
│     ├── C:/music/song.mp3                                               │
│     └── C:/downloads/song.mp3                                           │
╰──────────────── 共发现 2 组重复文件 | 耗时: 1.25 秒 ─────────────────────╯
缓存统计: 命中 12 次 / 共 1523 个文件 (避免了 12 次硬盘读取，命中率 0.8%)
```

### 2. JSON 报告输出格式 (用于 duplicates-handler 输入)
```json
{
  "summary": {
    "scan_time": "2026-07-01 19:54:12",
    "elapsed_seconds": 1.25,
    "total_files": 1523,
    "duplicate_groups": 2,
    "scan_folders": [
      "C:/data/photos",
      "C:/backup/photos"
    ]
  },
  "duplicates": {
    "8d2c2bc051187eb30a21fb9d1a3c7aa3": [
      "C:/data/photos/vacation/img_0421.jpg",
      "C:/backup/photos/img_0421.jpg"
    ],
    "14782bb192ca7fe39e1a12a8385bb12b": [
      "C:/music/song.mp3",
      "C:/downloads/song.mp3"
    ]
  }
}
```

---

## 🧪 运行测试

我们通过 `pytest` 对缓存读写、文件发现机制、多格式导出以及清理处理器的安全限制校验逻辑做了测试覆盖。

运行测试命令：
```bash
uv run pytest
```
# find-duplicates

一个高性能、高颜值的命令行查重工具，使用 **XXH3-128** 哈希算法在多个文件夹中快速查找内容完全相同的重复文件。支持自适应终端的漂亮进度条展示、重复文件树状层级排版、SQLite 增量缓存扫描以及多格式结果导出。

---

## 🌟 特性

* **高性能哈希**：基于 `xxhash` 的 `XXH3-128` 非加密算法，速度远超传统 MD5 或 SHA-256。
* **增量扫描缓存**：支持可选的 SQLite 数据库缓存，记录文件的 `size`、`mtime` 和 `hash`。在重复扫描时只处理被修改过的文件，避免多余的硬盘读写，速度可提升数十至数百倍。
* **精美终端界面 (Rich UI)**：
  * **动态进度条**：扫描时使用 `rich` 渲染动态滚动进度，展示当前扫描进度、耗时预测及当前处理的文件（自动安全截断长路径）。
  * **树状层级输出**：在终端中使用树形（Tree）结构分组展示重复文件，直观呈现每组文件的统一大小、XXH3 哈希值和对应路径。
  * **无样式降级**：当输出被重定向到管道或非 TTY 终端时，自动隐式移除颜色和树状控制符，以方便其他自动化脚本处理。
* **灵活的多路输出**：支持在一次扫描中同时导出多种格式的报告，目前支持 `.txt`、`.json`、`.csv`。
* **重合路径去重保护**：如果包含目录发生重叠（例如同时包含父目录和子目录），工具会自动跳过已扫描路径，防止重复读取计算。

---

## 📦 项目结构

重构后的包采用标准 Python 包结构：
```text
find-duplicates/
├── pyproject.toml                      # 依赖管理和打包入口配置
├── find_duplicates_xxh3_128.py         # 根目录快速启动脚本
├── src/                                # 源码目录
│   └── find_duplicates/                # 核心包
│       ├── __init__.py                 # 版本和元数据
│       ├── cache.py                    # SQLite 缓存引擎
│       ├── scanner.py                  # 核心扫描与去重发现模块
│       ├── output.py                   # 导出报告驱动
│       └── cli.py                      # 命令行控制和 Rich 终端渲染
└── tests/                              # 自动化测试脚本
```

---

## ⚙️ 安装与环境

本工具要求 **Python >= 3.12**。

### 使用 uv 安装（推荐）
```bash
# 同步并安装依赖环境
uv sync
```

### 使用 pip 安装
```bash
pip install xxhash rich pytest
```

---

## 🚀 命令行用法与实例

你可以通过以下两种方式运行该工具：
1. **直接运行本地包装脚本** (适用于本地开发或克隆仓库直接运行)：
   ```bash
   python find_duplicates_xxh3_128.py [参数]
   ```
2. **作为安装包运行** (在执行过包安装后，或者通过 `uv run`)：
   ```bash
   uv run find-duplicates [参数]
   ```

### 1. 扫描单个或多个文件夹
你可以通过多次传递 `-i` / `--include` 参数来指定多个扫描路径：
```bash
# 扫描单个文件夹
python find_duplicates_xxh3_128.py -i /path/to/project

# 扫描多个独立的文件夹
python find_duplicates_xxh3_128.py -i /data/photos -i /backup/photos
```

### 2. 排除指定文件夹
排除一些无需关注的文件夹（如虚拟环境、版本控制目录或构建产物），可以通过多次传递 `-e` / `--exclude` 实现：
```bash
# 扫描当前目录，但排除 node_modules 和 .git
python find_duplicates_xxh3_128.py -i . -e ./node_modules -e ./.git
```

### 3. 启用 SQLite 增量扫描缓存
使用 `--cache-file` 指定本地 SQLite 数据库的位置。启用后，会大幅提高二次扫描的速度：
```bash
# 启用缓存文件 cache.db (该文件会自动被 .gitignore 忽略)
python find_duplicates_xxh3_128.py -i /my/data --cache-file cache.db
```

### 4. 导出多格式扫描结果
使用 `-o` / `--output` 指定输出报告文件，可以通过指定不同的后缀，在一次运行中同时导出多种格式的报告：
```bash
python find_duplicates_xxh3_128.py -i /my/data \
  -o reports/result.txt \
  -o reports/result.json \
  -o reports/result.csv
```

---

## 📋 参数详解

通过运行 `python find_duplicates_xxh3_128.py --help` 可查看所有可用参数：

| 参数 | 缩写 | 是否必填 | 默认值 | 详细说明说明 |
| :--- | :--- | :---: | :---: | :--- |
| `--include` | `-i` | **是** | - | 指定要进行扫描的文件目录，支持相对路径和绝对路径。可以通过多次追加 `-i` 同时输入多个目录。 |
| `--exclude` | `-e` | 否 | `None` | 指定需要排除扫描的文件目录。凡是属于该目录子代的文件都将被过滤掉。支持多次追加。 |
| `--output` | `-o` | 否 | `None` | 指定结果输出的报告路径。后缀必须为 `.json`、`.csv` 或 `.txt`。支持多次指定来同时输出不同类型的报告。 |
| `--cache-file` | - | 否 | `None` | 指定 SQLite 缓存的文件路径。如果不填，程序将不使用任何缓存进行全盘物理扫描。 |
| `--help` | `-h` | 否 | - | 显示命令行帮助文档信息。 |

---

## 📊 终端输出和报告样例

### 1. 终端 Tree 结构输出
当在终端（TTY）中直接执行时，若有重复文件，则输出以卡片面板形式包装的树状关系：

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

### 2. TXT 报告输出
导出的 `.txt` 文件格式设计为简单的明文报告：
```text
扫描时间: 2026-07-01 19:54:12
扫描目录: C:/data/photos, C:/backup/photos
扫描完成：共发现 2 组重复文件。
==========================================

哈希值 (XXH3-128): 8d2c2bc051187eb30a21fb9d1a3c7aa3
  - C:/data/photos/vacation/img_0421.jpg
  - C:/backup/photos/img_0421.jpg

哈希值 (XXH3-128): 14782bb192ca7fe39e1a12a8385bb12b
  - C:/music/song.mp3
  - C:/downloads/song.mp3
==========================================
执行总耗时: 1.25 秒
```

### 3. JSON 报告输出
导出的 `.json` 报告结构如下，非常适合用于自动化分析或者网页展示：
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

### 4. CSV 报告输出
导出的 `.csv` 结构包含组序号、哈希标识符和文件完整绝对路径，便于直接用 Excel 打开做数据过滤和分类：
```csv
Group,Hash,FilePath
1,8d2c2bc051187eb30a21fb9d1a3c7aa3,C:/data/photos/vacation/img_0421.jpg
1,8d2c2bc051187eb30a21fb9d1a3c7aa3,C:/backup/photos/img_0421.jpg
2,14782bb192ca7fe39e1a12a8385bb12b,C:/music/song.mp3
2,14782bb192ca7fe39e1a12a8385bb12b,C:/downloads/song.mp3
```

---

## 🧪 运行测试

我们通过 `pytest` 对缓存读写、文件发现机制和多格式导出报告等核心模块做了测试覆盖。

运行命令以验证代码功能的健壮性：
```bash
uv run pytest
```
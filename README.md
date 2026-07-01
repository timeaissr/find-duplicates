# find-duplicates

使用 XXH3-128 哈希算法递归扫描文件夹，快速查找内容完全相同的重复文件。

## 特性

- **XXH3-128 哈希**：使用高性能非加密哈希算法，比 MD5/SHA 更快
- **多目录扫描**：支持同时指定多个目标目录
- **排除目录**：可排除不需要扫描的子目录
- **动态进度条**：根据终端宽度自适应调整，中文字符宽度精确对齐
- **去重保护**：多目录重叠时自动跳过已处理文件，避免重复计算

## 依赖

- Python >= 3.12
- [xxhash](https://github.com/ifduyue/python-xxhash) >= 3.8.0

## 安装

```bash
# 使用 uv（推荐）
uv sync

# 或使用 pip
pip install xxhash
```

## 用法

```bash
# 扫描单个目录
python find_duplicates_xxh3_128.py -i /path/to/dir

# 扫描多个目录
python find_duplicates_xxh3_128.py -i /path/to/dir1 -i /path/to/dir2

# 排除指定目录
python find_duplicates_xxh3_128.py -i /path/to/dir -e /path/to/dir/node_modules -e /path/to/dir/.git
```

### 参数说明

| 参数 | 说明 |
|------|------|
| `-i`, `--include` | 要扫描的文件夹路径，可多次使用 |
| `-e`, `--exclude` | 要排除的文件夹路径，可多次使用 |

## 输出示例

```
正在统计文件总数...
共找到 1523 个文件。开始计算哈希值...
[████████████████----] 80.0% (1218/1523) 正在读取: .../photos/vacation/img_0421.jpg

==========================================
找到 3 组重复文件（共涉及 7 个文件）：

[重复组 1] 文件大小: 2.35 MB
  - C:/docs/report_v1.pdf
  - C:/backup/report_v1.pdf

[重复组 2] 文件大小: 512.00 KB
  - C:/photos/img_001.jpg
  - C:/photos/backup/img_001.jpg
  - C:/exports/img_001.jpg

[重复组 3] 文件大小: 128.00 KB
  - C:/music/song.mp3
  - C:/downloads/song.mp3
==========================================
执行总耗时: 3.42 秒
```

## 许可

MIT
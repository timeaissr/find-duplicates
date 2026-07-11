# 增加包含单个文件的功能设计文档

本文档详述了如何为查重工具 `find-duplicates` 增加对单个文件进行扫描支持的设计方案。

## 需求背景
目前，用户通过 `-i` / `--include` 参数只能指定需要扫描的文件夹，如果指定的路径不是文件夹会被静默跳过。为了提高工具的灵活性，需要支持直接对单个文件进行查重扫描（如 `find-duplicates -i file1.txt -i file2.txt`）。

## 设计原则与行为约定
1. **统一输入入口**：保持使用 `-i` / `--include` 作为输入参数，使其不仅支持输入文件夹，还支持输入单个文件。
2. **安全排除优先**：当指定的单个文件路径满足排除规则时（例如文件本身或其父文件夹在 `-e` / `--exclude` 列表中），该文件依然会被正常排除，不进行扫描哈希。
3. **缓存有效性与清理**：在增量缓存更新和清理（Pruning）阶段，对于显式指定的单个文件，仅对该文件对应的精确路径做缓存状态的校验与失效清除，避免误伤同名目录或其他分支路径下的缓存。

## 详细变更

### 1. 扫描生成器更新 (`src/find_duplicates/scanner.py`)
修改前，`scan_duplicates_generator` 在遍历 `include_dirs` 时仅处理文件夹：
```python
    for root_dir in include_dirs:
        root_path = Path(root_dir).resolve()
        if not root_path.is_dir():
            continue
```

修改后，变更为统一解析文件与目录的逻辑：
- 检查 `root_path` 是否存在，如果不存在则跳过。
- 如果 `root_path` 是单个文件（`root_path.is_file() and not root_path.is_symlink()`）：
  - 检查该文件是否被排除（其绝对路径是否是任意排除路径本身或其子路径）。
  - 检查该文件是否是当前的 SQLite 缓存文件（若是则跳过以避免自循环读取）。
  - 检查该文件是否已在 `seen_paths` 中去重。
  - 若均通过，加入 `seen_paths` 并追加至待扫描 `file_list`。
- 如果 `root_path` 是文件夹（`root_path.is_dir()`）：
  - 检查该文件夹是否被排除，若未排除则递归扫描其中的所有子文件并追加至 `file_list`。

### 2. 缓存清理模块更新 (`src/find_duplicates/cache.py`)
在 `prune_stale_records` 方法中，更新获取当前扫描范围内缓存记录的 SQL 查询：
- 如果 `root_path` 存在且为文件：
  - 仅查询匹配该路径的缓存记录：`SELECT filepath FROM file_cache WHERE filepath = ?`。
- 如果 `root_path` 是文件夹或已不存在：
  - 查询匹配该文件夹及子目录的记录：`SELECT filepath FROM file_cache WHERE filepath = ? OR filepath LIKE ?`。

### 3. 命令行接口更新 (`src/find_duplicates/cli.py`)
- 更新 `--include` / `-i` 参数的 `help` 描述文字，改写为支持文件夹与文件的通用表述。

## 验证计划

### 自动化测试 (`tests/test_scanner.py`)
1. **测试包含单个文件查重**：
   - 构造两个内容相同的临时文件，通过 `--include` 显式传入这两个文件的路径，验证能够正确识别它们是重复的，且 total_files 为 2。
2. **测试包含单个文件与目录混合查重**：
   - 传入一个文件夹路径和一个单独的文件路径，验证混合模式下依然能正确扫描并识别重复。
3. **测试排除单个文件**：
   - 传入一个文件路径，并将其添加到排除参数 `--exclude` 中，验证该文件不会被扫描。

---
## 自我审查 (Self-Review)
- **无 TBD / TODO**：设计明确，未留有待定字段。
- **一致性**：文件处理和目录处理在过滤机制上完全一致，遵循相同的排除和防自循环读取规则。
- **作用域**：本次修改完全局限在 `scanner.py`、`cache.py`、`cli.py` 以及测试脚本中，不影响 `handler/` 模块的任何逻辑。

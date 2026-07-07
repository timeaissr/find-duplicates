# 规格说明书：重命名快速启动脚本

为了配合多哈希算法（XXH3 和 BLAKE3）的支持，将原有的 `find_duplicates_xxh3_128.py` 脚本重命名为更通用的 `find_duplicates.py`。

## 变更内容

### 启动脚本

#### [DELETE] [find_duplicates_xxh3_128.py](file:///c:/projects/find-duplicates/find_duplicates_xxh3_128.py)
#### [NEW] [find_duplicates.py](file:///c:/projects/find-duplicates/find_duplicates.py)

内容保持不变，仍然是：
```python
from find_duplicates.cli import main

if __name__ == "__main__":
    import sys
    sys.exit(main())
```

### 项目文档

#### [MODIFY] [README.md](file:///c:/projects/find-duplicates/README.md)
将所有 `find_duplicates_xxh3_128.py` 引用更新为 `find_duplicates.py`。

## 验证计划

- 运行 `uv run pytest` 确保现有测试通过。
- 手动执行 `python find_duplicates.py --help` 确保启动脚本能正常运行。

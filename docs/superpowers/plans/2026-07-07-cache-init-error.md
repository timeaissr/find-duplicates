# 缓存初始化失败终止程序实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 当指定了 `--cache-file` 且缓存初始化/读取失败时，使程序直接报错并安全终止退出，而非降级继续物理扫描。

**Architecture:** 
1. 改造 `FileCache` 类的初始化流程，捕获 `sqlite3.Error` 并在关闭连接后抛出 `RuntimeError`；
2. 将 `cli.py` 中 `FileCache` 的实例化移动到主 `try` 块内，统一由已有的 `except RuntimeError` 拦截并友好报错输出，通过 `sys.exit(1)` 退出。

**Tech Stack:** Python 3.12, SQLite, pytest, rich

## Global Constraints

- 缓存初始化失败时必须终止程序，不能降级继续物理扫描。
- 出错退出时必须向 `sys.stderr` 打印清洁的美化错误信息，而非 Python 回溯堆栈 (Traceback)。
- 如果数据库连接已打开但后续初始化（如建表）失败，必须显式关闭连接并清理资源。

---

### Task 1: 缓存组件抛出 RuntimeError 改造与单元测试

**Files:**
- Modify: `src/find_duplicates/cache.py` (L9-L52)
- Modify: `tests/test_cache.py` (在文件末尾新增测试用例)

**Interfaces:**
- Consumes: None
- Produces: `FileCache(db_path)` 实例化时在初始化失败时抛出 `RuntimeError`。

- [ ] **Step 1: 编写失败测试用例**

在 `tests/test_cache.py` 结尾添加 `test_cache_init_failure` 用例，通过提供非法路径触发 `sqlite3.Error`：

```python
def test_cache_init_failure():
    import pytest
    # 使用包含不存在父目录的路径，强制 sqlite3 抛出 OperationalError
    with pytest.raises(RuntimeError) as exc_info:
        FileCache("nonexistent_dir_12345/cache.db")
    assert "无法初始化缓存数据库" in str(exc_info.value)
```

- [ ] **Step 2: 运行测试以验证其失败**

运行：`uv run pytest tests/test_cache.py -k test_cache_init_failure -v`
预期结果：测试失败（因为当前 `FileCache` 内部捕获了异常且没有向外抛出，导致没有触发 `RuntimeError`）。

- [ ] **Step 3: 改造 `cache.py` 异常抛出逻辑**

修改 `src/find_duplicates/cache.py` 中 `__init__` 和 `_init_db` 方法，移除警告打印，改为抛出 `RuntimeError` 并清理连接：

```python
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        try:
            self.conn = sqlite3.connect(db_path)
            self._init_db()
        except sqlite3.Error as e:
            if self.conn:
                try:
                    self.conn.close()
                except sqlite3.Error:
                    pass
                self.conn = None
            raise RuntimeError(f"无法初始化缓存数据库: {e}")

    def _init_db(self):
        if not self.conn:
            return
        try:
            cursor = self.conn.cursor()
            cursor.execute("PRAGMA table_info(file_cache)")
            rows = cursor.fetchall()
            columns = {row[1] for row in rows}
            pk_columns = {row[1] for row in rows if row[5] > 0}
            
            expected_columns = {"filepath", "size", "mtime", "hash", "algorithm"}
            expected_pks = {"filepath", "algorithm"}
            
            if columns != expected_columns or pk_columns != expected_pks:
                with self.conn:
                    self.conn.execute("DROP TABLE IF EXISTS file_cache")
                    self.conn.execute("""
                        CREATE TABLE file_cache (
                            filepath TEXT,
                            size INTEGER,
                            mtime REAL,
                            algorithm TEXT,
                            hash TEXT,
                            PRIMARY KEY (filepath, algorithm)
                        )
                    """)
        except sqlite3.Error as e:
            raise RuntimeError(f"无法初始化缓存数据库表结构: {e}")
```

- [ ] **Step 4: 运行测试验证通过**

运行：`uv run pytest tests/test_cache.py -v`
预期结果：所有缓存测试用例均通过（包括新加的 `test_cache_init_failure`）。

- [ ] **Step 5: 提交更改**

```bash
git add src/find_duplicates/cache.py tests/test_cache.py
git commit -m "refactor: raise RuntimeError when cache DB init fails and add unit test"
```

---

### Task 2: 命令行入口集成错误捕获与手动验证

**Files:**
- Modify: `src/find_duplicates/cli.py` (L94-L108)

**Interfaces:**
- Consumes: `FileCache(db_path)` 初始化异常行为
- Produces: 命令行参数 `--cache-file` 初始化失败时，程序退出并返回状态码 1。

- [ ] **Step 1: 移动缓存初始化逻辑至 try 块内部**

修改 `src/find_duplicates/cli.py`：
```python
    start_time = time.perf_counter()
    duplicates = {}
    cache_hits = 0
    total_files = 0
    file_list = []

    try:
        # 初始化缓存
        cache = None
        if cache_file:
            cache = FileCache(cache_file)

        # 使用 rich progress bar
        with Progress(
```

- [ ] **Step 2: 手动验证 CLI 终止行为**

在终端执行包含不存在目录的缓存文件路径命令：
`uv run find-duplicates -i . --cache-file nonexistent_dir_12345/cache.db`

预期结果：终端干净地输出红色报错（无 traceback），且进程退出状态码非 0：
```text
[错误] 无法初始化缓存数据库: unable to open database file
```

- [ ] **Step 3: 运行所有自动化测试**

运行：`uv run pytest`
预期结果：全部测试通过。

- [ ] **Step 4: 提交更改**

```bash
git add src/find_duplicates/cli.py
git commit -m "feat: handle cache init error in CLI and exit clean"
```

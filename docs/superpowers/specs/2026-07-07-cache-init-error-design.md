# 缓存初始化失败终止程序设计文档

## 目标与背景

当前程序在指定 `--cache-file` 后，若 SQLite 数据库初始化失败（例如路径不可写、权限不足或表结构损坏等），会捕获 `sqlite3.Error` 并降级为无缓存模式继续物理扫描。
根据用户反馈，为了保证缓存的使用符合预期，避免用户误以为启用了缓存而实际上并未启用，当指定了 `--cache-file`且无法正常使用/初始化缓存时，程序应该直接**报错并终止运行**。

## 方案设计

### 1. `cache.py` 异常抛出改造

修改 `FileCache` 类的 `__init__` 和 `_init_db` 方法。遇到 `sqlite3.Error` 时：
1. 若 `self.conn` 已建立连接，捕获异常后安全关闭连接并置为 `None`。
2. 抛出 `RuntimeError` 异常，携带具体的错误说明。

### 2. `cli.py` 捕获异常与友好退出

在查重命令行入口中，将 `FileCache` 的实例化移至主 `try...except RuntimeError` 块内部。
当捕获到 `RuntimeError` 时：
1. 在标准错误 `sys.stderr` 中使用 `rich` 打印友好错误消息。
2. 调用 `sys.exit(1)` 退出程序，终止扫描。

### 3. 测试用例验证

在 `tests/test_cache.py` 中新增单元测试，传入无效或无权限的路径以测试初始化异常是否正确抛出。

## 变更文件明细

### [MODIFY] [cache.py](file:///c:/projects/find-duplicates/src/find_duplicates/cache.py)
*   改造 `FileCache.__init__` 和 `FileCache._init_db`，抛出 `RuntimeError` 代替原有的 `sys.stderr` 打印。

### [MODIFY] [cli.py](file:///c:/projects/find-duplicates/src/find_duplicates/cli.py)
*   将 `cache = FileCache(cache_file)` 移入 `try` 块内，统一错误退出处理。

### [MODIFY] [test_cache.py](file:///c:/projects/find-duplicates/tests/test_cache.py)
*   新增 `test_cache_init_failure` 测试用例。

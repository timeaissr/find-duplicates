# 规格说明书：移除根目录启动脚本

为了简化项目结构、避免命名空间冲突，并推荐统一的虚拟环境命令（`uv run`）运行方式，我们决定将根目录下的启动包装脚本全部移除。

## 变更内容

### 启动脚本

#### [DELETE] [find_duplicates_xxh3_128.py](file:///c:/projects/find-duplicates/find_duplicates_xxh3_128.py)
#### [DELETE] [duplicates_handler.py](file:///c:/projects/find-duplicates/duplicates_handler.py)

根目录下不再保留任何启动包装脚本，用户需统一使用以下命令运行工具：
- 扫描器：`uv run find-duplicates`
- 清理器：`uv run duplicates-handler`

### 项目文档

#### [MODIFY] [README.md](file:///c:/projects/find-duplicates/README.md)
- 移除所有关于 `python find_duplicates_xxh3_128.py` 的介绍和说明。
- 移除所有关于 `python duplicates_handler.py` 的介绍和说明。
- 更新项目结构（Directory Tree）展示。

## 验证计划

- 运行 `uv run pytest` 确保没有破坏任何核心模块或测试。
- 运行 `uv run find-duplicates --help` 确保打包入口命令正常运行。
- 运行 `uv run duplicates-handler --help` 确保打包入口命令正常运行。

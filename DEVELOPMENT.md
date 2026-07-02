# 开发规范 (Development Specification)

本文件定义了 `find-duplicates` 项目的开发、测试、版本控制以及代码规范，旨在帮助开发者和 AI 助手保持代码一致性，避免遗漏关键步骤。

---

## 1. 开发环境与依赖管理

项目使用 [uv](https://github.com/astral-sh/uv) 进行 Python 项目管理和依赖锁定。

* **依赖同步**：在克隆仓库或拉取最新更改后，请运行以下命令同步虚拟环境和依赖：
  ```bash
  uv sync
  ```
* **运行命令**：使用 `uv run` 来确保在正确的虚拟环境中执行脚本，例如：
  ```bash
  uv run find-duplicates --help
  ```
* **添加新依赖**：
  * 添加生产依赖：`uv add <package>`
  * 添加开发依赖：`uv add --dev <package>`

---

## 2. 版本控制与 SemVer 规范

为了防止因忘记升级版本号导致包管理混乱，项目严格执行**语义化版本（SemVer）**规范，并在每次修改后必须同步更新版本。

> [!IMPORTANT]
> **关于 0.y.z (初始开发阶段) 的特殊说明**：
> 目前项目主版本号为 `0`，根据 SemVer 规范，`0.y.z` 版本的升级规则有所调整：
> * **`0.y.z` $\rightarrow$ `0.y.(z+1)` (修订号升级)**：仅用于向下兼容的 Bug 修复。例如：`0.6.0` $\rightarrow$ `0.6.1`。
> * **`0.y.z` $\rightarrow$ `0.(y+1).0` (次版本号升级)**：用于增加新功能，**同时允许包含不向下兼容的修改**（例如数据库 schema 升级等破坏性变更）。例如：`0.5.0` $\rightarrow$ `0.6.0`。
> * 一旦发布 `1.0.0` 正式版，主版本号的递增才严格代表不向下兼容的变更。

### 版本升级流程
任何代码改动（除了纯粹的文档编辑），在提交（Git Commit）前必须执行以下流程：

1. **确定版本号变更类型**（当前阶段）：
   * **修订号（PATCH）**：`0.6.0` $\rightarrow$ `0.6.1`（Bug 修复，无功能变动，向下兼容）。
   * **次版本号（MINOR）**：`0.6.0` $\rightarrow$ `0.7.0`（包含新功能，可能伴随不向下兼容的破坏性修改）。
2. **更新配置文件**：
   * 修改 [pyproject.toml](pyproject.toml) 中的 `[project]` 表下的 `version` 字段。
3. **更新 Lock 文件**：
   * 在根目录下运行以下命令，更新 [uv.lock](uv.lock)：
     ```bash
     uv lock
     ```
4. **检查**：确认 `git diff` 中 `pyproject.toml` 和 `uv.lock` 的版本号保持一致。

---

## 3. 代码结构与模块职责

所有核心源码存放在 [src/find_duplicates/](src/find_duplicates/) 目录下：

* `cli.py`：负责处理命令行接口（CLI）参数解析、界面控制台交互逻辑。
* `scanner.py`：核心扫描逻辑，用于遍历目录、计算哈希值、判断重复文件。
* `cache.py`：负责 SQLite 缓存数据库的读写、表结构升级和增量扫描缓存逻辑。
* `output.py`：负责将重复文件扫描结果导出为文本、JSON 等多种格式。
* `handler/` (包)：处理重复文件后续动作的包（如 `send2trash` 删除、硬链接等）。

---

## 4. 代码质量与风格规范

* **Python 版本**：兼容 Python 3.12 及以上版本，鼓励使用类型标注（Type Hints）。
* **代码格式化与 Lint**：推荐使用 `ruff` 对代码进行格式化和静态分析。
* **注释与文档**：所有新增的公开类和方法必须附带简明清晰的 Docstring，解释其职责、参数及返回值。
* **不轻易删除现有注释**：在进行重构时，除非原注释与当前逻辑冲突，否则应予以保留，避免丢失上下文。

---

## 5. 测试规范

项目的所有单元测试和集成测试应存放于 [tests/](tests/) 目录中。

* **执行测试**：每次提交代码前，**必须**运行 pytest 确保所有现有测试通过：
  ```bash
  uv run pytest
  ```
* **编写测试**：
  * 引入新功能或修复 Bug 时，应当编写对应的单元测试文件或在已有测试中增加测试用例。
  * 涉及文件系统操作的测试，请使用 pytest 的 `tmp_path` fixture。

---

## 6. Git 提交规范

推荐使用清晰的 Commit Message 风格：
* `feat:`：引入新功能（例如：`feat: add CLI --algorithm flag`）
* `fix:`：修复 Bug（例如：`fix: handle permission error in scanning`）
* `chore:`：更新配置、依赖或琐碎任务（例如：`chore: bump version to 0.6.0`）
* `refactor:`：代码重构，既不修复 Bug 也不添加功能（例如：`refactor: modularize codebase`）

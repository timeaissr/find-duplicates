# Remove Starter Scripts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remove `find_duplicates_xxh3_128.py` and `duplicates_handler.py` from root directory and update all documentation references.

**Architecture:** Delete physical wrapper scripts and update instructions in `README.md` to recommend `uv run` command entry points.

**Tech Stack:** Python 3.12, Git

## Global Constraints

- Python >= 3.12
- Clean workspace (remove unused entry point scripts).
- Update references in README.md.

---

### Task 1: Delete root wrapper scripts

**Files:**
- Delete: `find_duplicates_xxh3_128.py`
- Delete: `duplicates_handler.py`

**Interfaces:**
- Consumes: None
- Produces: Cleaner workspace (no root python scripts)

- [ ] **Step 1: Delete both wrapper files**

Delete `find_duplicates_xxh3_128.py` and `duplicates_handler.py` from the root directory.

- [ ] **Step 2: Verify CLI commands still work via uv run**

Run: `uv run find-duplicates --help`
Expected: Outputs command-line argument instructions for scanning.

Run: `uv run duplicates-handler --help`
Expected: Outputs command-line argument instructions for handling duplicates.

- [ ] **Step 3: Commit the deletion changes**

Run:
```bash
git rm find_duplicates_xxh3_128.py duplicates_handler.py
git commit -m "feat: remove root launcher scripts find_duplicates_xxh3_128.py and duplicates_handler.py"
```

### Task 2: Update README.md references

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: Removed scripts (from Task 1)
- Produces: Updated `README.md` without references to deleted scripts

- [ ] **Step 1: Modify `README.md` to update references**

1. In the "📦 项目结构" section, remove the lines:
   ```text
   ├── find_duplicates_xxh3_128.py         # 根目录查重扫描器快速启动脚本
   ├── duplicates_handler.py               # 根目录清理处理器快速启动脚本
   ```
2. In the "🚀 命令行用法与实例" -> "1. 扫描重复文件" section, remove the option to run wrapper script:
   ```markdown
   你可以通过以下两种方式运行扫描：
   1. **作为虚拟环境命令运行**（推荐）：
      ```bash
      uv run find-duplicates [参数]
      ```
   2. **直接运行根目录包装脚本**：
      ```bash
      python find_duplicates_xxh3_128.py [参数]
      ```
   ```
   Replace it with:
   ```markdown
   你可以通过以下方式运行扫描：
   ```bash
   uv run find-duplicates [参数]
   ```
3. In the "2. 交互式清理处理器" section, change the run instruction from:
   ```markdown
   你可以通过以下两种方式运行处理器：
   1. **作为虚拟环境命令运行**（推荐）：
      ```bash
      uv run duplicates-handler --report <json_report_path> [参数]
      ```
   2. **直接运行根目录包装脚本**：
      ```bash
      python duplicates_handler.py --report <json_report_path> [参数]
      ```
   ```
   to:
   ```markdown
   你可以通过以下方式运行处理器：
   ```bash
   uv run duplicates-handler --report <json_report_path> [参数]
   ```

- [ ] **Step 2: Run git diff to check changes**

Run: `git diff README.md`
Expected: Diff shows removal of old run methods and project structure lines.

- [ ] **Step 3: Commit README changes**

Run:
```bash
git add README.md
git commit -m "docs: update README references to remove root launcher scripts"
```

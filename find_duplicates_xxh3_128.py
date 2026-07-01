#!/usr/bin/env python
import sys
import os

# 将 src/ 目录加入 sys.path 以支持在未安装包的情况下直接执行此脚本
src_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "src"))
if src_path not in sys.path:
    sys.path.insert(0, src_path)

from find_duplicates.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())

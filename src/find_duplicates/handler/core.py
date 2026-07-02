import json
from pathlib import Path
import send2trash

def load_json_report(report_path: Path) -> tuple[dict, dict]:
    """读取并解析查重JSON报告，返回 (summary, duplicates)。"""
    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("summary", {}), data.get("duplicates", {})

def validate_selections(duplicates: dict, keep_paths: set[str], trash_paths: set[str]) -> str | None:
    """校验选择是否安全。如果任一组的所有文件都被标记为删除，或者文件不存在，返回错误字符串。"""
    for hash_val, paths in duplicates.items():
        trash_count = sum(1 for p in paths if p in trash_paths)
        if trash_count == len(paths):
            return f"安全防护：重复组 {hash_val} 的所有文件都标记了删除，必须至少保留一个文件！"
    return None

def recycle_files(trash_paths: list[str]) -> tuple[int, int]:
    """物理移动文件至回收站。返回 (回收文件数, 释放空间字节数)。"""
    count = 0
    reclaimed_bytes = 0
    for path_str in trash_paths:
        path = Path(path_str)
        if path.is_file():
            size = path.stat().st_size
            send2trash.send2trash(str(path))
            count += 1
            reclaimed_bytes += size
    return count, reclaimed_bytes

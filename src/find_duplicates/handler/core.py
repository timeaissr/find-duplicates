import json
from pathlib import Path
import sys
import send2trash

def load_json_report(report_path: Path) -> tuple[dict, dict]:
    """读取并解析查重JSON报告，返回 (summary, duplicates)。"""
    with open(report_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("summary", {}), data.get("duplicates", {})

def validate_selections(duplicates: dict, keep_paths: set[str], trash_paths: set[str]) -> str | None:
    """校验选择是否安全。如果任一组的所有文件都被标记为删除，或者文件不存在，返回错误字符串。"""
    # 确保 keep_paths 与 trash_paths 没有重叠
    overlap = keep_paths & trash_paths
    if overlap:
        return f"安全防护：文件同时被标记为保留和删除：{', '.join(sorted(overlap))}"

    for hash_val, paths in duplicates.items():
        # 确保每个重复组中至少有一个文件未被标记为删除
        excluded_paths = [p for p in paths if p not in trash_paths]
        if not excluded_paths:
            return f"安全防护：重复组 {hash_val} 的所有文件都标记了删除，必须至少保留一个文件！"
        
        # 确保至少有一个保留的文件在磁盘上实际存在
        if not any(Path(p).is_file() for p in excluded_paths):
            return f"安全防护：重复组 {hash_val} 保留的文件均在磁盘上不存在，必须确保至少保留一个物理存在的文件！"
            
    return None

def recycle_files(trash_paths: list[str]) -> tuple[int, int]:
    """物理移动文件至回收站。返回 (回收文件数, 释放空间字节数)。"""
    count = 0
    reclaimed_bytes = 0
    for path_str in trash_paths:
        path = Path(path_str)
        if path.is_file():
            try:
                size = path.stat().st_size
                send2trash.send2trash(str(path))
                count += 1
                reclaimed_bytes += size
            except Exception as e:
                print(f"警告：物理移动文件至回收站失败 {path_str}，错误原因：{e}", file=sys.stderr)
    return count, reclaimed_bytes


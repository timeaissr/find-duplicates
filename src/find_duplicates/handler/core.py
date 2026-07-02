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


def main():
    import argparse
    import sys
    from .cli import run_cli_handler
    from .web import run_web_handler
    
    parser = argparse.ArgumentParser(
        description="重复文件选择处理器 (Duplicates Handler) - 安全清理冗余文件"
    )
    parser.add_argument("--report", required=True, help="查重生成的 JSON 报告文件路径")
    parser.add_argument("--web", action="store_true", help="启用网页模式启动本地服务及 GUI 交互")
    parser.add_argument("--port", type=int, default=52342, help="Web 服务器绑定的端口（默认: 52342）")
    parser.add_argument("--host", default="127.0.0.1", help="Web 服务器绑定的 Host（默认: 127.0.0.1）")
    
    args = parser.parse_args()
    report_path = Path(args.report)
    if not report_path.is_file():
        print(f"[错误] 报告文件不存在: '{args.report}'", file=sys.stderr)
        sys.exit(1)
        
    if args.web:
        run_web_handler(str(report_path), args.host, args.port)
    else:
        run_cli_handler(str(report_path))



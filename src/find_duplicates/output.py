import time
import json
import csv
from pathlib import Path


def write_results_to_file(
    output_path, duplicates, elapsed_time, total_files, include_dirs
):
    """将查重结果写入到指定的文件，支持 TXT, JSON, CSV 格式。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()

    if suffix == ".json":
        data = {
            "summary": {
                "scan_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "elapsed_seconds": round(elapsed_time, 2),
                "total_files": total_files,
                "duplicate_groups": len(duplicates),
                "scan_folders": [str(Path(d).resolve()) for d in include_dirs],
            },
            "duplicates": duplicates,
        }
        with path.open("w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    elif suffix == ".csv":
        with path.open("w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Group", "Hash", "FilePath"])
            for group_idx, (hsh, paths) in enumerate(duplicates.items(), start=1):
                for file_path in paths:
                    writer.writerow([group_idx, hsh, file_path])

    elif suffix == ".txt":
        with path.open("w", encoding="utf-8") as f:
            f.write(
                f"扫描时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n"
            )
            f.write(
                f"扫描目录: {', '.join(str(Path(d).resolve()) for d in include_dirs)}\n"
            )
            if not duplicates:
                f.write("扫描完成：未发现内容重复的文件。\n")
            else:
                f.write(f"扫描完成：共发现 {len(duplicates)} 组重复文件。\n")
                f.write("==========================================\n")
                for hsh, paths in duplicates.items():
                    f.write(f"\n哈希值 (XXH3-128): {hsh}\n")
                    for file_path in paths:
                        f.write(f"  - {file_path}\n")
                f.write("==========================================\n")
            f.write(f"执行总耗时: {elapsed_time:.2f} 秒\n")

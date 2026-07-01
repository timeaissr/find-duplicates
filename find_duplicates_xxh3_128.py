import sys
import time  # 导入 time 模块用于统计耗时
from collections import defaultdict
from pathlib import Path
import xxhash

def find_duplicates_pathlib_progress(root_dir):
    """
    使用 pathlib 遍历指定文件夹及其子文件夹，通过计算 XXH3-128 哈希值来查找内容完全相同的文件。
    包含实时进度条、当前读取文件路径的显示以及最终执行时间的统计。一旦遇到读取错误，程序直接终止。
    """
    # 记录程序开始执行的时间点
    start_time = time.perf_counter()
    
    root = Path(root_dir)
    
    # 1. 快速统计文件总数（仅获取路径，不读取内容）
    print("正在统计文件总数...")
    file_list = []
    
    for path in root.rglob('*'):
        if path.is_file() and not path.is_symlink():
            file_list.append(path)
            
    total_files = len(file_list)
    if total_files == 0:
        print("未找到任何文件。")
        return

    print(f"共找到 {total_files} 个文件。开始计算哈希值...")

    hash_map = defaultdict(list)
    chunk_size = 1024 * 1024  # 1MB 块大小
    processed_files = 0

    # 2. 开始遍历并计算哈希
    for path in file_list:
        processed_files += 1
        
        path_str = str(path)
        display_path = path_str
        if len(display_path) > 40:
            display_path = "..." + display_path[-37:]
        
        percent = (processed_files / total_files) * 100
        bar_length = 20
        filled_length = int(bar_length * processed_files // total_files)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        print(f"\r[{bar}] {percent:.1f}% ({processed_files}/{total_files}) 正在读取: {display_path}", end="", flush=True)

        try:
            hasher = xxhash.xxh3_128()
            with path.open('rb') as f:
                while chunk := f.read(chunk_size):
                    hasher.update(chunk)
            
            file_hash = hasher.hexdigest()
            hash_map[file_hash].append(path_str)
            
        except (OSError, PermissionError) as e:
            print("\r" + " " * 120 + "\r", end="", flush=True)
            print(f"[错误] 读取文件失败，程序终止！", file=sys.stderr)
            print(f"文件路径: {path}", file=sys.stderr)
            print(f"错误原因: {e}", file=sys.stderr)
            sys.exit(1)

    # 正常结束时换行
    print()

    # 3. 筛选重复文件
    duplicates = {hsh: paths for hsh, paths in hash_map.items() if len(paths) > 1}

    # 计算总耗时（单位：秒）
    end_time = time.perf_counter()
    elapsed_time = end_time - start_time

    if not duplicates:
        print("\n扫描完成：未发现内容重复的文件。")
        print(f"执行总耗时: {elapsed_time:.2f} 秒")
        return

    print(f"\n扫描完成：共发现 {len(duplicates)} 组重复文件。")
    print("==========================================")
    for hsh, paths in duplicates.items():
        print(f"\n哈希值 (XXH3-128): {hsh}")
        for path in paths:
            print(f"  - {path}")
    print("==========================================")
    
    # 打印最终执行时间
    print(f"执行总耗时: {elapsed_time:.2f} 秒")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("使用方法: python find_duplicates.py <目标文件夹路径>")
        sys.exit(1)
    
    target_directory = sys.argv[1]
    
    path_obj = Path(target_directory)
    if path_obj.is_dir():
        find_duplicates_pathlib_progress(target_directory)
    else:
        print(f"错误: '{target_directory}' 不是一个有效的文件夹路径。")
        sys.exit(1)
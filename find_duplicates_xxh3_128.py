import sys
import time
import shutil  # 用于获取终端窗口大小
import unicodedata  # 用于精确计算中文字符的视觉宽度
import argparse  # 用于解析命令行参数
from collections import defaultdict
from pathlib import Path
import xxhash

def get_char_width(char):
    """获取单个字符在终端中的视觉宽度（中文占2列，英文占1列）"""
    if unicodedata.east_asian_width(char) in ('W', 'F', 'A'):
        return 2
    return 1

def get_visual_width(text):
    """计算字符串在终端中的总视觉宽度"""
    return sum(get_char_width(c) for c in text)

def truncate_path_visually(path_str, max_width):
    """将路径从右侧截断（保留末尾文件名），并确保其视觉宽度不超过 max_width"""
    total_width = get_visual_width(path_str)
    if total_width <= max_width:
        return path_str
    
    # 需要预留 3 个宽度给 "..."
    target_width = max_width - 3
    if target_width <= 0:
        return "..."
    
    current_width = 0
    truncated_chars = []
    # 从后往前遍历，保留文件名和末尾路径
    for char in reversed(path_str):
        char_width = get_char_width(char)
        if current_width + char_width > target_width:
            break
        current_width += char_width
        truncated_chars.append(char)
    
    return "..." + "".join(reversed(truncated_chars))

def pad_to_visual_width(text, target_width):
    """用空格将字符串补齐到指定的视觉宽度，用于完美覆盖上一行"""
    current_width = get_visual_width(text)
    if current_width < target_width:
        return text + " " * (target_width - current_width)
    return text

def find_duplicates(include_dirs, exclude_dirs):
    """
    遍历多个指定的包含文件夹及其子文件夹，通过计算 XXH3-128 哈希值来查找内容完全相同的文件。
    支持排除指定的文件夹，进度条和文件名长度会根据当前终端窗口大小动态调整。
    """
    start_time = time.perf_counter()
    
    # 将所有排除路径解析为绝对路径
    exclude_paths = [Path(p).resolve() for p in exclude_dirs] if exclude_dirs else []
    
    # 1. 快速统计文件总数
    print("正在统计文件总数...")
    file_list = []
    seen_paths = set()  # 用于防止多个扫描目录重叠时重复处理同一个文件
    
    for root_dir in include_dirs:
        root_path = Path(root_dir).resolve()
        if not root_path.is_dir():
            print(f"警告: '{root_dir}' 不是一个有效的文件夹，已跳过。", file=sys.stderr)
            continue
            
        # 如果扫描的根目录本身就在排除列表中，直接跳过
        if any(root_path.is_relative_to(exclude) for exclude in exclude_paths):
            continue
            
        for path in root_path.rglob('*'):
            # 排除文件夹和符号链接，只保留普通文件
            if path.is_file() and not path.is_symlink():
                resolved_path = path.resolve()
                
                # 避免重复扫描（例如用户同时传入了父目录和子目录）
                if resolved_path in seen_paths:
                    continue
                
                # 检查当前文件是否在任何排除路径中
                if any(resolved_path.is_relative_to(exclude) for exclude in exclude_paths):
                    continue
                
                seen_paths.add(resolved_path)
                file_list.append(resolved_path)
            
    total_files = len(file_list)
    if total_files == 0:
        print("未找到任何有效文件。")
        return

    print(f"共找到 {total_files} 个文件。开始计算哈希值...")

    hash_map = defaultdict(list)
    chunk_size = 1024 * 1024  # 1MB 块大小
    processed_files = 0

    # 2. 开始遍历并计算哈希
    for path in file_list:
        processed_files += 1
        path_str = str(path)
        
        # 实时获取当前终端窗口的宽度
        terminal_columns, _ = shutil.get_terminal_size()
        
        # 根据终端宽度动态调整进度条本身的长度
        if terminal_columns >= 100:
            bar_length = 20
        elif terminal_columns >= 70:
            bar_length = 10
        else:
            bar_length = 5
            
        percent = (processed_files / total_files) * 100
        filled_length = int(bar_length * processed_files // total_files)
        bar = '█' * filled_length + '-' * (bar_length - filled_length)
        
        # 构造除路径外的固定部分，并计算其视觉宽度
        fixed_part = f"[{bar}] {percent:.1f}% ({processed_files}/{total_files}) 正在读取: "
        fixed_width = get_visual_width(fixed_part)
        
        # 动态计算留给路径的最大视觉宽度（预留 3 个字符的安全间距）
        max_path_width = terminal_columns - fixed_width - 3
        if max_path_width < 5:
            max_path_width = 5  # 保证在极窄终端下至少能显示几个字符
            
        # 动态截断路径
        display_path = truncate_path_visually(path_str, max_path_width)
        
        # 拼接当前行内容
        line_content = f"{fixed_part}{display_path}"
        
        # 将整行用空格补齐到刚好等于 terminal_columns - 1 的宽度
        padded_line = pad_to_visual_width(line_content, terminal_columns - 1)
        
        print(f"\r{padded_line}", end="", flush=True)

        try:
            hasher = xxhash.xxh3_128()
            with path.open('rb') as f:
                while chunk := f.read(chunk_size):
                    hasher.update(chunk)
            
            file_hash = hasher.hexdigest()
            hash_map[file_hash].append(path_str)
            
        except (OSError, PermissionError) as e:
            # 发生错误时，获取最新终端宽度并用空格清除整行，再输出错误信息并终止
            cols, _ = shutil.get_terminal_size()
            print("\r" + " " * (cols - 1) + "\r", end="", flush=True)
            print("[错误] 读取文件失败，程序终止！", file=sys.stderr)
            print(f"文件路径: {path}", file=sys.stderr)
            print(f"错误原因: {e}", file=sys.stderr)
            sys.exit(1)

    # 正常结束时换行
    print()

    # 3. 筛选重复文件
    duplicates = {hsh: paths for hsh, paths in hash_map.items() if len(paths) > 1}

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
    
    print(f"执行总耗时: {elapsed_time:.2f} 秒")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="使用 XXH3-128 算法在多个文件夹中查找内容重复的文件。")
    
    # 修改为 -i / --include，表示包含文件夹
    parser.add_argument(
        "-i", "--include", 
        action="append",
        required=True,
        help="要包含（扫描）的文件夹路径（若有多个，请多次使用 -i 或 --include）"
    )
    
    # 修改为 -e / --exclude，表示排除文件夹
    parser.add_argument(
        "-e", "--exclude", 
        action="append",
        default=None, 
        help="要排除的文件夹路径（若有多个，请多次使用 -e 或 --exclude）"
    )
    
    args = parser.parse_args()
    
    includes = args.include if args.include else []
    excludes = args.exclude if args.exclude else []
    
    # 执行查重主程序
    find_duplicates(includes, excludes)
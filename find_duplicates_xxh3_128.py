import sys
import time
import shutil  # 用于获取终端窗口大小
import unicodedata  # 用于精确计算中文字符的视觉宽度
import argparse  # 用于解析命令行参数
from collections import defaultdict
from pathlib import Path
import xxhash
import json
import csv
import sqlite3

class FileCache:
    """基于 SQLite 的文件哈希缓存，用于避免重复读取未修改的文件内容。"""
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        try:
            self.conn = sqlite3.connect(db_path)
            self._init_db()
        except sqlite3.Error as e:
            print(f"[警告] 无法初始化缓存数据库: {e}，将无法使用缓存功能。", file=sys.stderr)

    def _init_db(self):
        if not self.conn:
            return
        with self.conn:
            self.conn.execute("""
                CREATE TABLE IF NOT EXISTS file_cache (
                    filepath TEXT PRIMARY KEY,
                    size INTEGER,
                    mtime REAL,
                    hash TEXT
                )
            """)

    def get_hash(self, filepath: Path) -> str | None:
        """从缓存中检索哈希值，如果文件未修改则返回哈希，否则返回 None。"""
        if not self.conn:
            return None
        try:
            stat = filepath.stat()
            current_size = stat.st_size
            current_mtime = stat.st_mtime
            normalized_path = filepath.resolve().as_posix()
            
            cursor = self.conn.cursor()
            cursor.execute(
                "SELECT size, mtime, hash FROM file_cache WHERE filepath = ?",
                (normalized_path,)
            )
            row = cursor.fetchone()
            if row:
                cached_size, cached_mtime, cached_hash = row
                # 浮点数比对，保留微小容差
                if current_size == cached_size and abs(current_mtime - cached_mtime) < 1e-4:
                    return cached_hash
        except (OSError, sqlite3.Error):
            pass
        return None

    def update_hash(self, filepath: Path, file_hash: str):
        """将文件的当前状态和哈希值更新到数据库缓存中。"""
        if not self.conn:
            return
        try:
            stat = filepath.stat()
            normalized_path = filepath.resolve().as_posix()
            with self.conn:
                self.conn.execute(
                    "INSERT OR REPLACE INTO file_cache (filepath, size, mtime, hash) VALUES (?, ?, ?, ?)",
                    (normalized_path, stat.st_size, stat.st_mtime, file_hash)
                )
        except (OSError, sqlite3.Error):
            pass

    def prune_stale_records(self, include_dirs, keep_paths):
        """
        清理缓存中在当前扫描目录下但实际已被删除或改名的文件记录。
        """
        if not self.conn:
            return
        try:
            # 1. 查找当前扫描目录下所有的缓存记录
            cached_paths_in_scope = set()
            cursor = self.conn.cursor()
            
            for root_dir in include_dirs:
                root_path_str = Path(root_dir).resolve().as_posix()
                # 匹配目录本身或其子文件/子目录
                cursor.execute(
                    "SELECT filepath FROM file_cache WHERE filepath = ? OR filepath LIKE ?",
                    (root_path_str, root_path_str + "/%")
                )
                for row in cursor.fetchall():
                    cached_paths_in_scope.add(row[0])
            
            # 2. 找出已不存在（未被 keep_paths 记录）的缓存路径
            keep_paths_normalized = {Path(p).resolve().as_posix() for p in keep_paths}
            stale_paths = cached_paths_in_scope - keep_paths_normalized
            
            if stale_paths:
                # 3. 分批删除
                stale_list = list(stale_paths)
                batch_size = 999
                with self.conn:
                    for i in range(0, len(stale_list), batch_size):
                        batch = stale_list[i : i + batch_size]
                        placeholders = ",".join("?" for _ in batch)
                        self.conn.execute(
                            f"DELETE FROM file_cache WHERE filepath IN ({placeholders})",
                            batch
                        )
        except sqlite3.Error:
            pass

    def close(self):
        if self.conn:
            try:
                self.conn.close()
            except sqlite3.Error:
                pass


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

def write_results_to_file(output_path, duplicates, elapsed_time, total_files, include_dirs):
    """将查重结果写入到指定的文件，支持 TXT, JSON, CSV 格式。"""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = path.suffix.lower()
    
    if suffix == '.json':
        data = {
            "summary": {
                "scan_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()),
                "elapsed_seconds": round(elapsed_time, 2),
                "total_files": total_files,
                "duplicate_groups": len(duplicates),
                "scan_folders": [str(Path(d).resolve()) for d in include_dirs]
            },
            "duplicates": duplicates
        }
        with path.open('w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            
    elif suffix == '.csv':
        with path.open('w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(["Group", "Hash", "FilePath"])
            for group_idx, (hsh, paths) in enumerate(duplicates.items(), start=1):
                for file_path in paths:
                    writer.writerow([group_idx, hsh, file_path])
                    
    elif suffix == '.txt':
        with path.open('w', encoding='utf-8') as f:
            f.write(f"扫描时间: {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}\n")
            f.write(f"扫描目录: {', '.join(str(Path(d).resolve()) for d in include_dirs)}\n")
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

def find_duplicates(include_dirs, exclude_dirs, output_paths=None, cache_file_path=None):
    """
    遍历多个指定的包含文件夹及其子文件夹，通过计算 XXH3-128 哈希值来查找内容完全相同的文件。
    支持排除指定的文件夹，进度条和文件名长度会根据当前终端窗口大小动态调整。
    """
    start_time = time.perf_counter()
    
    # 初始化缓存
    cache = None
    cache_hits = 0
    if cache_file_path:
        cache = FileCache(cache_file_path)
    
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
                
                # 排除缓存文件本身
                if cache_file_path and resolved_path == Path(cache_file_path).resolve():
                    continue
                
                # 检查当前文件是否在任何排除路径中
                if any(resolved_path.is_relative_to(exclude) for exclude in exclude_paths):
                    continue
                
                seen_paths.add(resolved_path)
                file_list.append(resolved_path)
            
    total_files = len(file_list)
    if total_files == 0:
        print("未找到任何有效文件。")
        if output_paths:
            for out_path in output_paths:
                write_results_to_file(out_path, {}, 0.0, 0, include_dirs)
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
            file_hash = None
            if cache:
                file_hash = cache.get_hash(path)
                if file_hash:
                    cache_hits += 1
            
            if file_hash is None:
                hasher = xxhash.xxh3_128()
                with path.open('rb') as f:
                    while chunk := f.read(chunk_size):
                        hasher.update(chunk)
                file_hash = hasher.hexdigest()
                if cache:
                    cache.update_hash(path, file_hash)
            
            hash_map[file_hash].append(path_str)
            
        except (OSError, PermissionError) as e:
            # 发生错误时，获取最新终端宽度并用空格清除整行，再输出错误信息并终止
            cols, _ = shutil.get_terminal_size()
            print("\r" + " " * (cols - 1) + "\r", end="", flush=True)
            print("[错误] 读取文件失败，程序终止！", file=sys.stderr)
            print(f"文件路径: {path}", file=sys.stderr)
            print(f"错误原因: {e}", file=sys.stderr)
            if cache:
                cache.close()
            sys.exit(1)

    # 正常结束时换行
    print()

    # 清理失效缓存并关闭连接
    if cache:
        cache.prune_stale_records(include_dirs, file_list)
        cache.close()
        print(f"缓存统计: 命中 {cache_hits} 次 / 共 {total_files} 个文件 (避免了 {cache_hits} 次硬盘读取，命中率 {cache_hits/total_files*100:.1f}%)")

    # 3. 筛选重复文件
    duplicates = {hsh: paths for hsh, paths in hash_map.items() if len(paths) > 1}

    end_time = time.perf_counter()
    elapsed_time = end_time - start_time

    if not duplicates:
        print("\n扫描完成：未发现内容重复的文件。")
        print(f"执行总耗时: {elapsed_time:.2f} 秒")
        if output_paths:
            for out_path in output_paths:
                write_results_to_file(out_path, {}, elapsed_time, total_files, include_dirs)
        return

    print(f"\n扫描完成：共发现 {len(duplicates)} 组重复文件。")
    print("==========================================")
    for hsh, paths in duplicates.items():
        print(f"\n哈希值 (XXH3-128): {hsh}")
        for path in paths:
            print(f"  - {path}")
    print("==========================================")
    
    print(f"执行总耗时: {elapsed_time:.2f} 秒")

    if output_paths:
        for out_path in output_paths:
            write_results_to_file(out_path, duplicates, elapsed_time, total_files, include_dirs)

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
    
    # 增加 -o / --output，表示指定输出文件，支持多次使用同时输出多种格式
    parser.add_argument(
        "-o", "--output",
        action="append",
        default=None,
        help="指定输出文件路径，可多次指定以输出多种格式。后缀必须是 .txt, .json, .csv 之一（强制校验，不区分大小写）"
    )
    
    # 增加 --cache-file，指定 SQLite 缓存路径
    parser.add_argument(
        "--cache-file",
        default=None,
        help="指定 SQLite 缓存文件路径。若不指定，则不启用缓存（退化为完全物理扫描）"
    )
    
    args = parser.parse_args()
    
    includes = args.include if args.include else []
    excludes = args.exclude if args.exclude else []
    outputs = args.output if args.output else []
    cache_file = args.cache_file
    
    # 强制校验输出路径的后缀
    for out in outputs:
        p = Path(out)
        suffix = p.suffix.lower()
        if suffix not in ('.txt', '.json', '.csv'):
            parser.error(f"不支持的输出文件格式: '{out}'。后缀必须是 .txt, .json, .csv 之一。")
            
    # 执行查重主程序
    find_duplicates(includes, excludes, outputs, cache_file)
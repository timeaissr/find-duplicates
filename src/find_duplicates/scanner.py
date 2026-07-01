from pathlib import Path
from collections import defaultdict
import xxhash
from .cache import FileCache


def scan_duplicates_generator(
    include_dirs, exclude_dirs, cache: FileCache = None, cache_file_path: str = None
):
    """
    使用 XXH3-128 算法查找重复文件。
    这是一个生成器，通过 yield 报告扫描状态，避免直接依赖控制台输出。

    Yield 格式：
        - ("count_start", None): 开始统计文件总数
        - ("count_end", total_files): 统计文件总数完成
        - ("hash_progress", processed_files, total_files, current_path, is_cache_hit): 哈希计算进度

    返回：
        (duplicates, cache_hits, total_files, file_list)
    """
    # 1. 统计文件阶段
    yield ("count_start", None)

    exclude_paths = [Path(p).resolve() for p in exclude_dirs] if exclude_dirs else []
    file_list = []
    seen_paths = set()

    for root_dir in include_dirs:
        root_path = Path(root_dir).resolve()
        if not root_path.is_dir():
            # 这里不直接 print，但是如果需要警告，我们可以把它作为日志或生成器事件
            # 为了兼容且保持解耦，我们可以忽略或者通过 yield 警告事件
            continue

        if any(root_path.is_relative_to(exclude) for exclude in exclude_paths):
            continue

        for path in root_path.rglob("*"):
            if path.is_file() and not path.is_symlink():
                resolved_path = path.resolve()

                if resolved_path in seen_paths:
                    continue

                if cache_file_path and resolved_path == Path(cache_file_path).resolve():
                    continue

                if any(
                    resolved_path.is_relative_to(exclude) for exclude in exclude_paths
                ):
                    continue

                seen_paths.add(resolved_path)
                file_list.append(resolved_path)

    total_files = len(file_list)
    yield ("count_end", total_files)

    if total_files == 0:
        return {}, 0, 0, []

    hash_map = defaultdict(list)
    chunk_size = 1024 * 1024  # 1MB
    processed_files = 0
    cache_hits = 0

    # 2. 计算哈希阶段
    for path in file_list:
        processed_files += 1
        path_str = str(path)
        is_cache_hit = False

        try:
            file_hash = None
            if cache:
                file_hash = cache.get_hash(path)
                if file_hash:
                    cache_hits += 1
                    is_cache_hit = True

            if file_hash is None:
                hasher = xxhash.xxh3_128()
                with path.open("rb") as f:
                    while chunk := f.read(chunk_size):
                        hasher.update(chunk)
                file_hash = hasher.hexdigest()
                if cache:
                    cache.update_hash(path, file_hash)

            hash_map[file_hash].append(path_str)
            yield (
                "hash_progress",
                processed_files,
                total_files,
                path_str,
                is_cache_hit,
            )

        except (OSError, PermissionError) as e:
            # 向上层抛出异常，让 UI 模块决定如何展示和处理
            raise RuntimeError(f"读取文件失败: {path}\n原因: {e}")

    duplicates = {hsh: paths for hsh, paths in hash_map.items() if len(paths) > 1}
    return duplicates, cache_hits, total_files, file_list
